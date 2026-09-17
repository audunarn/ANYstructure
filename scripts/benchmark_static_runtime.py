"""Bounded complete-path benchmark for ANYstructure linear-static analysis."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import time

from anystruct import fem_integration
from anysolver import runtime as fe_solver


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))]


def _summary(values: list[float]) -> dict[str, object]:
    median = statistics.median(values)
    return {
        "values_seconds": values,
        "median_seconds": median,
        "mad_seconds": statistics.median(abs(value - median) for value in values),
        "p95_seconds": _percentile_95(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh-fidelity", choices=("coarse", "medium", "fine"), default="coarse")
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--load-cases", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1 or args.load_cases < 1:
        parser.error("repetitions and load-cases must be positive")

    app = fem_integration.example_runtime_app("girder_panel")
    snapshot = fem_integration.active_line_snapshot(app)
    pressure = float(snapshot.pressure_pa or 100_000.0)
    options = fem_integration.RuntimeFEMOptions(
        mesh_fidelity=args.mesh_fidelity,
        pressure_pa=pressure,
        include_stiffeners=True,
        include_girders=True,
        include_end_lids=True,
        analysis_type="linear static",
        runtime_solver="static only",
        num_buckling_modes=0,
    )
    geometry = fem_integration.runtime_geometry_summary(snapshot, options)
    solver_config = fem_integration._solver_config_from_options(options)
    generated = fem_integration.build_runtime_generated_geometry(
        fem_integration.runtime_geometry_projection(geometry, solver_config),
        solver_config,
    )

    complete: list[float] = []
    last_result = None
    for _ in range(args.repetitions + 1):
        started = time.perf_counter()
        result = fem_integration.run_runtime_fem(
            snapshot,
            options,
            precomputed_generated_geometry=generated,
            precomputed_geometry_is_imperfection=False,
        )
        elapsed = time.perf_counter() - started
        if result.status != "ok":
            raise RuntimeError("complete-path benchmark failed: " + result.status)
        if complete or last_result is not None:
            complete.append(elapsed)
        last_result = result

    context = fe_solver.RuntimeAnalysisContext()
    repeated: list[float] = []
    try:
        # Populate prepared model, structural plans and numerical factor once.
        warm = fem_integration.run_runtime_fem(
            snapshot,
            options,
            precomputed_generated_geometry=generated,
            precomputed_geometry_is_imperfection=False,
            analysis_context=context,
        )
        if warm.status != "ok":
            raise RuntimeError("context warm-up failed: " + warm.status)
        count = max(args.repetitions, args.load_cases)
        for index in range(count):
            factor = 0.5 + 1.5 * ((index % args.load_cases) / max(1, args.load_cases - 1))
            load_options = replace(options, pressure_pa=pressure * factor)
            started = time.perf_counter()
            result = fem_integration.run_runtime_fem(
                snapshot,
                load_options,
                precomputed_generated_geometry=generated,
                precomputed_geometry_is_imperfection=False,
                analysis_context=context,
            )
            elapsed = time.perf_counter() - started
            if result.status != "ok":
                raise RuntimeError("retained-path benchmark failed: " + result.status)
            if index < args.repetitions:
                repeated.append(elapsed)
            last_result = result
        context_diagnostics = context.diagnostics()
    finally:
        context.close()

    mesh = dict((last_result.summary or {}).get("mesh_info") or {})
    performance = dict(
        ((last_result.summary or {}).get("prestress_summary") or {}).get("performance")
        or {}
    )
    payload = {
        "schema": "anystructure-static-runtime-benchmark-v1",
        "fixture": "girder_panel",
        "mesh_fidelity": args.mesh_fidelity,
        "mesh": mesh,
        "complete": _summary(complete),
        "retained_load_only": _summary(repeated),
        "runtime_performance": performance,
        "runtime_context": context_diagnostics,
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
