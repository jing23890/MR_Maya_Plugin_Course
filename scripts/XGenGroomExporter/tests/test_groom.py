"""Run with Maya mayapy: -m unittest discover -s tests -v."""
from array import array
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from XGenGroomExporter.xgen_spline import SplineBlob, SplineData, SplineError
from XGenGroomExporter.abc_writer import GroomGroup, write_archive, inspect_archive, _cubic


def block(payload, kind=1):
    return struct.pack("<I4xQ", kind, len(payload)) + payload


def blob(groups=1, shift=32, corrupt_index=False, short=False):
    items, encoded = [], []
    for g in range(groups):
        fields = [struct.pack("<6I",0,1 if short else 2,0,2,3,0),
                  struct.pack("<15f",0,0,g,1,0,g,0,1,g,1,1,g,2,1,g),
                  struct.pack("<10f",.2,.3,.2,.3,.6,.7,.6,.7,.6,.7),
                  struct.pack("<5f",.1,.05,.2,.1,.01)]
        raw = b"".join(block(f) for f in fields)
        encoded.append(block(b"\0" * shift + zlib.compress(raw)))
        base = g << 32
        items.append(dict(Name=f"mesh{g}", PrimitiveInfos=base, Positions=base+1,
                          PatchUVs=base+2, WIDTH_CV=base+(99 if corrupt_index else 3)))
    header = dict(Header=dict(Type="XgSplineData", Version=1, GroupVersion=1,
                             GroupCount=groups, GroupDeflate=True), Items=items)
    return block(json.dumps(header).encode(), 0x8099CEAD) + b"".join(encoded)


class ParserTests(unittest.TestCase):
    def test_multiple_groups_and_root_uvs(self):
        data = SplineBlob(blob(2)).decode()
        self.assertEqual(list(data.counts), [2,3,2,3])
        self.assertEqual(data.point_count, 10)
        self.assertAlmostEqual(data.root_uvs[2], .6)
        self.assertAlmostEqual(data.widths[-1], .01)

    def test_scan_validates_shifted_stream(self):
        data = SplineBlob(blob(shift=47))
        self.assertEqual(data.offsets, [47])
        self.assertEqual(data.decode().curve_count, 2)

    def test_truncation_and_bad_reference(self):
        for invalid in (blob()[:-1], blob()[:15], blob() + b"trailing"):
            with self.assertRaises(SplineError):
                SplineBlob(invalid)
        with self.assertRaises(SplineError):
            SplineBlob(blob(corrupt_index=True)).decode()

    def test_skip_single_point_keeps_arrays_aligned(self):
        data = SplineBlob(blob(short=True)).decode()
        self.assertEqual(data.skipped, 1)
        self.assertEqual(list(data.counts), [3])
        self.assertEqual(len(data.root_uvs), 2)
        self.assertAlmostEqual(data.root_uvs[0], .6)
        self.assertEqual(len(data.widths), 3)

    def test_short_curve_elevation_preserves_endpoints(self):
        source = SplineBlob(blob()).decode()
        data = _cubic(source)
        self.assertEqual(list(data.counts), [4,4])
        self.assertEqual(list(data.positions[:3]), [0,0,0])
        self.assertEqual(list(data.positions[9:12]), [1,0,0])
        self.assertEqual(list(data.positions[-3:]), [2,1,0])
        # Quadratic midpoint is unchanged by cubic degree elevation.
        p = data.positions[12:]
        for j in range(3):
            midpoint = sum(p[i*3+j]*v for i,v in enumerate((.125,.375,.375,.125)))
            original = sum(source.positions[(i+2)*3+j]*v for i,v in enumerate((.25,.5,.25)))
            self.assertAlmostEqual(midpoint, original, places=6)


class AlembicTests(unittest.TestCase):
    def test_multigroup_and_guide_attributes(self):
        from alembic import Abc, AbcGeom as G
        data = SplineBlob(blob()).decode()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"test.abc"
            groups = [GroomGroup("hair",data,0), GroomGroup("hair",data,0,True), GroomGroup("brow",data,1)]
            write_archive(path, groups)
            self.assertEqual(len(inspect_archive(path)), 3)
            arc = Abc.IArchive(str(path))
            root = arc.getTop().getChild(0)
            for i,group in enumerate(groups):
                obj = G.ICurves(root.getChild(i), Abc.WrapExistingFlag.kWrapExisting)
                arb = obj.getSchema().getArbGeomParams()
                self.assertEqual(list(G.IInt32GeomParam(arb,"groom_group_id").getExpandedValue().getVals()), [group.group_id]*2)
                self.assertEqual(list(G.IInt32GeomParam(arb,"groom_guide").getExpandedValue().getVals()), [int(group.is_guide)]*2)
            del arb, obj, root, arc

    def test_disabled_optional_attributes(self):
        from alembic import Abc, AbcGeom as G
        data = SplineBlob(blob()).decode(False,False)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"test.abc"
            write_archive(path,[GroomGroup("hair",data,0)],False,False,False)
            result = inspect_archive(path)
            self.assertEqual(set(result[0]["attributes"]), {"groom_guide","groom_group_id"})

    def test_invalid_arrays_do_not_write(self):
        data = SplineData(array("f",[0,0,0]),array("i",[2]),None,None)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.abc"
            with self.assertRaises(SplineError):
                write_archive(path,[GroomGroup("hair",data,0)])
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
