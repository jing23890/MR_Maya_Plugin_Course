"""只在单独 mayapy 进程执行。会新建/替换测试场景，不要粘贴到正在制作的 Maya。"""
from pathlib import Path
import sys
import tempfile
import maya.standalone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
maya.standalone.initialize(name="python")
import maya.cmds as cmds
from course_scene.bridge import collect_selected


def scalar(value):
    return value[0] if isinstance(value, (list, tuple)) else value


def rejected(call):
    try:
        call()
    except RuntimeError:
        return
    raise AssertionError("Expected rejection")


try:
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True)
    a = cmds.polyCube(name="courseA")[0]
    b = cmds.polyCube(name="courseB")[0]
    cmds.select(a, b)
    records = collect_selected()
    assert len(records) == 2 and all(r.faces == 6 for r in records)
    cmds.select(a + ".vtx[0]")
    assert len(collect_selected()) == 1
    cmds.select(clear=True)
    assert collect_selected() == []
    print("PASS bridge: transforms, component selection, empty selection")

    move = cmds.loadPlugin(str(ROOT / "plug-ins/course_move.py"), quiet=True)[0]
    cmds.select(a, b)
    cmds.courseMoveX(3.0)
    assert cmds.getAttr(a + ".tx") == 3 and cmds.getAttr(b + ".tx") == 3
    cmds.undo()
    assert cmds.getAttr(a + ".tx") == 0 and cmds.getAttr(b + ".tx") == 0
    cmds.redo()
    assert cmds.getAttr(a + ".tx") == 3
    cmds.setAttr(b + ".tx", lock=True)
    rejected(lambda: cmds.courseMoveX(5))
    assert cmds.getAttr(a + ".tx") == 3  # 第二个失败不能让第一个偷偷移动。
    cmds.setAttr(b + ".tx", lock=False)
    cmds.select(a + ".vtx[0]")
    rejected(lambda: cmds.courseMoveX(5))
    cmds.select(clear=True)
    rejected(lambda: cmds.courseMoveX(5))
    cmds.currentUnit(linear="m")
    cmds.select(a)
    cmds.courseMoveX(100)
    assert abs(cmds.getAttr(a + ".tx") - 1.03) < 1e-9
    cmds.currentUnit(linear="cm")
    cmds.flushUndo()  # 仅隔离测试进程：释放队列里持有插件命令的实例。
    cmds.unloadPlugin(move)
    print("PASS MPxCommand: apply, undo, redo, preflight, component/empty rejection, units")

    multiply = cmds.loadPlugin(str(ROOT / "plug-ins/course_multiply.py"), quiet=True)[0]
    node = cmds.createNode("courseMultiply")
    cmds.setAttr(node + ".inputB", 2)
    cmds.connectAttr(b + ".tx", node + ".inputA")
    assert cmds.getAttr(node + ".output") == 6
    cmds.setAttr(b + ".tx", 4)
    assert cmds.getAttr(node + ".output") == 8
    with tempfile.TemporaryDirectory() as folder:
        scene = str(Path(folder) / "node.ma")
        cmds.file(rename=scene)
        cmds.file(save=True, type="mayaAscii")
        cmds.file(new=True, force=True)
        cmds.file(scene, open=True, force=True)
        assert cmds.getAttr(node + ".output") == 8
        cmds.file(new=True, force=True)
    cmds.flushUndo()
    cmds.unloadPlugin(multiply)
    print("PASS MPxNode: connection, dirty propagation, scene round trip")

    print("ALL REQUESTED MAYA TESTS PASSED")
finally:
    maya.standalone.uninitialize()
