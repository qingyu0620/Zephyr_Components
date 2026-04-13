"""
轻量模块依赖管理: 读取 modules.yaml, 克隆仓库并将指定目录提取到项目根.

用法:
    python -m zpull --tag template             # 拉取 template 标签 (空骨架)
    python -m zpull --tag blink_led            # 拉取 blink_led 标签 (完整版本)
    python -m zpull modules/led                # 拉模块 + 依赖 + 骨架
    python -m zpull modules/led bsp/bsp_i2c    # 拉多个
    python -m zpull --config modules.yaml      # 指定配置文件
"""

import argparse, sys
from pathlib import Path
from .utils import load_yaml, rmtree
from .repo import Repo
from .resolver import resolve_deps
from .extractor import extract_to


def build_sparse_list(args_paths, always, sparse_default):
    paths = list(args_paths)
    for a in always:
        if a not in paths:
            paths.append(a)
    print(f"  拉取指定路径 + 骨架: {paths}")
    return paths


def main():
    parser = argparse.ArgumentParser(description="模块依赖管理")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--tag", default=None, help="从指定标签完整拉取")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    cfg_path = Path(args.config) if args.config else root / "modules.yaml"
    if not cfg_path.exists():
        print(f"错误: 找不到 {cfg_path}")
        sys.exit(1)

    tmp = root / ".tmp_clone"

    # --- --tag 模式: 从指定标签完整拉取 ---
    if args.tag:
        tag = args.tag
        mod = load_yaml(cfg_path).get("modules", [None])[0]
        if not mod:
            print("错误: modules.yaml 中没有模块定义")
            sys.exit(1)
        extract = mod.get("extract", {})
        if tmp.exists():
            rmtree(tmp)
        repo = Repo(mod["repo"], tag, tmp)
        print(f"[tag] 从标签 '{tag}' 完整拉取")
        repo.clone_full()
        extract_to(tmp, root, extract)
        rmtree(tmp)
        print(f"  [clean] 临时目录已删除")
        print("\n=== 完成 ===")
        return

    # --- 模块模式: sparse checkout + 依赖解析 ---
    for i, mod in enumerate(load_yaml(cfg_path).get("modules", [])):
        always  = mod.get("always", []) or []
        extract = mod.get("extract", {})

        if not args.paths:
            sparse = mod.get("sparse", None)
            if extract and all((root / d).exists() for d in extract.values()):
                print(f"[{i+1}] 所有目标已存在, 跳过")
                continue
        else:
            sparse = build_sparse_list(args.paths, always, None)

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
        try:
            for t in targets:
                resolve_deps(t, repo, resolved, [])
        except Exception as e:
            print(f"  [WARN] 依赖解析异常: {e}")
        print(f"  共 {len(resolved)} 个模块解析完成")

        shallow = set(mod.get("shallow", [])) if not args.paths else None
        extract_to(tmp, root, extract, shallow_dirs=shallow)
        rmtree(tmp)
        print(f"  [clean] 临时目录已删除")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
