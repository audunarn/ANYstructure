import numpy as np
import pytest

from anystruct.ge_beam3_optin import (
    B3GERuntimeDefinition,
    B3_GE_SELECTION_SCHEMA,
    BeamRuntimeSelection,
    GeBeam3RuntimeDefinition,
    b3_ge_runtime_status,
    launch_beam_runtime,
    runtime_status,
)
from anysolver._ge_beam3_native_analysis import NativeBeamAnalysis
from anysolver.ge_beam3_element import GeometricallyExactBeam3D3NElement


def test_runtime_ge_beam3_is_exact_explicit_and_descriptive():
    definition = GeBeam3RuntimeDefinition(np.diag((10., 11., 12., 13., 14., 15.)),
                                          np.diag((2., 2., 2., .1, .2, .3)),
                                          (0., 1., 0.))
    element = definition.build(1, (1, 2, 3), "steel")
    assert type(element) is GeometricallyExactBeam3D3NElement
    status = runtime_status(definition)
    assert status["beam_element"] == "GE-B3 straight — mixed Simo–Reissner"
    assert status["explicit_opt_in"] is True and status["default_changed"] is False


def test_runtime_b3_ge_is_native_explicit_and_legacy_b3_stays_default():
    from anysolver import b3_ge
    from anysolver.boundary import BoundaryCondition
    from anysolver.elements import QuadraticBeamElement, create_element

    section = b3_ge.EllipsoidalGeneralizedSection(
        np.diag((10.0, 11.0, 12.0, 13.0, 14.0, 15.0)), np.eye(6), 1.0e6, 1.0
    )
    native = b3_ge.define_beam(
        b3_ge.SELECTOR, 1, (1, 2, 3),
        np.array(((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0))),
        np.repeat(np.eye(3)[None, :, :], 3, axis=0), section,
        np.diag((2.0, 2.0, 2.0, 0.07, 0.09, 0.11)),
    )
    restored = B3GERuntimeDefinition.from_dict(B3GERuntimeDefinition((native,)).to_dict())
    owner = restored.create_analysis((BoundaryCondition(
        "fixed", [1], {"ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}
    ),))
    status = b3_ge_runtime_status(restored)
    assert owner.identity
    assert status["beam_element"] == "B3-GE — geometrically exact Simo–Reissner"
    assert status["selector"] == "b3-ge"
    assert status["selection"] == "explicit opt-in"
    assert status["legacy_b3_default"] is True and status["default_changed"] is False
    assert type(create_element("quadratic_beam", 99, [1, 2, 3])) is QuadraticBeamElement
    oversized = B3GERuntimeDefinition((native,)).to_dict()
    oversized["definitions"][0]["raw_base64"] = "a" * 2_800_001
    with pytest.raises(ValueError, match="bounded"):
        B3GERuntimeDefinition.from_dict(oversized)


def test_bounded_launcher_distinguishes_explicit_b3_ge_from_migrated_legacy_default():
    from anysolver import b3_ge
    from anysolver._ge_beam3_native_definition import NativeBeamDefinition
    from anysolver.boundary import BoundaryCondition
    from anysolver.elements import QuadraticBeamElement

    default_legacy = launch_beam_runtime(
        element_id=19, node_ids=(1, 2, 3), material_name="steel"
    )
    assert type(default_legacy) is QuadraticBeamElement

    historical_project = {"beam_element_order": "B3"}
    migrated = BeamRuntimeSelection.from_project_options(historical_project)
    assert migrated.selector == "b3"
    legacy = launch_beam_runtime(
        migrated, element_id=20, node_ids=(1, 2, 3), material_name="steel"
    )
    assert type(legacy) is QuadraticBeamElement

    section = b3_ge.EllipsoidalGeneralizedSection(
        np.diag((10.0, 11.0, 12.0, 13.0, 14.0, 15.0)), np.eye(6), 1.0e6, 1.0
    )
    native = b3_ge.define_beam(
        b3_ge.SELECTOR,
        21,
        (1, 2, 3),
        np.array(((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0))),
        np.repeat(np.eye(3)[None, :, :], 3, axis=0),
        section,
        np.diag((2.0, 2.0, 2.0, 0.07, 0.09, 0.11)),
    )
    assert type(native) is NativeBeamDefinition
    explicit_record = {
        "schema": B3_GE_SELECTION_SCHEMA,
        "beam_formulation": "b3-ge",
    }
    explicit = BeamRuntimeSelection.from_project_options(explicit_record)
    assert BeamRuntimeSelection.from_project_options(explicit.to_dict()) == explicit
    owner = launch_beam_runtime(
        explicit,
        element_id=21,
        node_ids=(1, 2, 3),
        b3_ge_definition=B3GERuntimeDefinition((native,)),
        boundaries=(BoundaryCondition(
            "fixed", [1],
            {"ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0},
        ),),
    )
    assert type(owner) is NativeBeamAnalysis
    assert explicit.explicit_b3_ge is True
    assert type(owner) is not type(legacy)

    with pytest.raises(ValueError, match="versioned schema"):
        BeamRuntimeSelection.from_project_options({"beam_formulation": "b3-ge"})
    with pytest.raises(ValueError, match="complete native definition"):
        launch_beam_runtime(
            explicit, element_id=21, node_ids=(1, 2, 3), b3_ge_definition=None
        )
