"""做完练习后再看：只缩放宽度，不改位置，也不原地改输入。"""
import math


def scale_widths(widths, factor):
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("factor 必须是正有限数")
    result = []
    for width in widths:
        if not math.isfinite(width) or width < 0:
            raise ValueError("width 必须是非负有限数")
        scaled = width * factor
        if not math.isfinite(scaled):
            raise ValueError("缩放结果溢出")
        result.append(scaled)
    return result
