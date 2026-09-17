"""Bounded complete-path benchmark for modal and buckling performance."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import statistics
import time

from anystruct import fem_integration
from anysolver import AnalysisSession, solve_free_vibration
from anysolver import anystructure_fem_mode as backend
from anysolver.runtime import RuntimeAnalysisContext


def _summary(values: list[float]) -> dict[str, object]:
    ordered = sorted(values)
    median = statistics.median(values)
    return {
        "values_seconds": values,
        "median_seconds": median,
        "mad_seconds": statistics.median(abs(value - median) for value in values),
        "p95_seconds": ordered[max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))],
    }


def _peak_rss_bytes() -> int:
    if os.name == "nt":
        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        get_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        get_memory_info.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        if get_memory_info(
            get_current_process(),
            ctypes.byref(counters),
            counters.cb,
        ):
            return int(counters.PeakWorkingSetSize)
        return 0
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if os.uname().sysname == "Darwin" else value * 1024
    except (AttributeError, ImportError):
        return 0


def _scientific_consistency(
    records: list[list[float]],
    *,
    requested_modes: int,
) -> dict[str, object]:
    if not records:
        raise RuntimeError("spectral benchmark produced no scientific records")
    if any(len(record) != requested_modes for record in records):
        counts = [len(record) for record in records]
        raise RuntimeError(
            f"spectral benchmark requested {requested_modes} modes but returned {counts}"
        )
    reference = records[0]
    max_relative_spread = 0.0
    for record in records[1:]:
        for expected, actual in zip(reference, record):
            scale = max(abs(expected), abs(actual), 1.0)
            max_relative_spread = max(
                max_relative_spread,
                abs(actual - expected) / scale,
            )
            if not math.isclose(
                actual,
                expected,
                rel_tol=1.0e-10,
                abs_tol=1.0e-12 * scale,
            ):
                raise RuntimeError(
                    "spectral benchmark scientific results changed across repetitions"
                )
    return {
        "verified": True,
        "records": len(records),
        "requested_modes": requested_modes,
        "max_relative_spread": max_relative_spread,
    }


def _fixture(mesh_fidelity: str, modes: int):
    app = fem_integration.example_runtime_app("girder_panel")
    snapshot = fem_integration.active_line_snapshot(app)
    options = fem_integration.RuntimeFEMOptions(
        mesh_fidelity=mesh_fidelity,
        pressure_pa=float(snapshot.pressure_pa or 100_000.0),
        include_stiffeners=True,
        include_girders=True,
        include_end_lids=True,
        analysis_type="linear static + eigenvalue",
        runtime_solver="stepwise",
        num_buckling_modes=modes,
    )
    geometry = fem_integration.runtime_geometry_summary(snapshot, options)
    config = fem_integration._solver_config_from_options(options)
    generated = fem_integration.build_runtime_generated_geometry(
        fem_integration.runtime_geometry_projection(geometry, config),
        config,
    )
    return snapshot, options, config, generated


def _modal_model(config, generated):
    backend_config = backend.AnyStructureFEMConfig(
        pressure_pa=abs(float(config.pressure_pa)),
        pressure_sign=-1.0,
        load_scale=1.0,
        num_buckling_modes=int(config.num_buckling_modes),
        solver_type="direct",
        stress_percentile=95.0,
        add_inplane_edge_loads=False,
        auto_idealize_member_plates_as_beams=True,
        exclude_idealized_member_plates=True,
        require_idealized_member_beams=False,
        elastic_modulus=float(config.elastic_modulus_pa),
        poisson_ratio=float(config.poisson_ratio),
        yield_stress=float(config.yield_stress_pa),
    )
    return backend.build_fe_model_from_generated_geometry(generated, backend_config)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", choices=("modal", "buckling"), required=True)
    parser.add_argument("--mesh-fidelity", choices=("coarse", "medium", "fine"), default="coarse")
    parser.add_argument("--modes", type=int, choices=(5, 10), default=5)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--retained", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")

    snapshot, options, config, generated = _fixture(args.mesh_fidelity, args.modes)
    elapsed: list[float] = []
    cpu_elapsed: list[float] = []
    scientific: dict[str, object] = {}
    scientific_records: list[list[float]] = []
    diagnostics: dict[str, object] = {}

    if args.route == "buckling":
        context = RuntimeAnalysisContext() if args.retained else None
        try:
            for index in range(args.repetitions + 1):
                started = time.perf_counter()
                cpu_started = time.process_time()
                result = fem_integration.run_runtime_fem(
                    snapshot,
                    options,
                    precomputed_generated_geometry=generated,
                    precomputed_geometry_is_imperfection=False,
                    analysis_context=context,
                )
                duration = time.perf_counter() - started
                if result.status != "ok":
                    raise RuntimeError(f"buckling benchmark failed: {result.status}")
                if index:
                    elapsed.append(duration)
                    cpu_elapsed.append(time.process_time() - cpu_started)
                values = [float(value) for value in result.buckling_factors]
                scientific_records.append(values)
                scientific = {"buckling_factors": values}
                prestress_summary = (
                    (result.summary or {}).get("prestress_summary") or {}
                )
                diagnostics = {
                    "complete_route": dict(
                        prestress_summary.get("performance") or {}
                    ),
                    "buckling": dict(
                        prestress_summary.get("buckling_performance") or {}
                    ),
                }
        finally:
            if context is not None:
                context.close()
    else:
        model = _modal_model(config, generated)
        session = AnalysisSession(model) if args.retained else None
        try:
            for index in range(args.repetitions + 1):
                started = time.perf_counter()
                cpu_started = time.process_time()
                result = solve_free_vibration(
                    model,
                    num_modes=args.modes,
                    session=session,
                )
                duration = time.perf_counter() - started
                if result.solver_status != "ok":
                    raise RuntimeError(f"modal benchmark failed: {result.solver_status}")
                if index:
                    elapsed.append(duration)
                    cpu_elapsed.append(time.process_time() - cpu_started)
                values = [float(value) for value in result.frequencies_hz]
                scientific_records.append(values)
                scientific = {"frequencies_hz": values}
                diagnostics = dict(result.diagnostics)
        finally:
            if session is not None:
                session.close()

    payload = {
        "schema": "anystructure-spectral-runtime-benchmark-v1",
        "fixture": "girder_panel",
        "route": args.route,
        "mesh_fidelity": args.mesh_fidelity,
        "modes": args.modes,
        "retained": bool(args.retained),
        "runtime": {
            "wall": _summary(elapsed),
            "cpu": _summary(cpu_elapsed),
            "peak_rss_bytes": _peak_rss_bytes(),
        },
        "scientific": {
            **scientific,
            "repeat_consistency": _scientific_consistency(
                scientific_records,
                requested_modes=args.modes,
            ),
        },
        "diagnostics": diagnostics,
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
