import os
import platform
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import setuptools


class SetupEngineVariantTests(TestCase):
    def _load_setup_kwargs(self, *, machine: str, env: dict[str, str] | None = None):
        project_root = Path(__file__).resolve().parents[2]
        setup_py = project_root / "setup.py"
        captured_kwargs = {}
        original_sys_path = list(sys.path)
        original_setup = setuptools.setup

        try:
            sys.path = [entry for entry in sys.path if entry and str(project_root) not in entry]
            setuptools.setup = lambda *args, **kwargs: captured_kwargs.update(kwargs)
            with patch.object(platform, "machine", return_value=machine):
                with patch.dict(os.environ, env or {}, clear=False):
                    namespace = {"__file__": str(setup_py), "__name__": "__main__"}
                    exec(compile(setup_py.read_text(), str(setup_py), "exec"), namespace)
        finally:
            sys.path = original_sys_path
            setuptools.setup = original_setup

        return captured_kwargs

    def test_portable_x86_setup_declares_all_internal_engine_variants(self):
        kwargs = self._load_setup_kwargs(machine="x86_64", env={"OV_X86_BUILD_PROFILE": "portable"})

        self.assertEqual(
            [ext.name for ext in kwargs["ext_modules"]],
            [
                "openviking.storage.vectordb._engine_sse3",
                "openviking.storage.vectordb._engine_avx2",
                "openviking.storage.vectordb._engine_avx512",
            ],
        )

    def test_non_x86_setup_declares_single_engine_extension(self):
        kwargs = self._load_setup_kwargs(machine="arm64", env={"OV_X86_BUILD_PROFILE": "portable"})

        self.assertEqual(
            [ext.name for ext in kwargs["ext_modules"]],
            ["openviking.storage.vectordb._engine_native"],
        )
