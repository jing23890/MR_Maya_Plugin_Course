"""纯 Python 规则层：故意不 import maya，便于离开 Maya 测试。"""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class MeshRecord:
    path: str
    vertices: int
    faces: int
    local_scale: tuple[float, float, float]


@dataclass(frozen=True)
class Issue:
    path: str
    code: str
    message: str


def inspect(records: list[MeshRecord], face_limit: int = 50000) -> list[Issue]:
    """阈值必须是非负整数；不修改输入记录。"""
    if type(face_limit) is not int or face_limit < 0:
        raise ValueError("面数阈值必须是非负整数")
    issues = []
    for record in records:
        if record.faces > face_limit:
            issues.append(Issue(record.path, "FACE_LIMIT", f"面数 {record.faces} 超过 {face_limit}"))
        if any(not math.isfinite(v) or abs(v - 1.0) > 1e-6 for v in record.local_scale):
            issues.append(Issue(record.path, "LOCAL_SCALE", f"本地 scale 为 {record.local_scale}"))
    return issues


def save_report(path: str, records: list[MeshRecord], issues: list[Issue]) -> None:
    """显式写磁盘，不属于 Maya undo。界面负责让用户选择并确认覆盖路径。"""
    payload = {"schema_version": 1, "meshes": [asdict(r) for r in records],
               "issues": [asdict(i) for i in issues]}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
