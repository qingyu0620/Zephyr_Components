"""
轻量模块依赖管理: 读取 modules.yaml, 克隆仓库并将指定目录提取到项目根.

用法:
    python -m regulator                        # 拉取 modules.yaml 中声明的所有模块
    python -m regulator empty_project          # 只拉项目骨架 (always 列表)
    python -m regulator modules/led            # 拉模块 + 依赖 + 骨架
    python -m regulator modules/led bsp/bsp_i2c  # 拉多个
    python -m regulator --config modules.yaml  # 指定配置文件
"""

import argparse, sys
from pathlib import Path
from .utils import load_yaml, rmtree
from .repo import Repo
from .resolver import resolve_deps
from .extractor import extract_to


def build_sparse_list(args_paths, always, sparse_default):
    if args_paths == ["empty_project"]:
        paths = list(always)
        print(f"  empty_project: 拉取骨架 {paths}")
    elif args_paths:
        paths = list(args_paths)
        for a in always:
            if a not in paths:
                paths.append(a)
        print(f"  拉取指定路径 + 骨架: {paths}")
    else:
        paths = sparse_default
    return paths


def main():
    parser = argparse.ArgumentParser(description="模块依赖管理")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    cfg_path = Path(args.config) if args.config else root / "modules.yaml"
    if not cfg_path.exists():
        print(f"错误: 找不到 {cfg_path}")
        sys.exit(1)

    tmp = root / ".tmp_clone"

    for i, mod in enumerate(load_yaml(cfg_path).get("modules", [])):
        always  = mod.get("always", []) or []
        extract = mod.get("extract", {})
        sparse  = build_sparse_list(args.paths, always, mod.get("sparse", None))

        if not args.paths and extract:
            if all((root / d).exists() for d in extract.values()):
                print(f"[{i+1}] 所有目标已存在, 跳过")
                continue

        if tmp.exists():
            rmtree(tmp)
        repo = Repo(mod["repo"], mod.get("ref", "main"), tmp)

        print(f"[{i+1}] 克隆 {mod['repo']}")
        if sparse:
            print(f"  sparse: {sparse}")
            repo.clone_sparse(sparse)
        else:
            repo.clone_full()

        resolved = set()
        targets = [tmp / s for s in sparse] if sparse else \
                  [c for c in tmp.iterdir() if c.is_dir() and c.name != ".git"]
        for t in targets:
            resolve_deps(t, repo, resolved, [])
        print(f"  共 {len(resolved)} 个模块解析完成")

        extract_to(tmp, root, extract)
        rmtree(tmp)
        print(f"  [clean] 临时目录已删除")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
