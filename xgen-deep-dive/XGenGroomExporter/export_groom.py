"""Maya orchestration and transactional static Groom export."""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
import time
from .xgen_spline import SplineError, read_splines


@dataclass
class Description:
    # 类似 C++ 的数据 struct。dataclass 自动生成 __init__、__repr__ 等。
    # 注解 node: str 帮助读者/IDE，不会自动在运行时拒绝一个错误类型。
    node: str
    label: str
    legacy: bool = False


@dataclass
class ExportOptions:
    bake_root_uv: bool = True
    write_width: bool = True
    write_group_name: bool = True
    convert_legacy: bool = True
    overwrite: bool = False


@dataclass
class ExportItem:
    node: str
    group_name: str = ""
    is_guide: bool = False


class ExportCancelled(RuntimeError):
    pass


def list_descriptions():
    # cmds 是 Maya 命令层：像通过 Python 调用 Maya 自带命令，不是直接操纵内存。
    import maya.cmds as cmds
    if not cmds.pluginInfo("xgenToolkit", query=True, loaded=True):
        cmds.loadPlugin("xgenToolkit", quiet=True)
    result = []
    for kind, legacy in (("xgmSplineDescription", False), ("xgmDescription", True)):
        for node in cmds.ls(type=kind, long=True) or []:
            # long=True 返回完整 DAG 路径，避免不同组下的同名节点被混淆。
            # 某些 cmds 查询返回 None；“or []”把它统一为可迭代的空列表。
            parts = node.strip("|").split("|")
            label = "/".join(parts[:-1]) or parts[-1]
            result.append(Description(node, label, legacy))
    return result


def list_spline_descriptions():
    return {d.label: d.node for d in list_descriptions() if not d.legacy}


@contextmanager
def _resolved_node(node, allow_conversion):
    # 【关键】with 的上下文管理器，可类比 C++ RAII/scope guard。
    # yield 前准备资源，yield 后/ finally 中清理；它不是开线程，也不是复制节点。
    # with 内部抛异常时，这个 finally 仍会执行（进程被强杀不在保证范围内）。
    import maya.cmds as cmds
    if cmds.nodeType(node) == "xgmSplineDescription":
        yield node
        return
    if cmds.nodeType(node) != "xgmDescription" or not allow_conversion:
        raise SplineError(f"{node}: enable temporary conversion for legacy XGen")
    # Native conversion can create supporting DG nodes. Track UUIDs so only nodes
    # created inside this synchronous conversion are removed, even after failure.
    before = set(cmds.ls(uuid=True))
    # UUID 集合差找本次转换创建的节点，比靠节点名字前缀删除更可靠。
    # 注意这个方案假设转换同步执行；若别的回调同期创建节点，集合差未必都属于我们。
    selection = cmds.ls(selection=True, long=True) or []
    modified = cmds.file(query=True, modified=True)
    undo_enabled = cmds.undoInfo(query=True, state=True)
    try:
        # Temporary conversion/cleanup must not pollute the user's undo queue.
        cmds.undoInfo(stateWithoutFlush=False)
        # 临时禁用“记录撤销”，不会清空旧队列；这不等于让整个函数支持用户 Undo。
        cmds.select(node, replace=True)
        created = cmds.xgmGroomConvert() or []
        shapes = [n for n in created if cmds.objExists(n) and cmds.nodeType(n) == "xgmSplineDescription"]
        if len(shapes) != 1:
            raise SplineError(f"Expected one converted description, got {shapes}")
        yield shapes[0]
        # 这里把转换后的 shape 交给调用者读取，随后进入 finally 清理。
    finally:
        try:
            new_ids = set(cmds.ls(uuid=True)) - before
            new_nodes = [n for uid in new_ids for n in (cmds.ls(uid, long=True) or [])]
            if new_nodes:
                cmds.delete(new_nodes)
            remaining = [n for n in selection if cmds.objExists(n)]
            cmds.select(remaining, replace=True) if remaining else cmds.select(clear=True)
            cmds.file(modified=modified)
            # 恢复的是“未保存标记”，不是把场景恢复成快照；不要把它当成回滚 API。
        finally:
            cmds.undoInfo(stateWithoutFlush=undo_enabled)


def export_grooms(descs, out_path, options=None, progress=None, cancelled=None):
    """Export a list of ExportItem or node names. Must run on Maya's main thread.

    Equal group names share an explicit ID, allowing a guide description to join
    its render description. Selection is explicit; guide status is never guessed.
    progress(message, done, total), cancelled() are optional UI callbacks.
    """
    from .abc_writer import GroomGroup, write_archive, inspect_archive
    import maya.cmds as cmds
    options = options or ExportOptions()
    # 默认参数用 None，然后每次调用新建配置，避免可变默认对象被多次调用共享。
    items = [ExportItem(d) if isinstance(d, str) else d for d in descs]
    if not items:
        raise SplineError("Select at least one description")
    if len({d.node for d in items}) != len(items):
        raise SplineError("A description was selected more than once")
    path = Path(out_path).expanduser().resolve()
    if path.suffix.lower() != ".abc":
        raise SplineError("Output path must end in .abc")
    if not path.parent.is_dir():
        raise SplineError(f"Output directory does not exist: {path.parent}")
    if path.exists() and not options.overwrite:
        raise FileExistsError(str(path))
    started, groups, ids = time.monotonic(), [], {}
    total = len(items) + 2

    def status(message, done):
        # 嵌套函数捕获外层 progress/cancelled（闭包），类似保存回调的 C++ lambda。
        # 业务层不认识 QProgressDialog，所以无 UI 测试也能复用同一导出函数。
        if cancelled and cancelled():
            raise ExportCancelled("Export cancelled")
        if progress:
            progress(message, done, total)
        if cancelled and cancelled():
            raise ExportCancelled("Export cancelled")

    for i, item in enumerate(items):
        status(f"Reading {item.node}", i)
        name = item.group_name.strip() or item.node.split("|")[-1].removesuffix("Shape")
        if name.casefold() not in ids:
            # dict 将组名映射到连续 int ID。casefold 负责不区分大小写地比较。
            ids[name.casefold()] = len(ids)
        with _resolved_node(item.node, options.convert_legacy) as node:
            # 一次导出的主路径：先保证描述可读，再取得纯数据，再写文件。
            data = read_splines(node, options.bake_root_uv, options.write_width)
        # Maya's internal spline arrays are in centimeters, independent of UI units.
        groups.append(GroomGroup(name, data, ids[name.casefold()], item.is_guide))
    # An all-guide group cannot form a visible render Groom in UE.
    for group_id in ids.values():
        if all(g.is_guide for g in groups if g.group_id == group_id):
            raise SplineError("Every group needs a render description; give guides the same group name as their hair")
    fd, tmp = tempfile.mkstemp(prefix=".groom_", suffix=".abc", dir=path.parent)
    # 临时文件和最终文件放同一目录；先写完/回读，再替换，减少破坏旧输出的风险。
    # mkstemp 同时返回打开的文件描述符和路径；下面 close 是把写入交给 Alembic。
    os.close(fd)
    try:
        status("Writing Alembic", len(items))
        rows = write_archive(tmp, groups, options.bake_root_uv, options.write_width, options.write_group_name)
        status("Checking Alembic", len(items) + 1)
        checked = inspect_archive(tmp)
        # “API 调用没报错”不等于文件正确；回读验证拓扑和属性数量/作用域。
        if len(checked) != len(items):
            raise SplineError("Unexpected archive group count")
        status("Finishing", total)
        if options.overwrite:
            os.replace(tmp, path)
        else:
            # Windows rename fails if the destination appeared during export.
            os.rename(tmp, path)
    finally:
        if os.path.exists(tmp):
            # 成功 rename 后 tmp 已不存在；失败时才需要清理剩余临时文件。
            os.unlink(tmp)
    return dict(path=str(path), groups=len(ids), curve_nodes=len(rows),
                curves=sum(r["curves"] for r in rows), points=sum(r["points"] for r in rows),
                seconds=round(time.monotonic() - started, 3), descriptions=rows,
                validation=checked, source_frame=cmds.currentTime(query=True),
                source_ui_unit=cmds.currentUnit(query=True, linear=True), archive_unit="cm")
