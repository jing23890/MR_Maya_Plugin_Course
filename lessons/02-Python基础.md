# 第 2 课：Python 基础，从对象和函数开始

目标：能读懂本课程源码。不要求你了解其他语言的类、指针或内存管理。

## 2.1 变量绑定对象，不是复制容器

```python
a = [1, 2]
b = a
b.append(3)
print(a)       # [1, 2, 3]
c = a.copy()
c.append(4)
print(a)       # 仍是 [1, 2, 3]
```

`b = a` 让两个名字指向同一个列表，并没有新建列表。`copy()` 是浅复制：嵌套列表内部仍可能共享。函数收到列表后调用 append，会改变调用者看见的对象。

练习：写一个把所有数乘 2 的函数，要求原列表不变。参考形式是 `return [value * 2 for value in values]`。

## 2.2 函数、默认参数和返回值

```python
def add_issue(message, issues=None):
    if issues is None:
        issues = []
    issues.append(message)
    return issues
```

不要写 `issues=[]` 作为需要每次新建的默认值。默认参数对象在函数定义时创建，各次调用会共享它。类型标注如 `message: str` 是阅读和静态检查的信息，不会自动阻止传入整数。

Python 可以直接返回多个值：`return records, issues` 实际返回 tuple，调用侧用 `records, issues = scan()` 解包。`None` 通常表示没有结果，而空列表表示有效结果为空；接口应明确两者。

## 2.3 类和 dataclass

类是一种把数据和相关操作放在一起的定义，实例是照着定义创建的具体对象。先运行这个最小例子：

```python
class Report:
    def __init__(self, title):
        self.title = title

    def describe(self):
        return "报告：" + self.title

first = Report("模型检查")
print(first.describe())
```

调用 Report(...) 时创建实例，并用 __init__ 设置初始数据。self 指当前实例；first.describe() 会自动把 first 作为 self 传入。两个 Report 实例可以保存不同的 title。

打开 [core.py](../scripts/course_scene/core.py)。`MeshRecord` 描述一份读取后的快照。`@dataclass` 是一个装饰器：它根据字段声明帮这个类生成初始化等方法，减少重复代码。你先理解上面的手写类，再看这种简写。

`frozen=True` 禁止通常的字段重新赋值，但不会自动把内部所有对象变成不可修改。本例用字符串、整数、tuple，避免在记录里偷偷共享可变列表。

`@staticmethod` 表示这个函数不需要当前实例，调用时不会自动传入 self。继承写成 `class Child(Parent)`，让 Child 建立在 Parent 的能力上；继承 `om.MPxNode` 则是按 Maya 约定提供它会调用的方法，第 7 课再具体实践。

## 2.4 import 与目录

```text
scripts/
  course_scene/
    __init__.py
    core.py
    bridge.py
```

把 `scripts` 放入 sys.path 后，才能 `from course_scene import core`。不是把 `course_scene` 自己放进去。包内 `from .core import MeshRecord` 的点表示当前包。

模块首次导入会执行顶层语句，之后通常从 sys.modules 缓存取回。因此顶层不要创建模型、弹窗或修改选择。修改磁盘文件也不会自动更新已经加载的模块。开发时可 reload 纯逻辑模块；复杂 UI / 插件建议关闭并卸载后重新加载，避免旧类实例和新类混用。

## 2.5 异常、finally 与资源

`try / except` 用来处理已预期的失败，不应该用空的 except 隐藏所有问题。需要保证结束时执行清理，用 `with` 或 `try/finally`。先认识 try/finally，再阅读下面较进阶的上下文管理器，不必第一遍就会自己写装饰器。

```python
from contextlib import contextmanager
import maya.cmds as cmds

@contextmanager
def undo_group(label):
    cmds.undoInfo(openChunk=True, chunkName=label)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)
```

`yield` 前是进入，后是退出；即使块内抛异常也会执行 finally。**撤销分组不是事务**：它会合并撤销记录，不保证异常时自动回滚已执行动作。

## 验收

解释以下三件事，再进入下一课：

1. 为什么报告记录不直接存 Maya 的窗口对象？
2. 为什么 `def f(items=[])` 连续调用可能积累数据？
3. 为什么关闭 undo chunk 不能当作异常回滚？

动手：不用 Maya，定义一个包含路径与面数的 dataclass，写函数筛选面数大于阈值的记录，保证输入列表不变。

---

[课程首页](../README.md) · [上一课](01-开发地图与第一段脚本.md) · [下一课](03-需求与纯逻辑.md)
