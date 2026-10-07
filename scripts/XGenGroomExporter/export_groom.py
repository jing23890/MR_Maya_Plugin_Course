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
    import maya.cmds as cmds
    if not cmds.pluginInfo("xgenToolkit", query=True, loaded=True):
        cmds.loadPlugin("xgenToolkit", quiet=True)
    result = []
    for kind, legacy in (("xgmSplineDescription", False), ("xgmDescription", True)):
        for node in cmds.ls(type=kind, long=True) or []:
            parts = node.strip("|").split("|")
            label = "/".join(parts[:-1]) or parts[-1]
            result.append(Description(node, label, legacy))
    return result


def list_spline_descriptions():
    return {d.label: d.node for d in list_descriptions() if not d.legacy}


@contextmanager
def _resolved_node(node, allow_conversion):
    import maya.cmds as cmds
    if cmds.nodeType(node) == "xgmSplineDescription":
        yield node
        return
    if cmds.nodeType(node) != "xgmDescription" or not allow_conversion:
        raise SplineError(f"{node}: enable temporary conversion for legacy XGen")
    # Native conversion can create supporting DG nodes. Track UUIDs so only nodes
    # created inside this synchronous conversion are removed, even after failure.
    before = set(cmds.ls(uuid=True))
    selection = cmds.ls(selection=True, long=True) or []
    modified = cmds.file(query=True, modified=True)
    undo_enabled = cmds.undoInfo(query=True, state=True)
    try:
        # Temporary conversion/cleanup must not pollute the user's undo queue.
        cmds.undoInfo(stateWithoutFlush=False)
        cmds.select(node, replace=True)
        created = cmds.xgmGroomConvert() or []
        shapes = [n for n in created if cmds.objExists(n) and cmds.nodeType(n) == "xgmSplineDescription"]
        if len(shapes) != 1:
            raise SplineError(f"Expected one converted description, got {shapes}")
        yield shapes[0]
    finally:
        try:
            new_ids = set(cmds.ls(uuid=True)) - before
            new_nodes = [n for uid in new_ids for n in (cmds.ls(uid, long=True) or [])]
            if new_nodes:
                cmds.delete(new_nodes)
            remaining = [n for n in selection if cmds.objExists(n)]
            cmds.select(remaining, replace=True) if remaining else cmds.select(clear=True)
            cmds.file(modified=modified)
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
            ids[name.casefold()] = len(ids)
        with _resolved_node(item.node, options.convert_legacy) as node:
            data = read_splines(node, options.bake_root_uv, options.write_width)
        # Maya's internal spline arrays are in centimeters, independent of UI units.
        groups.append(GroomGroup(name, data, ids[name.casefold()], item.is_guide))
    # An all-guide group cannot form a visible render Groom in UE.
    for group_id in ids.values():
        if all(g.is_guide for g in groups if g.group_id == group_id):
            raise SplineError("Every group needs a render description; give guides the same group name as their hair")
    fd, tmp = tempfile.mkstemp(prefix=".groom_", suffix=".abc", dir=path.parent)
    os.close(fd)
    try:
        status("Writing Alembic", len(items))
        rows = write_archive(tmp, groups, options.bake_root_uv, options.write_width, options.write_group_name)
        status("Checking Alembic", len(items) + 1)
        checked = inspect_archive(tmp)
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
            os.unlink(tmp)
    return dict(path=str(path), groups=len(ids), curve_nodes=len(rows),
                curves=sum(r["curves"] for r in rows), points=sum(r["points"] for r in rows),
                seconds=round(time.monotonic() - started, 3), descriptions=rows,
                validation=checked, source_frame=cmds.currentTime(query=True),
                source_ui_unit=cmds.currentUnit(query=True, linear=True), archive_unit="cm")
