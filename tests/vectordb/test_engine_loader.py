import importlib.util
import unittest
from pathlib import Path


def load_engine_loader_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "openviking" / "storage" / "vectordb" / "engine.py"
    spec = importlib.util.spec_from_file_location("vectordb_engine_loader_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EngineLoaderSelectionTests(unittest.TestCase):
    def test_selects_avx512_before_avx2(self):
        module = load_engine_loader_module()

        selected = module._select_x86_variant(
            {"avx2", "avx512f", "avx512bw", "avx512dq", "avx512vl"},
            ["sse3", "avx2", "avx512"],
        )

        self.assertEqual(selected, "avx512")

    def test_falls_back_to_avx2_when_avx512_is_incomplete(self):
        module = load_engine_loader_module()

        selected = module._select_x86_variant(
            {"avx2", "avx512f", "avx512bw"},
            ["sse3", "avx2", "avx512"],
        )

        self.assertEqual(selected, "avx2")

    def test_uses_sse3_as_baseline(self):
        module = load_engine_loader_module()

        selected = module._select_x86_variant({"sse3"}, ["sse3", "avx2"])

        self.assertEqual(selected, "sse3")

    def test_raises_when_no_supported_variant_is_available(self):
        module = load_engine_loader_module()

        with self.assertRaises(ImportError):
            module._select_x86_variant(set(), ["sse3", "avx2"])


if __name__ == "__main__":
    unittest.main()
