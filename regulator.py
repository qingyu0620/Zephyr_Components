#!/usr/bin/env python3
"""
轻量模块依赖管理: 读取 modules.yaml, 克隆仓库并将指定目录提取到项目根.

用法:
    python mod_init.py                       # 拉取 modules.yaml 中声明的所有模块
    python mod_init.py empty_project         # 只拉项目骨架 (always 列表)
    python mod_init.py modules/led           # 只拉 modules/led 及其依赖
    python mod_init.py bsp/bsp_uart          # 只拉 bsp/bsp_uart
    python mod_init.py modules/led bsp/bsp_i2c  # 拉多个
    python mod_init.py --config modules.yaml # 指定配置文件

流程:
  1. 克隆仓库到临时目录 (支持 sparse checkout)
  2. 读取 module.yaml 递归解析内部依赖, 追加 sparse 路径
  3. 将 extract 指定的目录移动/合并到项目根
  4. 删除临时目录

modules.yaml 示例:
    modules:
      - repo: git@github.com:user/Components.git
        ref: main
        sparse: [modules/led, modules/key]   # 初始只拉这些
        extract:                              # 移动到项目根
          bsp: bsp                            # 仓库内 bsp/ -> 项目根 bsp/
          modules: modules                    # 仓库内 modules/ -> 项目根 modules/

module.yaml 示例 (仓库内各模块):
    name: led
    depends:
      - path: bsp/bsp_gpio                   # 内部依赖, 自动追加 sparse
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("需要 pyyaml: pip install pyyaml")
    sys.exit(1)


def rmtree(path: Path):
    """删除目录树, 处理 git 只读文件."""
    def on_error(func, fpath, _exc_info):
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)
    shutil.rmtree(str(path), onerror=on_error)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_git(args: list, cwd: str = None):
    subprocess.run(
        ["git"] + args, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=cwd
    )


def find_project_root(start: Path) -> Path:
    current = start
    for _ in range(10):
        if (current / "CMakeLists.txt").exists() and (current / "prj.conf").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return start


def sparse_checkout_add(clone_dir: Path, paths: list):
    """向已有 sparse checkout 仓库追加路径."""
    existing = subprocess.run(
        ["git", "sparse-checkout", "list"],
        capture_output=True, text=True, cwd=str(clone_dir)
    )
    existing_dirs = set(existing.stdout.strip().splitlines()) if existing.returncode == 0 else set()
    new_dirs = set(paths) - existing_dirs
    if not new_dirs:
        return
    all_dirs = sorted(existing_dirs | new_dirs)
    print(f"  [sparse+] +{sorted(new_dirs)}")
    run_git(["sparse-checkout", "set"] + all_dirs, cwd=str(clone_dir))
    run_git(["checkout"], cwd=str(clone_dir))


def resolve_deps(module_dir: Path, clone_dir: Path, resolved: set, chain: list):
    """递归解析 module.yaml 中的内部依赖, 追加 sparse checkout."""
    module_yaml = module_dir / "module.yaml"
    if not module_yaml.exists():
        return

    cfg = load_yaml(module_yaml)
    mod_name = cfg.get("name", module_dir.name)

    if mod_name in resolved:
        return
    resolved.add(mod_name)

    deps = cfg.get("depends", []) or []
    for dep in deps:
        if "path" not in dep:
            continue
        dep_path = dep["path"]
        print(f"  依赖: {' -> '.join(chain + [mod_name])} -> {dep_path}")
        sparse_checkout_add(clone_dir, [dep_path])
        resolve_deps(clone_dir / dep_path, clone_dir, resolved, chain + [mod_name])


def merge_dirs(src: Path, dest: Path):
    """将 src 目录内容合并到 dest, 只添加不存在的子目录."""
    for child in src.iterdir():
        target = dest / child.name
        if target.exists():
            continue
        shutil.move(str(child), str(target))


def main():
    parser = argparse.ArgumentParser(description="模块依赖管理")
    parser.add_argument("paths", nargs="*", help="要拉取的仓库内路径, 如 modules/led bsp/bsp_uart")
    parser.add_argument("--config", default=None, help="modules.yaml 路径")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = find_project_root(script_dir)

    config_path = Path(args.config) if args.config else project_root / "modules.yaml"
    if not config_path.exists():
        print(f"错误: 找不到 {config_path}")
        sys.exit(1)

    cfg = load_yaml(config_path)
    modules = cfg.get("modules", []) or []
    if not modules:
        print("modules.yaml 中没有声明模块")
        return

    tmp_dir = project_root / ".tmp_clone"

    for i, mod in enumerate(modules):
        repo = mod["repo"]
        ref = mod.get("ref", "main")
        sparse = mod.get("sparse", None)
        always = mod.get("always", []) or []
        extract = mod.get("extract", {})

        # 确定要拉的 sparse 路径
        is_empty_project = args.paths == ["empty_project"]

        if is_empty_project:
            # empty_project: 只拉 always 列表中的项目骨架
            sparse = list(always)
            print(f"[{i+1}] empty_project: 拉取项目骨架 {sparse}")
        elif args.paths:
            # 指定了具体路径, 覆盖 yaml 中的 sparse
            sparse = list(args.paths)
            print(f"[{i+1}] 拉取指定路径: {sparse}")
        else:
            # 检查 extract 目标是否已存在
            all_exist = all((project_root / dest).exists() for dest in extract.values())
            if extract and all_exist:
                print(f"[{i+1}] 所有目标目录已存在, 跳过")
                continue

        print(f"[{i+1}] 克隆 {repo}")

        # 清理临时目录
        if tmp_dir.exists():
            rmtree(tmp_dir)

        # 克隆
        if sparse:
            print(f"  sparse: {sparse}")
            clone_cmd = ["clone", "--no-checkout", "--depth", "1", "--filter=blob:none"]
            if ref:
                clone_cmd += ["--branch", ref]
            clone_cmd += [repo, str(tmp_dir)]
            run_git(clone_cmd)
            run_git(["sparse-checkout", "init", "--cone"], cwd=str(tmp_dir))
            run_git(["sparse-checkout", "set"] + sparse, cwd=str(tmp_dir))
            run_git(["checkout"], cwd=str(tmp_dir))
        else:
            clone_cmd = ["clone", "--depth", "1"]
            if ref:
                clone_cmd += ["--branch", ref]
            clone_cmd += [repo, str(tmp_dir)]
            run_git(clone_cmd)

        # 解析依赖, 可能追加 sparse 路径
        resolved: set = set()
        if sparse:
            for sub in sparse:
                sub_dir = tmp_dir / sub
                resolve_deps(sub_dir, tmp_dir, resolved, [])
        else:
            for child in tmp_dir.iterdir():
                if child.is_dir() and child.name != ".git":
                    resolve_deps(child, tmp_dir, resolved, [])

        print(f"  共 {len(resolved)} 个模块解析完成")

        # 移动/合并 extract 指定的目录/文件到项目根
        for src_name, dest_name in extract.items():
            src_path = tmp_dir / src_name
            dest_path = project_root / dest_name
            if not src_path.exists():
                continue
            if dest_path.exists():
                if src_path.is_dir():
                    merge_dirs(src_path, dest_path)
                    print(f"  [merge] {src_name}/ -> {dest_name}/")
                else:
                    print(f"  [skip] {dest_name} 已存在")
            else:
                shutil.move(str(src_path), str(dest_path))
                suffix = "/" if src_path.is_dir() else ""
                print(f"  [extract] {src_name}{suffix} -> {dest_name}{suffix}")

        # 清理临时目录
        rmtree(tmp_dir)
        print(f"  [clean] 临时目录已删除")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
