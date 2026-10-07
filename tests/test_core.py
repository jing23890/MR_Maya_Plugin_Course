import importlib.util
from pathlib import Path
import sys
import tempfile
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from course_scene.core import MeshRecord, inspect, save_report


class CoreTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(inspect([]), [])

    def test_threshold_and_no_mutation(self):
        records = [MeshRecord("|a|shape", 8, 6, (1, 1, 1))]
        before = records[:]
        self.assertEqual(inspect(records, 6), [])
        self.assertEqual([i.code for i in inspect(records, 5)], ["FACE_LIMIT"])
        self.assertEqual(records, before)

    def test_scale(self):
        self.assertEqual(inspect([MeshRecord("a", 1, 1, (1, 2, 1))])[0].code, "LOCAL_SCALE")

    def test_invalid_limit(self):
        for value in (-1, 2.5, True):
            with self.assertRaises(ValueError):
                inspect([], value)

    def test_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "report.json")
            save_report(path, [MeshRecord("头", 8, 6, (1, 1, 1))], [])
            self.assertEqual(json.loads(Path(path).read_text(encoding="utf-8"))["meshes"][0]["path"], "头")


if __name__ == "__main__":
    unittest.main()
