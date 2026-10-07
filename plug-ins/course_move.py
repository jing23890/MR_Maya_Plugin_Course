"""API 2.0 命令：把选中 transform 的 translateX 增加指定厘米数。"""
import math
import maya.api.OpenMaya as om

COMMAND = "courseMoveX"


def maya_useNewAPI():
    pass


class MoveX(om.MPxCommand):
    @staticmethod
    def creator():
        return MoveX()

    def doIt(self, args):
        if len(args) != 1:
            raise RuntimeError("用法：cmds.courseMoveX(厘米数)")
        delta = args.asDouble(0)
        if not math.isfinite(delta):
            raise RuntimeError("位移必须是有限数值")
        selection = om.MGlobal.getActiveSelectionList()
        if not selection.length():
            raise RuntimeError("请选中 transform")
        self.modifier = om.MDGModifier()
        seen = set()
        # 先准备全部修改，任意对象不合格就拒绝整次动作。
        for index in range(selection.length()):
            path, component = selection.getComponent(index)
            if not component.isNull() or not path.node().hasFn(om.MFn.kTransform):
                raise RuntimeError("本命令只接受 transform，不接受组件或 shape")
            fn = om.MFnDependencyNode(path.node())
            identity = fn.uuid().asString()
            if identity in seen:  # 同一个实例化 transform 的属性只改一次。
                continue
            seen.add(identity)
            plug = fn.findPlug("translateX", False)
            if plug.isLocked or plug.parent().isLocked or plug.isDestination:
                raise RuntimeError(f"{path.fullPathName()}.translateX 已锁定或被驱动")
            value = plug.asMDistance().asCentimeters() + delta
            self.modifier.newPlugValueMDistance(plug, om.MDistance(value, om.MDistance.kCentimeters))
        self.redoIt()

    def redoIt(self):
        self.modifier.doIt()

    def undoIt(self):
        self.modifier.undoIt()

    def isUndoable(self):
        return True


def initializePlugin(obj):
    om.MFnPlugin(obj, "Maya Course", "1.0", "Any").registerCommand(COMMAND, MoveX.creator)


def uninitializePlugin(obj):
    om.MFnPlugin(obj).deregisterCommand(COMMAND)
