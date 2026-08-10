"""ANYstructure's compatibility boundary with the neutral geometry package."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from anygeometry import EntityRef, GeometryModel
from anygeometry.generators import layout

from anystruct import geometry_generators, representation_geometry


def test_representation_layout_helpers_are_anygeometry_compatibility_exports() -> None:
    """Existing imports retain behavior while ANYgeometry owns the code."""

    assert geometry_generators.GeometryModel is GeometryModel
    assert representation_geometry.positive_spacing is layout.positive_spacing
    assert (
        representation_geometry.centered_member_positions
        is layout.centered_member_positions
    )
    assert representation_geometry.centered_bay_breaks is layout.centered_bay_breaks
    assert representation_geometry.cleaned_axis_values is layout.cleanup_axis
    assert (
        representation_geometry.bay_ranges_from_support_positions
        is layout.bay_ranges
    )
    assert (
        representation_geometry.closed_loop_member_count
        is layout.closed_loop_member_count
    )


def test_representation_layout_legacy_results_remain_stable() -> None:
    assert representation_geometry.centered_member_positions(10.0, 3.0) == (
        0.5,
        3.5,
        6.5,
        9.5,
    )
    assert representation_geometry.centered_bay_breaks(10.0, 3.0) == (
        0.0,
        0.5,
        3.5,
        6.5,
        9.5,
        10.0,
    )
    assert representation_geometry.cleaned_axis_values(
        (-1.0, 0.0, 2.0, 2.0, 5.0), 4.0
    ) == (0.0, 2.0, 4.0)
    assert representation_geometry.bay_ranges_from_support_positions(
        10.0, (3.0, 7.0), 0.2
    ) == (
        (0.0, 2.9),
        (3.1, 6.9),
        (7.1, 10.0),
    )
    assert representation_geometry.closed_loop_member_count(10.0, 3.0) == 3


@pytest.mark.parametrize(
    ("adapter_name", "delegate_name", "args", "kwargs"),
    (
        ("generate_plate_geometry", "_plate", (4.0, 3.0), {"semantic_group": "deck"}),
        (
            "generate_stiffened_panel_geometry",
            "_stiffened_panel",
            (4.0, 3.0),
            {"longitudinal_spacing": 1.0, "transverse_spacing": 2.0},
        ),
        (
            "generate_cylinder_geometry",
            "_cylinder",
            (2.0, 5.0),
            {"circumferential_segments": 8, "ring_spacing": 2.5},
        ),
        (
            "generate_cone_geometry",
            "_cone",
            (2.0, 1.5, 5.0),
            {"circumferential_segments": 8, "longitudinal_spacing": 1.0},
        ),
    ),
)
def test_generator_adapters_preserve_the_exact_model_refs_and_groups(
    monkeypatch: pytest.MonkeyPatch,
    adapter_name: str,
    delegate_name: str,
    args: tuple[float, ...],
    kwargs: dict[str, object],
) -> None:
    """ANYstructure must not copy or reinterpret the neutral model."""

    model = GeometryModel()
    first = model.add_point(0.0, 0.0, 0.0)
    second = model.add_point(1.0, 0.0, 0.0)
    boundary = model.entity_ref("edge", model.add_line(first, second))
    model.add_to_group("boundaries", (boundary,))
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def delegate(*args: object, **kwargs: object) -> GeometryModel:
        calls.append((args, kwargs))
        return model

    monkeypatch.setattr(geometry_generators, delegate_name, delegate)
    adapter = getattr(geometry_generators, adapter_name)
    returned = adapter(*args, **kwargs)

    assert returned is model
    assert len(calls) == 1
    delegated_args, delegated_kwargs = calls[0]
    assert delegated_args == args
    assert all(delegated_kwargs[name] == value for name, value in kwargs.items())
    assert returned.group("boundaries") == (boundary,)
    assert isinstance(boundary, EntityRef)
    assert (boundary.kind, boundary.id) == ("edge", 1)


@pytest.mark.parametrize(
    ("builder", "args", "kwargs", "expected_groups"),
    (
        (
            geometry_generators.generate_plate_geometry,
            (4.0, 3.0),
            {},
            ("shell", "plate", "boundaries"),
        ),
        (
            geometry_generators.generate_stiffened_panel_geometry,
            (4.0, 3.0),
            {"longitudinal_spacing": 1.0, "transverse_spacing": 2.0},
            (
                "shell",
                "plate",
                "boundaries",
                "longitudinal_stiffeners",
                "transverse_stiffeners",
            ),
        ),
        (
            geometry_generators.generate_cylinder_geometry,
            (2.0, 5.0),
            {
                "circumferential_segments": 8,
                "longitudinal_spacing": 2.0,
                "ring_spacing": 2.5,
            },
            ("shell", "bottom", "top", "longitudinal_stiffeners", "ring_stiffeners"),
        ),
        (
            geometry_generators.generate_cone_geometry,
            (2.0, 1.5, 5.0),
            {
                "circumferential_segments": 8,
                "longitudinal_spacing": 2.0,
                "ring_spacing": 2.5,
            },
            ("shell", "bottom", "top", "longitudinal_stiffeners", "ring_stiffeners"),
        ),
    ),
)
def test_neutral_generator_groups_carry_valid_anygeometry_refs(
    builder: Callable[..., GeometryModel],
    args: tuple[float, ...],
    kwargs: dict[str, object],
    expected_groups: tuple[str, ...],
) -> None:
    model = builder(*args, **kwargs)

    assert type(model) is GeometryModel
    for group_name in expected_groups:
        references = model.group(group_name)
        assert references, group_name
        assert all(isinstance(reference, EntityRef) for reference in references)
        assert all(model.resolve_ref(reference) == (reference,) for reference in references)
