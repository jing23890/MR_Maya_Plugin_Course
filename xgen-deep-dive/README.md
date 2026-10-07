# 用 XGen 导出工具学习 Maya 开发

以实际可运行的 Maya 2026 XGen 导出工具为主线，适合完成基础课程后深入阅读。文中的 C++ 对照只是辅助理解，不要求编译或编写 C++；不熟悉时可先跳过对照部分。

[返回课程首页](../README.md) · [项目结构](../PROJECT_STRUCTURE.md) · [Python 基础课](../lessons/02-Python基础.md)

这里提供 **中文注释版源码、分章教程、练习和一个正式的 Python 命令插件**。注释版保持原导出逻辑不变；它是独立学习副本，不覆盖已安装的工具。没有包含角色、XGen 项目或 Alembic 测试资产。

## 建议阅读顺序

| 顺序 | 章节 | 读完应能回答 |
| --- | --- | --- |
| 1 | [Maya 开发全景](docs/01-Maya开发全景.md) | 脚本工具、API、MPx 插件和 C++ 插件有什么关系？ |
| 2 | [给 C++ 开发者的 Python](docs/02-Python对照C++.md) | self、dataclass、yield、闭包和 import 到底在做什么？ |
| 3 | [跟踪一次导出](docs/03-跟踪一次导出.md) | 从点击按钮到 ABC，数据经过了哪些层？ |
| 4 | [场景、求值与 XGen 数据](docs/04-场景与二进制.md) | DAG、DG、MObject、Plug、序列化数组如何连接？ |
| 5 | [UI、异常、测试和部署](docs/05-工程实践.md) | 为什么不用线程直接读 Maya？怎样不破坏场景？ |
| 6 | [正式插件与动手练习](docs/06-正式插件与练习.md) | 怎样注册 MPxCommand？什么时候应该写 MPxNode/C++？ |

第一次可以按 1 → 2 → 3 → 5 → 6 阅读，第 4 章的二进制细节留到理解主流程后。

## 源码地图

```text
XGenGroomExporter/
  __init__.py        对外入口：show()
  ui.py              Qt 界面：读取用户输入、触发业务、展示结果
  export_groom.py    业务流程：描述发现、临时转换、取消、文件提交
  xgen_spline.py     Maya 数据桥接 + 独立二进制解码
  abc_writer.py      Alembic 写入和回读验证
  tests/            原工具的 8 个回归测试
examples/
  python_basics.py   不依赖 Maya 的 Python 小实验
  scene_probe.py     只读检查当前选择和节点接口
  dg_lab.py          用 Maya 自带节点观察连接与求值，自动清理本次节点
  selection_count_plugin.py   正式 MPxCommand 插件
tests/
  run_maya_lessons.py  在独立 mayapy 中验证练习
```

## 如何打开注释版工具

不要在同一 Maya 会话里混用原版和学习版同名包。新开 Maya 后，在 Python Script Editor 中运行，把路径改为此 README 所在目录：

```python
import sys
sys.path.insert(0, r"D:/Courses/MR_Maya_Plugin_Course/xgen-deep-dive")
import XGenGroomExporter
print(XGenGroomExporter.__file__)  # 先确认确实导入学习副本
XGenGroomExporter.show()
```

已导入原版时，修改 sys.path 不会自动替换 sys.modules 中缓存的包。初学阶段直接重启 Maya，比混合 reload 多层依赖更可靠。

## 学习目标和边界

这份教程给出 Maya 扩展开发的整体地图，并让你实际走通脚本工具和命令插件两条路线。自定义变形器、视口绘制、并行求值及自定义节点属于后续专题，不会把仅看过概念当成已经掌握。

注释主要解释“为什么这么组织”和“与 C++ 有什么不同”，不是逐行把 Python 翻成中文。某些原实现有明确局限，例如 XGen 内部格式依赖、临时转换清理和取消粒度；教程会指出，不把它们描述成所有 Maya 工具都应照搬的标准答案。

本教材随仓库按根目录 LICENSE 发布。官方文档链接分布在相关章节。

## 与基础课程和运行版的关系

| 入口 | 用途 |
|---|---|
| `../lessons/` | 从零建立 Python 与 Maya 开发基础，建议先完成第 1–10 课 |
| `../scripts/XGenGroomExporter/` | 随课运行版，沿用课程根目录 scripts 的启动方式 |
| 本目录 `XGenGroomExporter/` | 带中文教学注释的独立源码副本，配合本目录六章阅读 |

两份 XGen 包同名，不要在同一 Maya 会话混用。查看 `XGenGroomExporter.__file__` 确认加载位置。注释版是教学快照；后续修改运行版不意味着注释版会自动同步。

## 验证教材示例

在本目录打开 PowerShell，按实际安装路径修改 mayapy：

```powershell
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' -m unittest discover -s XGenGroomExporter/tests -p 'test_*.py' -v
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' tests/run_maya_lessons.py
```

第二条必须在独立 mayapy 进程执行，不要粘进正在制作的 Maya。真实 XGen 场景及其缓存需要自行提供。
