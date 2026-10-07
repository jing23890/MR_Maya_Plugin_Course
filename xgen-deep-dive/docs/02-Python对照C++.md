# 2. 用 C++ 经验读本项目的 Python

建议同时运行 `examples/python_basics.py`。先理解这些语法，就足以读主流程。

## 2.1 名字绑定，不是固定类型的栈变量

```python
a = [1, 2]
b = a
b.append(3)
print(a)  # [1, 2, 3]
c = a.copy()
c.append(4)
```

`b = a` 没有复制容器，两个名字指向同一个对象。可类比共享同一对象的引用，但 Python 的赋值会重新绑定名字，不等于 C++ 引用变量的所有语义。`a.copy()` 是浅拷贝：若元素本身也是可变对象，内部对象仍可能共享。

`list` 是动态对象引用序列，不是紧密排列的 C++ 数值数组。本项目使用 `array('f')` 储存连续浮点数据；文件读写时仍要处理字节序和尺寸检查。

## 2.2 函数、类和数据类

```python
def export_grooms(descs, out_path, options=None):
    options = options or ExportOptions()
```

`def` 定义函数，缩进定义代码块。`None` 是“未提供值”的约定。本项目没有把 `ExportOptions()` 放在默认参数位置，因为默认表达式在函数定义时求值，不是每次调用重新创建。

```python
from dataclasses import dataclass

@dataclass
class ExportItem:
    node: str
    group_name: str = ""
    is_guide: bool = False
```

可以把它看作自动生成构造函数和显示形式的数据 struct。`ExportItem("descriptionShape", "Hair", False)` 构造实例。`node: str` 是类型提示，不是 C++ 编译期类型检查；错误类型通常要等实际使用时才报错。

`self` 类似显式 `this`：实例方法的第一个参数按习惯叫 self。`super().__init__(parent)` 调用继承链上的初始化实现。`@property` 让 getter 看起来像成员读取，比如 `data.curve_count`。

`_validate` 的单下划线表示“内部使用”的约定，不是 C++ private，外部仍可调用。

## 2.3 import、包和缓存

- `.py` 文件通常对应模块。
- 带 `__init__.py` 的目录在本项目中是普通包。
- `from .ui import show` 的点表示当前包，不是磁盘当前目录。
- `import` 首次执行模块顶层代码，后续通常取 `sys.modules` 中已缓存对象。
- `sys.path` 列的是查找包的父目录，不是包内部文件路径。

因此 `import XGenGroomExporter` 不会创建窗口；显式调用 `show()` 才会导入 UI 并构造窗口。这与 C++ 的头文件文本展开不同，不要把 import 当成 `#include`。

`from module import function` 会把函数对象绑定到当前名字；之后 reload 原模块，不保证所有已经持有旧函数/类的地方都更新。这是 Maya 开发里“明明改了代码却没生效”的常见原因。

## 2.4 容器和推导式

```python
nodes = [d.node for d in descriptions if not d.legacy]
by_name = {d.label: d.node for d in descriptions}
unique = {d.node for d in descriptions}
```

分别是 list、dict、set 推导式。第一条等价于：

```python
nodes = []
for d in descriptions:
    if not d.legacy:
        nodes.append(d.node)
```

`for i, item in enumerate(items)` 同时得到下标和元素。`zip(a, b)` 同时遍历两个序列，默认以较短者为界；涉及文件协议时应先验证长度，不能用 zip 静默掩盖不匹配。

`array[start:end]` 采用左闭右开区间，类似 C++ `[first,last)`。`range(0, len(info), 3)` 每次跨过一条三字段记录。

`cmds.ls(...) or []` 利用短路逻辑：左边为 None 或空容器时返回空列表。`is None` 判断是不是同一个特殊对象；数值、字符串内容比较用 `==`。

## 2.5 函数也是对象：回调和闭包

```python
self.export_button.clicked.connect(self.export)
```

这里传入的是将来可调用的方法。写成 `self.export()` 会立即执行，再把返回值传给 connect，含义完全不同。

`export_grooms(..., progress, dialog.wasCanceled)` 将 UI 的进度和取消查询函数传给业务层。业务层只需知道“能调用它”，不需要包含 Qt。

内部函数 `status()` 使用外层的 `progress` 和 `cancelled`，这叫闭包，类似带捕获的 C++ lambda。读取外层变量不必写声明；若要在内部重新绑定外层局部名字，需要 `nonlocal`。本项目没有在 status 中重新绑定这些名字。

## 2.6 异常和上下文管理器

```python
try:
    result = do_work()
except ValueError as exc:
    print(exc)
finally:
    release_resource()
```

`raise` 类似 throw。`finally` 在正常结束或异常离开时执行；它不是数据库回滚，更不能抵御进程崩溃。

```python
from contextlib import contextmanager

@contextmanager
def resource():
    print("准备")
    try:
        yield "可用对象"
    finally:
        print("清理")

with resource() as value:
    print(value)
```

运行顺序为准备 → with 中的代码 → 清理。可以用 RAII/scope guard 的经验理解，但 Python 不建议依赖 `__del__` 及时释放关键资源；`with` 的退出路径更明确。

不要混淆两种 yield：`iter_blocks()` 是被循环消费的生成器；`_resolved_node()` 经 `@contextmanager` 装饰，被 with 协议消费，要求一次资源使用对应一次 yield。

## 2.7 常见的小语法

| 代码 | 含义 |
| --- | --- |
| `f"读取 {node}"` | 格式化字符串 |
| `{parent_path!r}` | 插入 repr 形式，适合把路径写入 Python 代码文本 |
| `cls(*values)` | 把序列展开为多个位置参数 |
| `getattr(imath, "V3f")` | 按属性名取得类型/对象 |
| `pass` | 空语句，例如暂时不扩展父异常类 |
| `a if condition else b` | 条件表达式，类似三目运算 |
| `global _window` | 函数中重新绑定模块级名字 |

动态灵活不代表无需约束：本项目靠类型提示、输入检查和测试共同维护数据契约。
