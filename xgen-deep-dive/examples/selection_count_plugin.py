"""真正的 API 2.0 命令插件：使用 cmds.loadPlugin 加载，不是普通 import 工具。"""
import maya.api.OpenMaya as om

COMMAND_NAME = "xgLearnSelectionCount"


def maya_useNewAPI():
    # Maya 通过这个入口判断插件采用 Python API 2.0 对象。
    pass


class SelectionCountCommand(om.MPxCommand):
    @staticmethod
    def creator():
        # 与 C++ 静态 creator 相同的角色：让 Maya 创建一次命令实例。
        return SelectionCountCommand()

    def doIt(self, args):
        active = om.MGlobal.getActiveSelectionList()
        self.setResult(active.length())

    def isUndoable(self):
        # 只读命令，没有场景更改需要撤销。
        return False


def initializePlugin(plugin_object):
    plugin = om.MFnPlugin(plugin_object, "XGen Learning", "1.0", "Any")
    plugin.registerCommand(COMMAND_NAME, SelectionCountCommand.creator)


def uninitializePlugin(plugin_object):
    plugin = om.MFnPlugin(plugin_object)
    plugin.deregisterCommand(COMMAND_NAME)
