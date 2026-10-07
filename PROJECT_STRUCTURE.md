# 项目结构与代码阅读指南

本仓库是 Python 主线的 Maya 插件入门课程，包含课程正文、可运行示例、XGen 综合项目和测试。仓库根目录就是课程根目录，不需要再套一层文件夹。

```text
MR_Maya_Plugin_Course/
├── README.md                      # 阅读入口、环境要求与快速启动
├── PROJECT_STRUCTURE.md           # 本文：文件职责与调用关系
├── VALIDATION.md                  # 已验证范围和未验证项
├── MayaPluginCourse.mod           # Maya 模块安装模板，安装前修改路径
├── package_course.py              # 检查链接/语法并生成课程 ZIP
├── lessons/                       # 01–12 课正文与官方参考资料
├── scripts/
│   ├── course_scene/              # 项目一：只读场景检查器
│   │   ├── __init__.py            # 包与版本入口
│   │   ├── core.py                # 普通数据、检查规则、JSON 输出
│   │   ├── bridge.py              # 从 Maya 场景读取网格快照
│   │   └── ui.py                  # PySide6 窗口和按钮事件
│   └── XGenGroomExporter/         # 综合项目：XGen → Alembic Groom
│       ├── README.md              # 启动方法、源码阅读顺序
│       ├── __init__.py            # 延迟加载窗口的入口
│       ├── ui.py                  # 导出界面和工具架入口
│       ├── export_groom.py        # 导出选项、流程及临时资源清理
│       ├── xgen_spline.py         # XGen 样条数据读取与解析
│       ├── abc_writer.py          # Alembic 写入和回读检查
│       ├── icons/groom.png        # Maya 工具图标
│       └── tests/test_groom.py    # 解析与 Alembic 数据测试
├── plug-ins/
│   ├── course_move.py             # 项目二：可撤销的 courseMoveX 命令
│   └── course_multiply.py         # 项目三：courseMultiply 计算节点
├── exercises/
│   ├── widths_starter.py          # 待完成的宽度缩放练习
│   └── widths_solution.py         # 参考答案
└── tests/
    ├── test_core.py               # 场景检查纯逻辑测试
    ├── test_widths.py             # 练习契约测试，默认验证参考答案
    └── run_maya.py                # 独立 mayapy 场景/命令/节点测试
```

## 三条代码阅读路线

| 学习阶段 | 阅读顺序 | 重点 |
|---|---|---|
| 场景检查器 | core → bridge → ui | 先确定规则，再访问 Maya，最后连接界面 |
| 正式插件 | course_move → course_multiply | 一次动作及撤销，与持续的数据依赖求值 |
| XGen 综合项目 | __init__ → ui → export_groom → xgen_spline / abc_writer | 参数、数据契约、读取和写出分层 |

场景检查器的按钮分别调用 bridge 和 core：bridge 返回普通记录，core 生成问题列表，ui 显示结果。core 不导入 Maya，因此可以单独测试。

XGen 工具由 export_groom 协调读取与写出。先搞清 positions、counts、widths、root UV 的意义，再研究具体二进制字段。课程示例与 XGen 工具各自独立，不需要先加载 courseMultiply 才能导出头发。

## 目录与安装机制

- `scripts` 加入 Python 搜索路径后，可导入两个工具包；**不要把包自身目录代替其父目录加入 sys.path**。
- `plug-ins` 中的文件通过 Maya `loadPlugin` 加载，注册命令或节点。
- `.mod` 用于告诉 Maya 模块位置；它不会自动打开窗口，也不等于自动加载正式插件。
- 测试与练习不是生产启动入口；`run_maya.py` 会新建测试场景，只在独立 mayapy 进程运行。

## 包含与不包含

包含 XGen 导出器的源码、图标和测试；不包含 Maya 软件、用户制作场景、XGen 缓存、UE 工程或 UE 端转换插件。实际导出需要有效 XGen 场景及其外部数据。旧版长篇注释教材不属于此仓库的前置依赖。

[返回课程首页](README.md)
