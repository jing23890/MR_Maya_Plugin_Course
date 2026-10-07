"""完整计算节点。ID 仅供本地学习；发布产品前申请并使用自己的唯一 ID。"""
import maya.api.OpenMaya as om

NAME = "courseMultiply"
TYPE_ID = om.MTypeId(0x0007F7A1)


def maya_useNewAPI():
    pass


class Multiply(om.MPxNode):
    @staticmethod
    def creator():
        return Multiply()

    @staticmethod
    def initialize():
        attr = om.MFnNumericAttribute()
        Multiply.a = attr.create("inputA", "ia", om.MFnNumericData.kDouble, 1.0)
        attr.keyable = True
        Multiply.addAttribute(Multiply.a)
        Multiply.b = attr.create("inputB", "ib", om.MFnNumericData.kDouble, 1.0)
        attr.keyable = True
        Multiply.addAttribute(Multiply.b)
        Multiply.output = attr.create("output", "out", om.MFnNumericData.kDouble, 0.0)
        attr.writable = False
        attr.storable = False
        Multiply.addAttribute(Multiply.output)
        Multiply.attributeAffects(Multiply.a, Multiply.output)
        Multiply.attributeAffects(Multiply.b, Multiply.output)

    def compute(self, plug, data):
        if plug != self.output:
            return None
        a = data.inputValue(self.a).asDouble()
        b = data.inputValue(self.b).asDouble()
        data.outputValue(self.output).setDouble(a * b)
        data.setClean(plug)


def initializePlugin(obj):
    om.MFnPlugin(obj, "Maya Course", "1.0", "Any").registerNode(
        NAME, TYPE_ID, Multiply.creator, Multiply.initialize, om.MPxNode.kDependNode)


def uninitializePlugin(obj):
    om.MFnPlugin(obj).deregisterNode(TYPE_ID)
