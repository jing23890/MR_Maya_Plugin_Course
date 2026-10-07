"""校验文档链接和 Python 语法，打包源码；包含长篇教材，排除 build/cache。"""
import ast
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
allowed_dirs = {"scripts", "plug-ins", "exercises", "tests", "lessons", "xgen-deep-dive"}
files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in {".md", ".py", ".mod"}]
files += [ROOT / name for name in ("LICENSE", ".gitignore") if (ROOT / name).is_file()]
for name in sorted(allowed_dirs):
    files += [p for p in (ROOT / name).rglob("*")
              if p.is_file() and p.suffix in {".py", ".md", ".png"} and "__pycache__" not in p.parts]
for path in files:
    if path.suffix == ".py":
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    elif path.suffix == ".md":
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (path.parent / target.split("#")[0]).exists(), (path, target)
output = ROOT.parent / "Maya-Plugin-Course_Python_1.0.zip"
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, str(Path(ROOT.name) / path.relative_to(ROOT)))
print(f"Validated {len(files)} files; package: {output}")
