"""在 Maya 中调用 inspect_selection()；只读，不改变当前选择。"""


def inspect_selection():
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    rows = []
    for name in cmds.ls(selection=True, objectsOnly=True, long=True) or []:
        local_list = om.MSelectionList()
        local_list.add(name)
        obj = local_list.getDependNode(0)
        fn = om.MFnDependencyNode(obj)
        row = {
            "selection_name": name,
            "api_name": fn.name(),
            "node_type": fn.typeName,
            "is_dag": obj.hasFn(om.MFn.kDagNode),
            "shapes": cmds.listRelatives(name, shapes=True, fullPath=True) or [],
        }
        rows.append(row)
    for row in rows:
        print(row)
    return rows
