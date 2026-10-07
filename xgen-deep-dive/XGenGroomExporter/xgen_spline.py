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
    # 【数据边界】脱离 Maya 节点的纯 Python 数据，用于测试、转换和文件写入。
    # positions = [x0,y0,z0,x1,y1,z1,...]；counts = [第一根点数,第二根点数,...]。
    # array('f') 近似连续的 float32 缓冲；不要把 Python 普通 list 当成 C++ float*。
    positions: array
    counts: array
    root_uvs: array | None
    widths: array | None
    skipped: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def curve_count(self):
        # property 让调用者写 data.curve_count，不用 data.curve_count()；没有额外存一份数量。
        return len(self.counts)

    @property
    def point_count(self):
        return len(self.positions) // 3


def iter_blocks(buf):
    """Yield (type, payload memoryview); reject truncation and trailing bytes."""
    view = memoryview(buf)
    # memoryview 像受 Python 对象生命周期管理的字节视图，切片通常不复制底层数据。
    offset = 0
    while offset < len(view):
        if len(view) - offset < 16:
            raise SplineError(f"Truncated block header at {offset}")
        kind, size = struct.unpack_from("<I4xQ", view, offset)
        # C++ 对照：小端 uint32 + 跳过4字节 + uint64，共16字节。
        # 显式描述文件布局，不能用宿主 struct 的 padding/alignment 去猜序列化格式。
        end = offset + 16 + size
        if end > len(view):
            raise SplineError(f"Block at {offset} exceeds buffer: {size}")
        yield kind, view[offset + 16:end]
        # 这是普通生成器：调用者每次迭代才取得一个块，区别于 @contextmanager 的协议。
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
    # 不信任文件里的大小：限制解压长度，并检查流是否结束、是否有尾随垃圾。
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
    # frombytes 按 array 元素类型解释字节；必须另外处理文件的小端约定。
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
        # 64位引用的高32位是组号、低32位是组内块号。这是已验证布局的规则，非通用 Maya API。
        try:
            return _numbers(self.groups[group][index][1], code)
        except IndexError as exc:
            raise SplineError(f"{key} reference out of bounds: {group}/{index}") from exc

    def decode(self, read_uv=True, read_width=True):
        # 将压缩/分组/带偏移的内部存储，转换为下游只需顺序遍历的连续发丝数据。
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
                # PrimitiveInfos 每条记录3个 uint32：offset、length、reserved。
                # offset 按“顶点”计数；取 positions 时乘3，取 UV 时乘2，width 不用乘。
                offset, length, _reserved = info[i:i + 3]
                if offset < previous_end or offset + length > n:
                    raise SplineError("Overlapping or out-of-range curve indices")
                previous_end = offset + length
                if length < 2:
                    # 跳过不能形成曲线的数据时，所有可选属性必须同步跳过，避免属性错位。
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
    # cmds：加载/执行命令；API 2.0：访问节点、属性接口。两者可以在同一个工具里分工。
    if cmds.nodeType(node) != "xgmSplineDescription":
        raise SplineError(f"{node}: expected xgmSplineDescription; convert legacy XGen first")
    errors = []
    for plug_name in ("outSplineData", "outRenderData"):
        plug = f"{node}.{plug_name}"
        try:
            selection = om.MSelectionList()
            # 这个局部 MSelectionList 用于把名字解析成对象；不会更改 Maya 当前选择。
            selection.add(node)
            dep = om.MFnDependencyNode(selection.getDependNode(0))
            # MObject 是 Maya 对象句柄；MFnDependencyNode 是附着到它上面的“操作接口”。
            data = om.MFnPluginData(dep.findPlug(plug_name, False).asMObject()).data()
            # Plug 是节点属性接口，不是文件插头。读取输出可能触发 DG 求值。
            # XGen 原生 C++ MPxData 不一定暴露出可在 Python 调用的 writeBinary，因此需要后备路径。
            blob = data.writeBinary()
            if isinstance(blob, bytes) and blob:
                return blob
        except Exception as exc:
            errors.append(f"{plug} API: {exc}")
        fd, path = tempfile.mkstemp(suffix=".xgspline")
        os.close(fd)
        try:
            cmds.xgmExportSplineDataInternal(plug, output=path)
            # 名字含 Internal：这是内部命令。当前版本测试可用，不应承诺跨版本稳定。
            # 临时文件保存的是 XGen 序列化数据，不是最终 Alembic，也不生成逐根 Maya 曲线。
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
