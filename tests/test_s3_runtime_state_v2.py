"""Fast formulation-authority checks for ANYstructure runtime-state v2."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from anysolver import LegacyShellElement, create_shell_element

from anystruct import fem_integration


def test_new_runtime_state_binds_qualified_s3_and_physical_normal_authority() -> None:
    state = fem_integration.runtime_fem_state_to_dict(
        fem_integration.RuntimeFEMOptions()
    )

    assert state["format"] == "anystructure-runtime-fem-state-v2"
    assert state["shell_authority"] == {
        "schema": "anystructure-runtime-shell-authority-v2",
        "q4_formulation": "e4-pl",
        "q4_formulation_id": "E4_PL_QUALIFIED_Q4_HYBRID_V2",
        "s3_formulation": "e4-pl-s3",
        "s3_formulation_id": "E4_PL_QUALIFIED_S3_COMPANION_V1",
        "physical_normal_authority": "PHYSICAL_SURFACE_OWNER_NORMAL_V1",
        "migration_disposition": "CURRENT_POLICY",
    }


def test_runtime_fem_v1_migrates_s3_to_explicit_legacy_without_hot_restart(
    tmp_path,
) -> None:
    path = tmp_path / "historical-v1.fem.json"
    path.write_text(
        json.dumps(
            {
                "format": "anystructure-runtime-fem-state-v1",
                "saved_utc": "2026-01-01T00:00:00Z",
                "options": {},
            }
        ),
        encoding="utf-8",
    )

    state = fem_integration.load_runtime_fem_state(path)

    assert state["format"] == "anystructure-runtime-fem-state-v2"
    assert state["source_format"] == "anystructure-runtime-fem-state-v1"
    assert state["shell_authority"]["s3_formulation"] == "legacy-s3"
    assert state["shell_authority"]["physical_normal_authority"] == (
        "ABSENT_HISTORICAL_V1"
    )
    assert "NO_HOT_RESTART" in state["shell_authority"]["migration_disposition"]
    assert state["migration_diagnostics"]
    assert not fem_integration.runtime_shell_authority_allows_hot_restart(
        state["shell_authority"]
    )


def test_migrated_v1_authority_round_trips_as_legacy_v2(tmp_path) -> None:
    original = tmp_path / "historical-v1.fem.json"
    original.write_text(
        json.dumps(
            {
                "format": "anystructure-runtime-fem-state-v1",
                "saved_utc": "2026-01-01T00:00:00Z",
                "options": {},
            }
        ),
        encoding="utf-8",
    )
    migrated = fem_integration.load_runtime_fem_state(original)
    saved = tmp_path / "migrated-v2.fem.json"

    fem_integration.save_runtime_fem_state(
        saved,
        migrated["options"],
        shell_authority=migrated["shell_authority"],
    )
    restored = fem_integration.load_runtime_fem_state(saved)

    assert restored["source_format"] == "anystructure-runtime-fem-state-v2"
    assert restored["shell_authority"] == migrated["shell_authority"]
    assert restored["migration_diagnostics"]
    assert not fem_integration.runtime_shell_authority_allows_hot_restart(
        restored["shell_authority"]
    )


def test_runtime_window_refuses_migrated_v1_hot_restart(monkeypatch) -> None:
    window = object.__new__(fem_integration.RuntimeFEMWindow)
    window.solver_thread = None
    window._loaded_shell_authority = fem_integration._runtime_shell_authority(
        migrated_v1=True
    )
    statuses: list[tuple[str, bool]] = []
    errors: list[tuple[str, str]] = []
    window._write_status = lambda text, keep_run_results=False: statuses.append(
        (text, keep_run_results)
    )
    monkeypatch.setattr(
        fem_integration.messagebox,
        "showerror",
        lambda title, text: errors.append((title, text)),
    )

    window.run()

    assert len(statuses) == 1
    assert statuses[0][1] is True
    assert "cannot be hot-restarted" in statuses[0][0]
    assert errors == [("FEM solver", statuses[0][0])]


@pytest.mark.parametrize(
    "payload",
    (
        '{"format":"anystructure-runtime-fem-state-v2","format":"duplicate"}',
        '{"format":"anystructure-runtime-fem-state-v2","value":NaN}',
    ),
)
def test_runtime_fem_state_rejects_duplicate_keys_and_nonfinite_json(
    tmp_path, payload,
) -> None:
    path = tmp_path / "malformed.fem.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError):
        fem_integration.load_runtime_fem_state(path)


def test_runtime_state_rejects_forged_current_s3_identity(tmp_path) -> None:
    state = fem_integration.runtime_fem_state_to_dict(
        fem_integration.RuntimeFEMOptions()
    )
    state["shell_authority"]["s3_formulation_id"] = "FORGED"
    path = tmp_path / "forged.fem.json"
    path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="shell authority is incompatible"):
        fem_integration.load_runtime_fem_state(path)


def _imported_model_with(element):
    return SimpleNamespace(mesh=SimpleNamespace(elements={1: element}))


def test_imported_qualified_s3_with_physical_normal_retains_current_authority() -> None:
    element = create_shell_element(
        1,
        [1, 2, 3],
        formulation="e4-pl-s3",
        reference_normal=(0.0, 0.0, 1.0),
    )

    authority = fem_integration._imported_model_shell_authority(
        _imported_model_with(element)
    )

    assert authority == fem_integration._runtime_shell_authority()
    assert fem_integration.runtime_shell_authority_allows_hot_restart(authority)


def test_imported_missing_id_s3_saves_and_reloads_as_no_restart_legacy(
    tmp_path,
) -> None:
    legacy = LegacyShellElement(1, [1, 2, 3])
    # Formulation-like instance fields cannot turn the wrong concrete class
    # into qualified authority.
    legacy.formulation_id = "E4_PL_QUALIFIED_S3_COMPANION_V1"
    legacy.reference_normal = (0.0, 0.0, 1.0)
    authority = fem_integration._imported_model_shell_authority(
        _imported_model_with(legacy)
    )
    path = tmp_path / "imported-legacy.fem.json"

    fem_integration.save_runtime_fem_state(
        path,
        fem_integration.RuntimeFEMOptions(),
        shell_authority=authority,
    )
    restored = fem_integration.load_runtime_fem_state(path)

    assert restored["shell_authority"]["s3_formulation"] == "legacy-s3"
    assert restored["shell_authority"]["physical_normal_authority"] == (
        "UNPROVEN_IMPORTED_MODEL"
    )
    assert restored["migration_diagnostics"] == [
        "IMPORTED_MODEL_S3_RETAINED_AS_EXPLICIT_LEGACY: qualified-S3 "
        "physical-normal authority was not proven; hot restart is forbidden"
    ]
    assert not fem_integration.runtime_shell_authority_allows_hot_restart(
        restored["shell_authority"]
    )


def test_malformed_imported_model_cannot_claim_current_shell_authority() -> None:
    authority = fem_integration._imported_model_shell_authority(
        SimpleNamespace(mesh=SimpleNamespace(elements=None))
    )

    assert authority == fem_integration._runtime_shell_authority(
        imported_legacy=True
    )
