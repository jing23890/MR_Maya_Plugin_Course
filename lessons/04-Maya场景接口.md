# 第 4 课：场景不是一个普通对象列表

## 4.1 transform 与 shape

transform 存放变换；mesh shape 存放几何。选择一个模型时通常选中 transform，但顶点和面数来自 mesh。一个 transform 可有多个 shape，历史中还可能存在 intermediate shape，不能总取第一个子节点。

本课程用 listRelatives 的 shapes、noIntermediate、fullPath、type="mesh" 明确筛选范围。阅读 [bridge.py](../scripts/course_scene/bridge.py)，在每个条件旁写一句自己的理解。

## 4.2 DAG、DG 和实例

DAG 表达层级路径，例如 `|groupA|head|headShape`；DG 表达属性连接和求值依赖。一个节点可以参与两者。DAG 实例让同一个对象出现在多个路径下，所以 **对象身份和路径不是一回事**。

检查器以完整 shape 路径为键：不同实例路径可能有不同父 transform 缩放，应分别检查。第 6 课改 transform 属性时按节点 UUID 去重，因为同一个 transform 对象的属性不该加两次。这两个选择不同，但都来自各自的需求。

短名字在不同父节点下可以重名。避免使用 `name.split('|')[-1]` 之后再查场景；短名适合显示，不适合作为可靠身份。

## 4.3 cmds 与 API 2.0 配合

```python
selection = om.MSelectionList()
selection.add(path)
dag_path = selection.getDagPath(0)
mesh = om.MFnMesh(dag_path)
count = mesh.numPolygons
```

MSelectionList 在这里是名字到 Maya 对象的解析器；MFnMesh 是附着在对象上的功能接口。不是创建了一个新 mesh。API 中的 MObject 也不是 Python 模型实体的完整复制。

cmds 简洁，适合现成命令和查询；API 适合直接访问数据与扩展类型。不要为了“高级”把每个命令都改成 API，也不要在几十万顶点循环里反复调用字符串命令。

## 4.4 快照边界

collect_selected 返回普通记录，后续分析不持有活的 MObject。代价是场景后来改变，报告不会自动更新；界面因此明确写“本次检查报告”。持有对象句柄并监听变化是更复杂的实时工具设计，不应无意间引入。

## 实验与验收

1. 创建两个立方体，分别放进两个组；把一个 scaleY 改成 2。
2. 同时选择两个立方体，检查应返回两个记录且只有一个缩放问题。
3. 只选最外面的组：本工具不会递归找里面的网格。解释这是契约，不是必然的 Maya 限制。
4. 选择一个顶点再检查：本工具检查所属 mesh，而不只检查那一个顶点。
5. 对模型创建 instance，分别选择实例路径，观察完整路径与父变换。

进阶修改：增加明确的“递归检查组”选项，并处理重复路径；不要偷偷改变默认范围。

---

[课程首页](../README.md) · [上一课](03-需求与纯逻辑.md) · [下一课](05-界面.md)
