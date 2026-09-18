# conftest.py — Makes 'sight_core' importable from the 'sight-core' directory.
# Also prevents pytest from treating __init__.py as a test module.

import sys
import os
import importlib.util

# Path to sight-core directory (parent of tests/)
SIGHT_CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(SIGHT_CORE_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SIGHT_CORE_DIR not in sys.path:
    sys.path.insert(0, SIGHT_CORE_DIR)

# Tell pytest to ignore __init__.py files - they are package files, not test files
collect_ignore = [os.path.join(SIGHT_CORE_DIR, "__init__.py")]
collect_ignore_glob = ["*/__init__.py"]


def _bootstrap_sight_core(pkg_name: str, pkg_dir: str):
    """Register pkg_dir as the 'sight_core' top-level package."""
    if pkg_name in sys.modules:
        return

    spec = importlib.util.spec_from_file_location(
        pkg_name,
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    pkg_mod = importlib.util.module_from_spec(spec)
    pkg_mod.__path__ = [pkg_dir]
    pkg_mod.__package__ = pkg_name
    sys.modules[pkg_name] = pkg_mod
    spec.loader.exec_module(pkg_mod)

    # Register all direct sub-packages
    for sub_name in os.listdir(pkg_dir):
        sub_dir = os.path.join(pkg_dir, sub_name)
        sub_init = os.path.join(sub_dir, "__init__.py")
        if not os.path.isdir(sub_dir) or not os.path.exists(sub_init):
            continue
        if sub_name.startswith((".", "_")) or sub_name == "tests":
            continue

        full_name = f"{pkg_name}.{sub_name}"
        if full_name in sys.modules:
            continue

        sub_spec = importlib.util.spec_from_file_location(
            full_name,
            sub_init,
            submodule_search_locations=[sub_dir],
        )
        sub_mod = importlib.util.module_from_spec(sub_spec)
        sub_mod.__path__ = [sub_dir]
        sub_mod.__package__ = full_name
        sys.modules[full_name] = sub_mod
        sub_spec.loader.exec_module(sub_mod)


_bootstrap_sight_core("sight_core", SIGHT_CORE_DIR)
