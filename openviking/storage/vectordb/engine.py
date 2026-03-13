# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib
import platform
import subprocess
import sys
from pathlib import Path

_AVX512_REQUIRED_FLAGS = frozenset({"avx512f", "avx512bw", "avx512dq", "avx512vl"})
_VARIANT_TO_MODULE = {
    "sse3": "openviking.storage.vectordb._engine_sse3",
    "avx2": "openviking.storage.vectordb._engine_avx2",
    "avx512": "openviking.storage.vectordb._engine_avx512",
}
_NON_X86_MODULE = "openviking.storage.vectordb._engine_native"
_X86_NATIVE_MODULE = "openviking.storage.vectordb._engine_native"


def _normalize_x86_flags(raw_flags: str) -> set[str]:
    normalized = raw_flags.replace(",", " ").strip().lower()
    return {flag for flag in normalized.split() if flag}


def _read_linux_x86_flags() -> set[str]:
    cpuinfo_path = Path("/proc/cpuinfo")
    if not cpuinfo_path.exists():
        return set()

    for line in cpuinfo_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "flags":
            return _normalize_x86_flags(value)
    return set()


def _read_macos_x86_flags() -> set[str]:
    flags = set()
    for key in ("machdep.cpu.features", "machdep.cpu.leaf7_features"):
        try:
            value = subprocess.check_output(["sysctl", "-n", key], text=True).strip()
        except Exception:
            continue
        flags.update(_normalize_x86_flags(value))
    return flags


def _get_x86_flags() -> set[str]:
    system = platform.system().lower()
    if system == "linux":
        return _read_linux_x86_flags()
    if system == "darwin":
        return _read_macos_x86_flags()
    return set()


def _select_x86_variant(cpu_flags: set[str], available_variants: list[str]) -> str:
    available = set(available_variants)
    if "avx512" in available and _AVX512_REQUIRED_FLAGS.issubset(cpu_flags):
        return "avx512"
    if "avx2" in available and "avx2" in cpu_flags:
        return "avx2"
    if "sse3" in available and "sse3" in cpu_flags:
        return "sse3"
    raise ImportError(
        "No compatible x86 vectordb engine module is available for this CPU; "
        "expected at least SSE3 support."
    )


def _is_x86_runtime() -> bool:
    return platform.machine().lower() in {"x86_64", "amd64", "i386", "i686"}


def _available_x86_variants() -> list[str]:
    return [
        variant for variant, module_name in _VARIANT_TO_MODULE.items() if _can_import(module_name)
    ]


def _can_import(module_name: str) -> bool:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, AttributeError, ValueError):
        return False
    return spec is not None


def _load_runtime_module():
    if not _is_x86_runtime():
        return importlib.import_module(_NON_X86_MODULE)

    available_variants = _available_x86_variants()
    if available_variants:
        selected_variant = _select_x86_variant(_get_x86_flags(), available_variants)
        return importlib.import_module(_VARIANT_TO_MODULE[selected_variant])

    if _can_import(_X86_NATIVE_MODULE):
        return importlib.import_module(_X86_NATIVE_MODULE)

    raise ImportError("No packaged vectordb engine variants were found")


def _export_runtime_module(module) -> None:
    public_names = getattr(module, "__all__", None)
    if public_names is None:
        public_names = [name for name in dir(module) if not name.startswith("_")]

    current_module = sys.modules[__name__]
    for name in public_names:
        setattr(current_module, name, getattr(module, name))
    current_module.__all__ = list(public_names)


if __package__ == "openviking.storage.vectordb":
    _export_runtime_module(_load_runtime_module())
