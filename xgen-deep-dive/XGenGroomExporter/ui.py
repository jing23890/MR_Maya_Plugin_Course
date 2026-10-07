"""Small Maya 2026 / PySide6 front end. All Maya access stays on the UI thread."""
from pathlib import Path
import traceback
from PySide6 import QtCore, QtGui, QtWidgets
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui
from .export_groom import (ExportItem, ExportOptions, ExportCancelled,
                           export_grooms, list_descriptions)

_window = None
 # Python 模块保留窗口引用；否则包装对象可能被回收。Qt 仍有自己的父子对象生命周期。


class GroomWindow(QtWidgets.QDialog):
    # 类比 class GroomWindow : public QDialog。self 类似显式 this，super 调用父类实现。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XGen → UE Groom · Maya 2026")
        self.setWindowIcon(QtGui.QIcon(str(Path(__file__).resolve().parent / "icons" / "groom.png")))
        self.resize(760, 440)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self._busy = False
        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel("当前帧静态导出 · 相同组名合并为同一 UE 组；导线须与对应头发同组。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["XGen 描述", "组名", "是导线", "类型"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 65)
        self.table.setColumnWidth(3, 100)
        layout.addWidget(self.table)
        self.refresh_button = QtWidgets.QPushButton("刷新描述")
        self.refresh_button.clicked.connect(self.refresh)
        # 传的是绑定方法，而不是 self.refresh() 的调用结果；Qt 在点击时才调用它。
        layout.addWidget(self.refresh_button)
        options = QtWidgets.QHBoxLayout()
        self.uv = QtWidgets.QCheckBox("Bake root UV")
        self.width = QtWidgets.QCheckBox("写 width")
        self.names = QtWidgets.QCheckBox("写 group name")
        self.legacy = QtWidgets.QCheckBox("临时转换传统 XGen")
        for box in (self.uv, self.width, self.names, self.legacy):
            box.setChecked(True)
            options.addWidget(box)
        self.uv.setToolTip("取 XGen PatchUVs 的根顶点值，写标准 uniform .uv；不会重新投影到其他网格。")
        self.legacy.setToolTip("在内存中转换，读取后清理生成节点；不保存源场景。")
        layout.addLayout(options)
        file_row = QtWidgets.QHBoxLayout()
        self.path = QtWidgets.QLineEdit(str(Path.home() / "groom.abc"))
        self.browse = QtWidgets.QPushButton("选择路径…")
        self.browse.clicked.connect(self.choose_path)
        file_row.addWidget(self.path)
        file_row.addWidget(self.browse)
        layout.addLayout(file_row)
        self.export_button = QtWidgets.QPushButton("导出 Groom Alembic")
        self.export_button.clicked.connect(self.export)
        layout.addWidget(self.export_button)
        self.status = QtWidgets.QLabel("就绪")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        if self._busy:
            return
        try:
            previous = {}
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                previous[item.data(QtCore.Qt.ItemDataRole.UserRole)] = (
                    item.checkState(), self.table.item(row, 1).text(), self.table.item(row, 2).checkState())
            descriptions = list_descriptions()
            self.table.setRowCount(len(descriptions))
            for row, desc in enumerate(descriptions):
                checked, name, guide = previous.get(desc.node, (QtCore.Qt.CheckState.Checked,
                    desc.label.split("/")[-1], QtCore.Qt.CheckState.Unchecked))
                item = QtWidgets.QTableWidgetItem(desc.label)
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsSelectable)
                item.setCheckState(checked)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, desc.node)
                # 显示文字和真实 DAG 路径分开。不能把给人看的短标签当成唯一场景标识。
                item.setToolTip(desc.node)
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(name))
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(guide)
                self.table.setItem(row, 2, item)
                item = QtWidgets.QTableWidgetItem("传统 XGen" if desc.legacy else "交互式")
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(row, 3, item)
            self.status.setText(f"找到 {len(descriptions)} 个描述" if descriptions else "未找到 XGen 描述。请先打开含 XGen 的 Maya 场景。")
        except Exception as exc:
            self.status.setText(str(exc))
            traceback.print_exc()

    def choose_path(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "输出 Alembic", self.path.text(), "Alembic (*.abc)")
        if path:
            self.path.setText(path if path.lower().endswith(".abc") else path + ".abc")

    def export(self):
        # UI 只负责读取输入、展示结果；真正导出位于 export_groom.py，可无界面调用。
        if self._busy:
            return
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                selected.append(ExportItem(item.data(QtCore.Qt.ItemDataRole.UserRole),
                    self.table.item(row, 1).text(), self.table.item(row, 2).checkState() == QtCore.Qt.CheckState.Checked))
        path = self.path.text().strip()
        overwrite = Path(path).is_file()
        if overwrite and QtWidgets.QMessageBox.question(self, "覆盖输出", f"替换已有文件？\n{path}") != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        dialog = QtWidgets.QProgressDialog("准备导出…", "取消", 0, len(selected) + 2, self)
        dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        self._busy = True
        # processEvents 会允许其他 UI 事件运行，所以必须防止用户重入同一次导出。
        self.export_button.setEnabled(False)

        def progress(message, done, total):
            dialog.setLabelText(message)
            dialog.setMaximum(total)
            dialog.setValue(done)
            QtWidgets.QApplication.processEvents()
            # 这不是多线程。这里只在阶段边界处理事件；一次耗时的 XGen 求值仍会占用主线程。

        try:
            result = export_grooms(selected, path, ExportOptions(self.uv.isChecked(), self.width.isChecked(),
                self.names.isChecked(), self.legacy.isChecked(), overwrite), progress, dialog.wasCanceled)
            self.status.setText(f"已导出 {result['groups']} 组 / {result['curves']:,} 根 / {result['points']:,} 点 · {result['seconds']} 秒\n{result['path']}")
        except ExportCancelled:
            self.status.setText("已取消")
        except Exception as exc:
            self.status.setText(f"导出失败：{exc}")
            # 给用户简短错误，同时在 Script Editor 输出 traceback，保留开发定位信息。
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "导出失败", str(exc))
        finally:
            dialog.close()
            self._busy = False
            self.export_button.setEnabled(True)

    def closeEvent(self, event):
        if self._busy:
            event.ignore()
        else:
            super().closeEvent(event)


def show():
    global _window
    # Refresh existing buttons after an upgrade without creating extra buttons.
    import maya.cmds as cmds
    icon = str(Path(__file__).resolve().parent / "icons" / "groom.png")
    for button in cmds.lsUI(type="shelfButton", long=True) or []:
        if cmds.shelfButton(button, query=True, annotation=True) == "XGenGroomExporter":
            cmds.shelfButton(button, edit=True, image=icon, style="iconOnly")
    if _window is not None:
        try:
            _window.show()
            _window.raise_()
            _window.activateWindow()
            return _window
        except RuntimeError:
            _window = None
    pointer = omui.MQtUtil.mainWindow()
    # Maya 拥有 QApplication，不要自己再创建/exec 一个主事件循环。
    # wrapInstance 把 Maya 的原生 Qt 指针包装成 PySide 对象；为窗口设置 Maya 父窗口。
    parent = wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None
    _window = GroomWindow(parent)
    _window.show()
    return _window


def install_shelf():
    """Run explicitly to add an idempotent button to the currently selected shelf."""
    import maya.cmds as cmds
    import maya.mel as mel
    top = mel.eval("$tmp = $gShelfTopLevel")
    shelf = cmds.tabLayout(top, query=True, selectTab=True)
    icon = str(Path(__file__).resolve().parent / "icons" / "groom.png")
    parent_path = str(Path(__file__).resolve().parent.parent)
    command = f"import sys\np = {parent_path!r}\nif p not in sys.path: sys.path.insert(0, p)\nimport XGenGroomExporter\nXGenGroomExporter.show()"
    # Shelf 存的是下次点击要执行的 Python 文本；!r 使用 repr，正确保留路径引号/反斜杠。
    for child in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
        if cmds.objectTypeUI(child) == "shelfButton" and cmds.shelfButton(child, query=True, annotation=True) == "XGenGroomExporter":
            cmds.shelfButton(child, edit=True, image=icon, command=command, sourceType="python", style="iconOnly")
            return child
    return cmds.shelfButton(parent=shelf, label="UE Groom", annotation="XGenGroomExporter",
        image=icon, sourceType="python", command=command, style="iconOnly")
