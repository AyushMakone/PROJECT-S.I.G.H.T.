# Root conftest.py — Project S.I.G.H.T. Master Test Configuration
# Bootstraps all Python packages so tests can import cleanly.

import sys
import os
import importlib.util

ROOT = os.path.dirname(os.path.abspath(__file__))


def _bootstrap_pkg(pkg_name: str, pkg_dir: str):
    """Register pkg_dir as a top-level Python package named pkg_name."""
    if pkg_name in sys.modules:
        return
    init = os.path.join(pkg_dir, "__init__.py")
    if not os.path.exists(init):
        return
    spec = importlib.util.spec_from_file_location(
        pkg_name, init, submodule_search_locations=[pkg_dir]
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__path__ = [pkg_dir]
    mod.__package__ = pkg_name
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    # Register all direct sub-packages
    for sub in os.listdir(pkg_dir):
        sub_dir = os.path.join(pkg_dir, sub)
        sub_init = os.path.join(sub_dir, "__init__.py")
        if not os.path.isdir(sub_dir) or not os.path.exists(sub_init):
            continue
        if sub.startswith((".", "_")) or sub in ("tests",):
            continue
        full = f"{pkg_name}.{sub}"
        if full in sys.modules:
            continue
        s = importlib.util.spec_from_file_location(
            full, sub_init, submodule_search_locations=[sub_dir]
        )
        m = importlib.util.module_from_spec(s)
        m.__path__ = [sub_dir]
        m.__package__ = full
        sys.modules[full] = m
        s.loader.exec_module(m)


# Bootstrap S.I.G.H.T. Core (directory has hyphen, package uses underscore)
_bootstrap_pkg("sight_core", os.path.join(ROOT, "sight-core"))

# Bootstrap other project packages (standard directory names)
for _pkg in ("simulator", "backend", "communication"):
    _pkg_dir = os.path.join(ROOT, _pkg)
    if os.path.isdir(_pkg_dir):
        _bootstrap_pkg(_pkg, _pkg_dir)

# Ensure ROOT is on sys.path for any remaining absolute imports
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
