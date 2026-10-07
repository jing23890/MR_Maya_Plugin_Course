# 从零设计 Maya 插件 · Python 实战课程

面向：接触过编程语法，但 Python 基础薄弱，希望自己设计、调试和交付 Maya 工具的人。不要求 C++ 知识。

这套课程全程使用 Python，通过 **场景检查器 → 可撤销命令 → 计算节点** 建立开发全貌。最后回到 XGen 导出器，练习跨软件数据管线。每课都有动手任务和验收要求；不要只看代码。

## 从这里开始

**导航：** [课程目录](#课程目录) · [项目结构与代码阅读指南](PROJECT_STRUCTURE.md) · [快速启动](#快速启动) · [测试方法](#测试方法) · [验证记录](VALIDATION.md)

先读 [第 1 课](lessons/01-开发地图与第一段脚本.md)，在一个空白练习场景中运行第一段代码。今天只完成第 1、2 课，不必一次读完。

## 课程目录

| 顺序 | 课程 | 完成后的能力 |
|---|---|---|
| 1 | [开发地图与第一段脚本](lessons/01-开发地图与第一段脚本.md) | 分清工具、命令插件、节点插件，验证运行环境 |
| 2 | [Python 基础](lessons/02-Python基础.md) | 理解引用、函数、模块、异常和上下文管理器 |
| 3 | [先设计，再写场景检查器](lessons/03-需求与纯逻辑.md) | 写输入输出契约，把算法与 Maya 分开 |
| 4 | [场景、DAG、DG 与数据边界](lessons/04-Maya场景接口.md) | 正确处理 transform、shape、长路径和选择 |
| 5 | [界面与生命周期](lessons/05-界面.md) | 使用 PySide6 信号，管理窗口与对象生命周期 |
| 6 | [撤销与正式命令](lessons/06-可撤销命令.md) | 实现 doIt / redoIt / undoIt，先验证再修改 |
| 7 | [真正的依赖图节点](lessons/07-依赖图节点.md) | 注册属性、声明依赖、通过 compute 输出结果 |
| 8 | [注册、卸载与回调](lessons/08-插件生命周期.md) | 管理插件入口、注册资源和清理过程 |
| 9 | [测试与定位问题](lessons/09-测试调试.md) | 区分纯逻辑测试、Maya 集成测试和界面验收 |
| 10 | [安装、版本与交付](lessons/10-安装发布.md) | 使用 .mod 组织工具，清理回调，明确兼容性 |
| 11 | [XGen 综合项目](lessons/11-XGen综合项目.md) | 设计数据契约、单位转换、导出事务和错误诊断 |
| 12 | [毕业项目与继续深入](lessons/12-毕业项目.md) | 从需求独立完成一个工具，并知道 API 的进阶方向 |

## 工程目录

详细的文件职责、调用关系和阅读路线见 [项目结构与代码阅读指南](PROJECT_STRUCTURE.md)。

```text
scripts/course_scene/   场景检查器：core / bridge / ui 三层
scripts/XGenGroomExporter/  完整 XGen 导出插件源码、图标和测试
plug-ins/              两个完整 Python API 2.0 插件
exercises/             留给你填写的练习与参考答案
tests/                 纯逻辑测试、独立 Maya 集成测试
lessons/               教材正文
MayaPluginCourse.mod   安装描述文件模板
```

示例以 **Windows / Maya 2026 / Python 3 / PySide6 / API 2.0** 为基线。其他版本不默认承诺兼容。课程无需 C++ 编译器。测试状态见 [验证记录](VALIDATION.md)。

## 快速启动

克隆仓库或通过 GitHub 的 **Code → Download ZIP** 下载并解压：

```bash
git clone https://github.com/jing23890/MR_Maya_Plugin_Course.git
```

以下假设仓库放在 `D:/Courses/MR_Maya_Plugin_Course`。所有示例路径都需要按你的实际位置修改；无需把文件复制到 Maya 安装目录。第一次运行请使用空白练习场景。

### 打开场景检查器

在 Maya 的 Script Editor 中选择 **Python** 标签，替换路径后运行：

```python
import sys
course_root = r"D:/Courses/MR_Maya_Plugin_Course"
scripts_path = course_root + "/scripts"
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
from course_scene import ui
ui.show()
```

先在空场景创建一个立方体、选中它，再点击“检查选中的网格”。工具只检查选择的 transform 或 mesh 本身，不递归扫描整个组。报告中的缩放指 **transform 的本地 scale 属性**，不是世界变换，也不会自动修改模型。

### 加载正式插件与 XGen 工具

- 可撤销命令：按 [第 6 课](lessons/06-可撤销命令.md) 加载 `plug-ins/course_move.py`。
- 计算节点：按 [第 7 课](lessons/07-依赖图节点.md) 加载 `plug-ins/course_multiply.py`。节点 ID 仅作本地学习，公开分发自定义节点前需解决唯一 ID 问题。
- XGen 导出器：按 [随课 XGen 启动说明](scripts/XGenGroomExporter/README.md) 打开；它需要有效的 XGen 场景和正确的 Maya Project。
- 持久安装：参考 [第 10 课](lessons/10-安装发布.md)，修改 `.mod` 模板中的路径后再安装。

## 测试方法

在仓库根目录打开 PowerShell，替换 mayapy 的实际安装路径：

```powershell
# 纯逻辑与练习参考答案：10 项
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' -m unittest discover -s tests -p 'test_*.py' -v

# XGen 数据解析与 Alembic 写入：8 项
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' -m unittest discover -s scripts/XGenGroomExporter/tests -p 'test_*.py' -v

# Maya 集成：只在独立进程运行，会新建/替换临时测试场景
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' tests/run_maya.py
```

不要把最后一个脚本粘贴到正在制作的 Maya 场景中。界面人工验收、其他 Maya 版本和真实 XGen → UE 绑定不属于这些测试的覆盖范围，详见 [验证记录](VALIDATION.md)。

在课程根目录运行 `mayapy package_course.py` 可检查本地 Markdown 链接和 Python 语法，并在父目录生成源码 ZIP。打包不等同于运行上述测试。

## 学法与范围

每课按“先预测 → 自己运行 → 故意制造一次错误 → 对照源码 → 独立改动”进行。建议按完成验收推进，而不是按阅读页数推进。

这里的“完整”指从需求到交付的一条完整开发路径。变形器、Viewport 2.0、自定义绘制、复杂并行求值属于后续专题，本课程提供学习入口，不把一个乘法节点说成掌握了整个 Maya SDK。

XGen 插件已包含在本课程包中，见 [XGen 启动与阅读说明](scripts/XGenGroomExporter/README.md)。之前的长篇 XGen 注释教材不包含在本包中，也不是前置条件。已有的制作场景、XGen 工程缓存、UE 插件/工程和商业 SDK 不包含在课程包内；运行需要 Maya，实际导出需要你自己的有效 XGen 场景。
