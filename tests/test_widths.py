"""默认验收参考答案。设置 COURSE_EXERCISE=starter 切换到你填写的练习。"""
import importlib.util
import os
from pathlib import Path
import unittest

variant = os.environ.get("COURSE_EXERCISE", "solution")
if variant not in ("starter", "solution"):
    raise ValueError("COURSE_EXERCISE must be starter or solution")
path = Path(__file__).resolve().parents[1] / "exercises" / f"widths_{variant}.py"
spec = importlib.util.spec_from_file_location("widths", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
scale_widths = module.scale_widths


class WidthTests(unittest.TestCase):
    def test_value_and_source(self):
        source = [0.0, 0.08, 0.1]
        self.assertEqual(scale_widths(source, 0.5), [0.0, 0.04, 0.05])
        self.assertEqual(source, [0.0, 0.08, 0.1])

    def test_empty(self):
        self.assertEqual(scale_widths([], 1), [])

    def test_bad_factor(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                scale_widths([1], value)

    def test_bad_width(self):
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                scale_widths([value], 1)

    def test_overflow(self):
        with self.assertRaises(ValueError):
            scale_widths([1e308], 1e308)


if __name__ == "__main__":
    unittest.main()
