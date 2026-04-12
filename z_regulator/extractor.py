import shutil
from pathlib import Path


def extract_to(clone_dir: Path, project_root: Path, extract_map: dict):
    for src_name, dest_name in extract_map.items():
        src = clone_dir / src_name
        dest = project_root / dest_name
        if not src.exists():
            continue
        if dest.exists():
            if src.is_dir():
                for child in src.iterdir():
                    if not (dest / child.name).exists():
                        shutil.move(str(child), str(dest / child.name))
                print(f"  [merge] {src_name}/ -> {dest_name}/")
            else:
                print(f"  [skip] {dest_name} 已存在")
        else:
            shutil.move(str(src), str(dest))
            s = "/" if src.is_dir() else ""
            print(f"  [extract] {src_name}{s} -> {dest_name}{s}")
