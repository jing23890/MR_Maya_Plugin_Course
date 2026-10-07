# XGen 综合项目：随课插件副本

这是此前开发的 XGen → UE Groom 导出工具源码副本，包含五个 Python 模块、icons/groom.png 和 tests/test_groom.py。制作场景、工程缓存、导出 Alembic、UE 端插件不在此目录中。

## 启动

在 Maya 2026 的 Python Script Editor 执行，移动课程目录后修改路径：

```python
import sys
scripts_path = r"D:/Courses/MR_Maya_Plugin_Course/scripts"
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
import XGenGroomExporter
print(XGenGroomExporter.__file__)  # 确认加载的是课程副本
XGenGroomExporter.show()
```

若此前会话已加载其他位置的同名包，sys.path 改动不会替换缓存模块。保存工作后重启 Maya，再从课程路径加载，避免混用两份源码。

使用 Maya 自带的 Alembic、imath、PySide6 等依赖，不需要另行 pip 安装。只有在有效 XGen 场景、正确 Maya Project 和完整外部缓存下，才能验证真实发型导出。

## 使用步骤

1. 打开自己的 XGen 场景，设置对应 Maya Project，确认发型正常求值。
2. 打开窗口，勾选描述、设置组名。传统 XGen 按需要启用临时转换。
3. 设置 root UV、宽度与组信息，选择输出路径后导出当前帧静态 Groom。
4. 在 UE 中导入 Alembic；MetaHuman 衣橱转换与绑定属于另一个 UE 工具的范围。

## 阅读顺序

- __init__.py：包入口，延迟加载 UI。
- ui.py：参数收集、信号、状态与工具架入口。
- export_groom.py：导出流程、参数对象、临时转换与文件提交。
- xgen_spline.py：样条读取、二进制解析与普通数据结构。
- abc_writer.py：Alembic 写入和回读检查。

结合课程第 11 课画出数据流，再实现宽度缩放作业。此副本保留原源码，不代表每行都已补充教学注释。

## 运行配套测试

在课程根目录的 PowerShell 中执行，按本机安装修改 mayapy 路径：

```powershell
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' -m unittest discover -s scripts/XGenGroomExporter/tests -p 'test_*.py' -v
```

这些测试不等价于实际用户场景端到端导出与 UE 绑定验证。
