import sys
from pathlib import Path

import setuptools


def test_setup_py_can_import_local_build_support_without_repo_on_sys_path():
    project_root = Path(__file__).resolve().parents[2]
    setup_py = project_root / "setup.py"
    original_sys_path = list(sys.path)
    original_setup = setuptools.setup

    try:
        sys.path = [entry for entry in sys.path if entry and str(project_root) not in entry]
        setuptools.setup = lambda *args, **kwargs: None

        namespace = {"__file__": str(setup_py), "__name__": "__main__"}
        exec(compile(setup_py.read_text(), str(setup_py), "exec"), namespace)
    finally:
        sys.path = original_sys_path
        setuptools.setup = original_setup
