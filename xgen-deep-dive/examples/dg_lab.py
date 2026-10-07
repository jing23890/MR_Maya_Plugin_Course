"""在练习场景运行：创建少量内置节点，观察求值，再清理本次节点。"""


def run():
    import maya.cmds as cmds
    saved_selection = cmds.ls(selection=True, long=True) or []
    created = []
    try:
        driver = cmds.createNode("transform", name="xgLearn_driver#", skipSelect=True)
        created.append(driver)
        multiply = cmds.createNode("multiplyDivide", name="xgLearn_multiply#", skipSelect=True)
        created.append(multiply)
        cmds.setAttr(multiply + ".operation", 1)  # 1 = Multiply。
        cmds.setAttr(multiply + ".input2X", 2.0)
        cmds.connectAttr(driver + ".translateX", multiply + ".input1X")
        results = []
        for value in (3.0, 5.0):
            cmds.setAttr(driver + ".translateX", value)
            # 读取依赖输出，由 Maya 求值；没有手动调用节点的 compute。
            results.append(cmds.getAttr(multiply + ".outputX"))
        print("DG results:", results)
        return results
    finally:
        # 仅清理由本函数记录的对象，不扫描整个场景按名字删除。
        for name in reversed(created):
            if cmds.objExists(name):
                cmds.delete(name)
        remaining = [name for name in saved_selection if cmds.objExists(name)]
        if remaining:
            cmds.select(remaining, replace=True)
        else:
            cmds.select(clear=True)
