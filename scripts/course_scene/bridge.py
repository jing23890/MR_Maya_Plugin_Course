"""主线程场景适配层：把 Maya 对象读成普通数据，规则层不持有 MObject。"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
from .core import MeshRecord


def collect_selected() -> list[MeshRecord]:
    meshes = set()
    # objectsOnly 把组件选择归到对象；这是检查器的规则，不是所有工具的通用规则。
    for path in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if cmds.nodeType(path) == "mesh":
            if not cmds.getAttr(path + ".intermediateObject"):
                meshes.add(path)
        elif cmds.nodeType(path) == "transform":
            meshes.update(cmds.listRelatives(path, shapes=True, noIntermediate=True,
                                            fullPath=True, type="mesh") or [])
    records = []
    for path in sorted(meshes):
        selection = om.MSelectionList()
        selection.add(path)
        dag_path = selection.getDagPath(0)
        mesh = om.MFnMesh(dag_path)
        parent_path = om.MDagPath(dag_path)
        parent_path.pop()
        scale = tuple(cmds.getAttr(parent_path.fullPathName() + ".scale")[0])
        records.append(MeshRecord(path, mesh.numVertices, mesh.numPolygons, scale))
    return records
