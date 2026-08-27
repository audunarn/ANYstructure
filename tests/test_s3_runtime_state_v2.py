"""Fast formulation-authority checks for ANYstructure runtime-state v2."""

from __future__ import annotations

import json

import pytest

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
