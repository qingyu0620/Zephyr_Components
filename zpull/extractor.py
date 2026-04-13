import shutil
from pathlib import Path


def extract_to(clone_dir: Path, project_root: Path, extract_map: dict,
               shallow_dirs: set | None = None):
    shallow_dirs = shallow_dirs or set()
    for src_name, dest_name in extract_map.items():
        src = clone_dir / src_name
        dest = project_root / dest_name
        if not src.exists():
            continue
        is_shallow = src_name in shallow_dirs
        if dest.exists():
            if src.is_dir():
                for child in src.iterdir():
                    if is_shallow and child.is_dir():
                        continue
                    if not (dest / child.name).exists():
                        shutil.move(str(child), str(dest / child.name))
                print(f"  [merge] {src_name}/ -> {dest_name}/")
            else:
                print(f"  [skip] {dest_name} 已存在")
        else:
            if is_shallow and src.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                for child in src.iterdir():
                    if child.is_dir():
                        continue
                    shutil.move(str(child), str(dest / child.name))
                print(f"  [extract-shallow] {src_name}/ -> {dest_name}/")
            else:
                shutil.move(str(src), str(dest))
                s = "/" if src.is_dir() else ""
                print(f"  [extract] {src_name}{s} -> {dest_name}{s}")
