from __future__ import annotations

from dataclasses import dataclass

_PORTABLE_X86_VARIANTS = ("sse3", "avx2", "avx512")
_FIXED_SIMD_VARIANTS = {"SSE3": "sse3", "AVX2": "avx2", "AVX512": "avx512", "NATIVE": "native"}


@dataclass(frozen=True)
class EngineVariant:
    variant_name: str
    module_name: str
    target_name: str
    simd_level: str
    internal_module_name: str


@dataclass(frozen=True)
class EngineExtensionPlan:
    loader_module_name: str
    variants: tuple[EngineVariant, ...]


def _is_x86_machine(machine: str) -> bool:
    normalized = machine.strip().lower()
    return normalized in {"x86_64", "amd64", "i386", "i686"}


def _variant_module_name(variant: str) -> str:
    return f"openviking.storage.vectordb._engine_{variant}"


def _variant_target_name(variant: str) -> str:
    return f"engine_{variant}"


def _variant_spec(variant: str) -> EngineVariant:
    return EngineVariant(
        variant_name=variant,
        module_name=_variant_module_name(variant),
        target_name=_variant_target_name(variant),
        simd_level=variant.upper(),
        internal_module_name=f"_engine_{variant}",
    )


def resolve_engine_extension_plan(
    *,
    platform: str,
    machine: str,
    x86_build_profile: str,
    x86_simd_level: str | None = None,
) -> EngineExtensionPlan:
    del platform
    loader_module_name = "openviking.storage.vectordb.engine"
    normalized_profile = x86_build_profile.strip().lower()

    if not _is_x86_machine(machine):
        return EngineExtensionPlan(
            loader_module_name=loader_module_name,
            variants=(
                EngineVariant(
                    variant_name="native",
                    module_name="openviking.storage.vectordb._engine_native",
                    target_name="engine_native",
                    simd_level="DEFAULT",
                    internal_module_name="_engine_native",
                ),
            ),
        )

    if normalized_profile == "portable":
        variants = tuple(_variant_spec(variant) for variant in _PORTABLE_X86_VARIANTS)
        return EngineExtensionPlan(loader_module_name=loader_module_name, variants=variants)

    normalized_level = (x86_simd_level or "AVX2").strip().upper()
    variant = _FIXED_SIMD_VARIANTS[normalized_level]
    return EngineExtensionPlan(
        loader_module_name=loader_module_name,
        variants=(_variant_spec(variant),),
    )
