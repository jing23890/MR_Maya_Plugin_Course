"""Strict, Maya-independent decoder plus Maya's native binary serialization.

Verified layout: the first block's size is JSON *length*, not end offset.
Compressed group payloads have a 32-byte preamble before the zlib stream.
Serialized PrimitiveInfos contains offset, count, reserved (12-byte records).
"""
from array import array
from dataclasses import dataclass, field
import json
import math
import os
import struct
import sys
import tempfile
import zlib


class SplineError(RuntimeError):
    pass


@dataclass
class SplineData:
    positions: array
    counts: array
    root_uvs: array | None
    widths: array | None
    skipped: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def curve_count(self):
        return len(self.counts)

    @property
    def point_count(self):
        return len(self.positions) // 3


def iter_blocks(buf):
    """Yield (type, payload memoryview); reject truncation and trailing bytes."""
    view = memoryview(buf)
    offset = 0
    while offset < len(view):
        if len(view) - offset < 16:
            raise SplineError(f"Truncated block header at {offset}")
        kind, size = struct.unpack_from("<I4xQ", view, offset)
        end = offset + 16 + size
        if end > len(view):
            raise SplineError(f"Block at {offset} exceeds buffer: {size}")
        yield kind, view[offset + 16:end]
        offset = end


def _header(blob):
    if len(blob) < 16:
        raise SplineError("Missing XGen header")
    kind, size = struct.unpack_from("<I4xQ", blob)
    if kind != 0x8099CEAD or not 0 < size <= min(len(blob) - 16, 16 * 1024 * 1024):
        raise SplineError("Unrecognized XGen header or invalid JSON size")
    try:
        header = json.loads(blob[16:16 + size])
    except (ValueError, UnicodeError) as exc:
        raise SplineError("Invalid XGen JSON header") from exc
    info = header.get("Header", {})
    if info.get("Type") != "XgSplineData" or info.get("Version") != 1 or info.get("GroupVersion") != 1:
        raise SplineError(f"Unsupported XGen format: {info}")
    if info.get("GroupBase64"):
        raise SplineError("Base64 groups are not supported")
    return header, 16 + size


def parse_header(blob):
    return _header(blob)[0]


def _inflate(payload, offset, limit):
    dec = zlib.decompressobj()
    raw = dec.decompress(payload[offset:], limit + 1)
    if len(raw) > limit or not dec.eof or dec.unused_data:
        raise SplineError("Incomplete, oversized or trailing compressed group")
    blocks = list(iter_blocks(raw))
    if not blocks:
        raise SplineError("Empty decompressed block list")
    return blocks


def _group(payload, compressed, limit):
    if not compressed:
        # The uncompressed variant is deliberately unsupported until sampled.
        raise SplineError("Uncompressed XGen groups have not been validated")
    # Bounded scan only within this group, never through unrelated group data.
    candidates = [32] + [i for i in range(min(4096, len(payload) - 1)) if i != 32]
    for offset in candidates:
        if offset + 2 > len(payload):
            continue
        a, b = payload[offset:offset + 2]
        if a & 15 != 8 or ((a << 8) | b) % 31:
            continue
        try:
            return _inflate(payload, offset, limit), offset
        except (zlib.error, SplineError):
            continue
    raise SplineError("No complete zlib stream containing valid blocks in group")


def _numbers(payload, code):
    if len(payload) % 4:
        raise SplineError("Misaligned numeric array")
    values = array(code)
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    return values


class SplineBlob:
    def __init__(self, blob, max_group_bytes=1024 * 1024 * 1024):
        self.header, self.header_end = _header(blob)
        info = self.header["Header"]
        groups = list(iter_blocks(memoryview(blob)[self.header_end:]))
        if len(groups) != info.get("GroupCount"):
            raise SplineError("GroupCount does not match binary block count")
        self.groups, self.offsets = [], []
        for _, payload in groups:
            blocks, offset = _group(payload, info.get("GroupDeflate"), max_group_bytes)
            self.groups.append(blocks)
            self.offsets.append(offset)

    def extract(self, item, key, code="f"):
        reference = item.get(key)
        if not isinstance(reference, int) or reference < 0:
            raise SplineError(f"Missing or invalid {key} reference")
        group, index = reference >> 32, reference & 0xFFFFFFFF
        try:
            return _numbers(self.groups[group][index][1], code)
        except IndexError as exc:
            raise SplineError(f"{key} reference out of bounds: {group}/{index}") from exc

    def decode(self, read_uv=True, read_width=True):
        positions, counts = array("f"), array("i")
        uvs = array("f") if read_uv else None
        widths = array("f") if read_width else None
        skipped, item_counts = 0, []
        for item in self.header.get("Items", []):
            p = self.extract(item, "Positions")
            info = self.extract(item, "PrimitiveInfos", "I")
            uv = self.extract(item, "PatchUVs") if read_uv else None
            w = self.extract(item, "WIDTH_CV") if read_width else None
            if len(p) % 3 or len(info) % 3:
                raise SplineError("Invalid Positions or 12-byte PrimitiveInfos records")
            n = len(p) // 3
            if uv is not None and len(uv) != 2 * n:
                raise SplineError("PatchUVs is not a per-vertex float2 array")
            if w is not None and len(w) != n:
                raise SplineError("WIDTH_CV is not a per-vertex float array")
            if not all(math.isfinite(x) for x in p):
                raise SplineError("Non-finite positions")
            if uv is not None and not all(math.isfinite(x) for x in uv):
                raise SplineError("Non-finite UVs")
            if w is not None and not all(math.isfinite(x) and x >= 0 for x in w):
                raise SplineError("Negative or non-finite widths")
            previous_end = 0
            for i in range(0, len(info), 3):
                offset, length, _reserved = info[i:i + 3]
                if offset < previous_end or offset + length > n:
                    raise SplineError("Overlapping or out-of-range curve indices")
                previous_end = offset + length
                if length < 2:
                    skipped += 1
                    continue
                counts.append(length)
                positions.extend(p[3 * offset:3 * (offset + length)])
                if uvs is not None:
                    uvs.extend(uv[2 * offset:2 * offset + 2])
                if widths is not None:
                    widths.extend(w[offset:offset + length])
            item_counts.append(len(info) // 3)
        if not counts:
            raise SplineError("Description contains no curves with at least two points")
        return SplineData(positions, counts, uvs, widths, skipped, {
            "header": self.header["Header"], "item_curve_counts": item_counts,
            "deflate_offsets_in_group": self.offsets,
        })


def read_blob(node):
    """Maya C++ plugin data is not necessarily exposed as an MPxData in Python.

    Try the direct API, then Autodesk's own serializer (temporary binary file,
    no curve nodes and no Alembic intermediate). Both output plugs are tried.
    """
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    if cmds.nodeType(node) != "xgmSplineDescription":
        raise SplineError(f"{node}: expected xgmSplineDescription; convert legacy XGen first")
    errors = []
    for plug_name in ("outSplineData", "outRenderData"):
        plug = f"{node}.{plug_name}"
        try:
            selection = om.MSelectionList()
            selection.add(node)
            dep = om.MFnDependencyNode(selection.getDependNode(0))
            data = om.MFnPluginData(dep.findPlug(plug_name, False).asMObject()).data()
            blob = data.writeBinary()
            if isinstance(blob, bytes) and blob:
                return blob
        except Exception as exc:
            errors.append(f"{plug} API: {exc}")
        fd, path = tempfile.mkstemp(suffix=".xgspline")
        os.close(fd)
        try:
            cmds.xgmExportSplineDataInternal(plug, output=path)
            with open(path, "rb") as stream:
                blob = stream.read()
            if blob:
                return blob
            errors.append(f"{plug}: empty native serialization")
        except Exception as exc:
            errors.append(f"{plug} native: {exc}")
        finally:
            os.unlink(path)
    raise SplineError("Cannot read XGen spline data:\n" + "\n".join(errors))


def read_splines(node, read_uv=True, read_width=True):
    return SplineBlob(read_blob(node)).decode(read_uv, read_width)
