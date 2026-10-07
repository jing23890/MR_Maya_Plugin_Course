"""Alembic output; imported lazily so the parser works outside Maya."""
from array import array
from dataclasses import dataclass
import math
import re
from .xgen_spline import SplineData, SplineError


@dataclass
class GroomGroup:
    name: str
    data: SplineData
    group_id: int
    is_guide: bool = False


def _validate(data):
    if not data.counts or any(n < 2 for n in data.counts):
        raise SplineError("Each curve needs at least two points")
    if sum(data.counts) * 3 != len(data.positions):
        raise SplineError("Curve counts do not match position array")
    if data.root_uvs is not None and len(data.root_uvs) != 2 * data.curve_count:
        raise SplineError("Root UV count must equal curve count")
    if data.widths is not None and len(data.widths) != data.point_count:
        raise SplineError("Width count must equal point count")
    for values in (data.positions, data.root_uvs, data.widths):
        if values is not None and not all(math.isfinite(x) for x in values):
            raise SplineError("Non-finite geometry values")
    if data.widths is not None and any(x < 0 for x in data.widths):
        raise SplineError("Negative width")


def _cubic(data):
    """Degree-elevate 2/3-CV curves exactly; keep a single cubic ICurves node.

    Avoid variable-order curves: the local UE importer treats order as degree.
    Full clamped Alembic knot arrays have n+4 values (Maya API uses n+2).
    """
    _validate(data)
    if min(data.counts) >= 4:
        return data
    positions, counts = array("f"), array("i")
    widths = array("f") if data.widths is not None else None
    start = 0
    for n in data.counts:
        p = [tuple(data.positions[3 * i:3 * i + 3]) for i in range(start, start + n)]
        w = list(data.widths[start:start + n]) if widths is not None else None
        if n < 4:
            if n == 2:
                weights = [(1, 0), (2/3, 1/3), (1/3, 2/3), (0, 1)]
            else:
                weights = [(1, 0, 0), (1/3, 2/3, 0), (0, 2/3, 1/3), (0, 0, 1)]
            p = [tuple(sum(v[j] * a for v, a in zip(p, row)) for j in range(3)) for row in weights]
            if w is not None:
                w = [sum(v * a for v, a in zip(w, row)) for row in weights]
        for v in p:
            positions.extend(v)
        counts.append(len(p))
        if widths is not None:
            widths.extend(w)
        start += n
    return SplineData(positions, counts, data.root_uvs, widths, data.skipped, data.metadata)


def _array(imath, kind, values):
    result = getattr(imath, kind)(len(values))
    for i, value in enumerate(values):
        result[i] = value
    return result


def _vectors(imath, kind, vector, values, size):
    result = getattr(imath, kind)(len(values) // size)
    cls = getattr(imath, vector)
    for i in range(len(result)):
        result[i] = cls(*values[i * size:(i + 1) * size])
    return result


def _write_group(parent, object_name, group, bake_root_uv, write_width, write_group_name):
    from alembic import AbcGeom as G
    import imath
    data = _cubic(group.data)
    uniform, vertex = G.GeometryScope.kUniformScope, G.GeometryScope.kVertexScope
    curves = G.OCurves(parent, object_name)
    schema = curves.getSchema()
    sample = G.OCurvesSchemaSample()
    sample.setPositions(_vectors(imath, "V3fArray", "V3f", data.positions, 3))
    sample.setCurvesNumVertices(_array(imath, "IntArray", data.counts))
    sample.setType(G.CurveType.kCubic)
    sample.setBasis(G.BasisType.kBsplineBasis)
    sample.setWrap(G.CurvePeriodicity.kNonPeriodic)
    sample.setOrders(_array(imath, "UnsignedCharArray", [4] * data.curve_count))
    knots = array("f")
    for n in data.counts:
        knots.extend([0, 0, 0] + list(range(n - 2)) + [n - 3] * 3)
    sample.setKnots(_array(imath, "FloatArray", knots))
    if bake_root_uv:
        if data.root_uvs is None:
            raise SplineError(f"{group.name}: root UVs requested but unavailable")
        sample.setUVs(G.OV2fGeomParamSample(_vectors(imath, "V2fArray", "V2f", data.root_uvs, 2), uniform))
    if write_width:
        if data.widths is None:
            raise SplineError(f"{group.name}: widths requested but unavailable")
        sample.setWidths(G.OFloatGeomParamSample(_array(imath, "FloatArray", data.widths), vertex))
    schema.set(sample)
    arb = schema.getArbGeomParams()
    for name, value in (("groom_guide", int(group.is_guide)), ("groom_group_id", group.group_id)):
        # UE's generic numeric attribute switch accepts kInt32POD, not kUint32POD.
        param = G.OInt32GeomParam(arb, name, False, uniform, 1)
        param.set(G.OInt32GeomParamSample(_array(imath, "IntArray", [value] * data.curve_count), uniform))
    if write_group_name:
        param = G.OStringGeomParam(arb, "groom_group_name", False, uniform, 1)
        param.set(G.OStringGeomParamSample(_array(imath, "StringArray", [group.name] * data.curve_count), uniform))
    return dict(object_name=object_name, group_name=group.name, group_id=group.group_id,
                is_guide=group.is_guide, curves=data.curve_count, points=data.point_count,
                source_points=group.data.point_count, skipped=data.skipped)


def write_archive(path, groups, bake_root_uv=True, write_width=True, write_group_name=True):
    """Low-level writer. Caller owns overwrite policy. One constant sample/node."""
    from alembic import Abc, AbcGeom as G
    if not groups:
        raise SplineError("No groups selected")
    for group in groups:
        _validate(group.data)
        if not group.name.strip() or not 0 <= group.group_id <= 2147483647:
            raise SplineError("Invalid group name or group ID")
    archive = Abc.OArchive(str(path))
    root = G.OXform(archive.getTop(), "Groom")
    root.getSchema().set(G.XformSample())
    rows = []
    for i, group in enumerate(groups):
        # Object names need not equal group names; preserve Unicode names in attributes.
        name = re.sub(r"[^A-Za-z0-9_]", "_", group.name).strip("_") or "group"
        rows.append(_write_group(root, f"{i:03d}_{name}", group, bake_root_uv, write_width, write_group_name))
    # Boost.Python archive writes its footer when its last owner is released.
    del root
    del archive
    return rows


def inspect_archive(path):
    """Read back topology, knots and attribute scope/cardinality. Raises on mismatch."""
    from alembic import Abc, AbcGeom as G
    archive = Abc.IArchive(str(path))
    rows = []

    def visit(obj):
        if G.ICurves.matches(obj.getHeader()):
            curves = G.ICurves(obj, Abc.WrapExistingFlag.kWrapExisting)
            schema = curves.getSchema()
            sample = schema.getValue()
            counts = list(sample.getCurvesNumVertices())
            points = sample.getPositions()
            if sum(counts) != len(points) or any(n < 4 for n in counts):
                raise SplineError("Invalid archived curve topology")
            if len(sample.getKnots()) != sum(n + 4 for n in counts):
                raise SplineError("Invalid full cubic knot count")
            if schema.getNumSamples() != 1:
                raise SplineError("Expected one static sample")
            row = dict(path=obj.getFullName(), curves=len(counts), points=len(points), attributes={})

            def check(name, param, scope, count):
                if param.getScope() != scope or len(param.getExpandedValue().getVals()) != count:
                    raise SplineError(f"{name}: invalid scope or cardinality")
                row["attributes"][name] = str(scope)

            uv = schema.getUVsParam()
            if uv.valid():
                check("uv", uv, G.GeometryScope.kUniformScope, len(counts))
            width = schema.getWidthsParam()
            if width.valid():
                check("width", width, G.GeometryScope.kVertexScope, len(points))
            arb = schema.getArbGeomParams()
            for name in ("groom_guide", "groom_group_id"):
                check(name, G.IInt32GeomParam(arb, name), G.GeometryScope.kUniformScope, len(counts))
            if arb.getPropertyHeader("groom_group_name"):
                check("groom_group_name", G.IStringGeomParam(arb, "groom_group_name"), G.GeometryScope.kUniformScope, len(counts))
            rows.append(row)
        for i in range(obj.getNumChildren()):
            visit(obj.getChild(i))

    visit(archive.getTop())
    if not rows:
        raise SplineError("Archive contains no ICurves")
    return rows
