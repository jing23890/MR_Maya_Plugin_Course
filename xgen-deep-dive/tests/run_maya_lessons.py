"""用 mayapy 独立运行，不要在已打开的 Maya Script Editor 中执行本文件。"""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import maya.standalone
maya.standalone.initialize(name="python")

try:
    import maya.cmds as cmds
    from examples import python_basics, scene_probe, dg_lab

    python_basics.run()
    cmds.select(clear=True)
    assert scene_probe.inspect_selection() == []
    nodes = [cmds.createNode("transform", name="lessonA"), cmds.createNode("transform", name="lessonB")]
    cmds.select(nodes, replace=True)
    rows = scene_probe.inspect_selection()
    assert len(rows) == 2 and all(row["node_type"] == "transform" for row in rows)
    before = set(cmds.ls(uuid=True))
    assert dg_lab.run() == [6.0, 10.0]
    assert set(cmds.ls(uuid=True)) == before
    assert set(cmds.ls(selection=True)) == set(nodes)

    plugin_path = str(root / "examples" / "selection_count_plugin.py")
    loaded_plugin = cmds.loadPlugin(plugin_path, quiet=True)[0]
    try:
        result = cmds.xgLearnSelectionCount()
        print("Command result:", repr(result), type(result).__name__)
        # 本机 Maya 2026 的 Python 命令桥把单一数字返回为单元素列表。
        count = result[0] if isinstance(result, (list, tuple)) else result
        assert count == 2, result
        cmds.select(clear=True)
        result = cmds.xgLearnSelectionCount()
        count = result[0] if isinstance(result, (list, tuple)) else result
        assert count == 0, result
    finally:
        cmds.unloadPlugin(loaded_plugin)
    cmds.delete(nodes)
    print("PASS: Python basics, scene probe, DG cleanup/selection, MPxCommand load/execute/unload")
finally:
    maya.standalone.uninitialize()
