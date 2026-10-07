"""Direct XGen spline to Unreal Groom exporter for Maya 2026."""
__version__ = "0.1.0"


def show():
    # 【学习入口】import 包只执行本文件；调用 show() 才导入 UI。
    # 这叫延迟导入：命令行测试解析器时，不必先加载 Qt 和 Maya UI。
    # “.ui”是本包里的 ui.py；as 给导入的函数换一个局部名字，避免同名。
    from .ui import show as open_window
    return open_window()
