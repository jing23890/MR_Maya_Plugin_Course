"""薄界面：收集参数 → 调用适配层/规则层 → 显示结果。"""
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui
from . import bridge, core

_window = None  # 保留 Python 引用，Qt parent 负责宿主层的所有权。


class ReviewWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("课程：场景检查器")
        self.resize(640, 380)
        self.records = []
        self.issues = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("检查选择的网格；只读，不自动冻结变换。"))
        self.limit = QtWidgets.QSpinBox()
        self.limit.setRange(0, 10000000)
        self.limit.setValue(50000)
        self.limit.setPrefix("面数阈值：")
        layout.addWidget(self.limit)
        scan = QtWidgets.QPushButton("检查选中的网格")
        scan.clicked.connect(self.scan)
        layout.addWidget(scan)
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.export = QtWidgets.QPushButton("导出本次检查报告…")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.save)
        layout.addWidget(self.export)

    def scan(self):
        # 清掉旧结果，失败时不能把旧报告当成本次结果保存。
        self.records, self.issues = [], []
        self.export.setEnabled(False)
        try:
            self.records = bridge.collect_selected()
            self.issues = core.inspect(self.records, self.limit.value())
            lines = [f"网格 {len(self.records)} 个；问题 {len(self.issues)} 个"]
            lines += [f"{i.path}\n  [{i.code}] {i.message}" for i in self.issues]
            if not self.records:
                lines.append("请选中 mesh 或直接包含 mesh 的 transform。")
            self.output.setPlainText("\n".join(lines))
            self.export.setEnabled(bool(self.records))
        except Exception as exc:
            self.output.setPlainText(f"检查失败：{exc}")
            import traceback
            traceback.print_exc()  # 用户读简短提示，开发者在 Script Editor 读完整堆栈。

    def save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存报告", "", "JSON (*.json)")
        if not path:
            return
        try:
            core.save_report(path, self.records, self.issues)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "保存失败", str(exc))


def show():
    global _window
    # 本课程窗口没有 scriptJob/callback；如果以后增加，关闭时必须显式移除。
    if _window is not None:
        _window.close()
        _window.deleteLater()
    parent = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    _window = ReviewWindow(parent)
    _window.show()
    return _window
