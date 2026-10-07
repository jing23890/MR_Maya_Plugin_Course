"""可用普通 Python 3.10+ 或 mayapy 运行；完全不依赖 Maya。"""
from array import array
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class ExportChoice:
    name: str
    width_scale: float = 1.0


@contextmanager
def tracked_resource(events):
    events.append("acquire")
    try:
        yield "resource"
    finally:
        events.append("release")


def run():
    # 1. 赋值绑定同一对象；显式 copy 才得到新的顶层列表。
    original = [1, 2]
    alias = original
    alias.append(3)
    independent = original.copy()
    independent.append(4)
    assert original == [1, 2, 3] and independent == [1, 2, 3, 4]

    # 2. dataclass 是少写样板代码，不是把 Python 变成静态类型语言。
    choice = ExportChoice("Hair")
    assert choice.width_scale == 1.0

    # 3. 闭包把外部的收集列表带进回调，而不是使用全局日志。
    messages = []
    def report(text):
        messages.append(text)
    callback = report  # 传递函数对象，尚未执行。
    callback("reading")
    assert messages == ["reading"]

    # 4. 即使 with 的代码抛异常，contextmanager 的 finally 仍执行。
    events = []
    try:
        with tracked_resource(events) as resource:
            assert resource == "resource"
            raise ValueError("模拟读取失败")
    except ValueError:
        events.append("caught")
    assert events == ["acquire", "release", "caught"]

    # 5. 两根曲线的数组布局：第二根起点偏移按顶点计数，再乘3。
    positions = array("f", [0, 0, 0, 0, 1, 0, 2, 0, 0, 2, 1, 0, 2, 2, 0])
    counts = array("i", [2, 3])
    start = counts[0]
    assert list(positions[start * 3:start * 3 + 3]) == [2.0, 0.0, 0.0]
    assert sum(counts) * 3 == len(positions)
    return {"alias": original, "events": events, "curves": len(counts)}


if __name__ == "__main__":
    print(run())
