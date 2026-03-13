import unittest


class ResolveEngineExtensionPlanTests(unittest.TestCase):
    def test_portable_x86_build_emits_all_runtime_variants(self):
        from build_support.vectordb_engine_variants import resolve_engine_extension_plan

        plan = resolve_engine_extension_plan(
            platform="linux",
            machine="x86_64",
            x86_build_profile="portable",
        )

        self.assertEqual(
            [variant.module_name for variant in plan.variants],
            [
                "openviking.storage.vectordb._engine_sse3",
                "openviking.storage.vectordb._engine_avx2",
                "openviking.storage.vectordb._engine_avx512",
            ],
        )
        self.assertEqual(plan.loader_module_name, "openviking.storage.vectordb.engine")

    def test_fixed_x86_build_only_emits_requested_variant(self):
        from build_support.vectordb_engine_variants import resolve_engine_extension_plan

        plan = resolve_engine_extension_plan(
            platform="linux",
            machine="x86_64",
            x86_build_profile="fixed",
            x86_simd_level="AVX2",
        )

        self.assertEqual(
            [variant.module_name for variant in plan.variants],
            ["openviking.storage.vectordb._engine_avx2"],
        )

    def test_non_x86_build_uses_single_engine_module(self):
        from build_support.vectordb_engine_variants import resolve_engine_extension_plan

        plan = resolve_engine_extension_plan(
            platform="darwin",
            machine="arm64",
            x86_build_profile="portable",
        )

        self.assertEqual(
            [variant.module_name for variant in plan.variants],
            ["openviking.storage.vectordb._engine_native"],
        )


if __name__ == "__main__":
    unittest.main()
