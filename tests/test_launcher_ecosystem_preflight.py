"""Headless release-graph checks for the checkout launcher."""

from __future__ import annotations

from importlib import metadata
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _launcher_namespace():
    return runpy.run_path(str(ROOT / "run_gui.py"), run_name="preflight_test")


def _compatible_versions() -> dict[str, str]:
    return {
        "ANY3dView": "0.5.5",
        "ANYbuckling": "0.1.1",
        "ANYfileio": "0.3.1",
        "ANYgeometry": "0.4.2",
        "ANYmaterial": "0.2.0",
        "ANYmesher": "0.4.0",
        "ANYsolver": "0.4.1",
        "ANYtk3D": "0.5.5",
    }


def _sibling_specs(namespace):
    roots = {
        module_name: root
        for _distribution, module_name, root in namespace["ECOSYSTEM_SOURCES"]
    }

    def find_spec(module_name: str):
        root = roots[module_name]
        return SimpleNamespace(
            origin=str(root / module_name / "__init__.py"),
            submodule_search_locations=(),
        )

    return find_spec


def _write_checkout(
    root: Path, *, project: str, package_name: str, version: str
) -> Path:
    package = root / "src" / package_name
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{project}"\nversion = '
        f'"{version}"\n',
        encoding="utf-8",
    )
    return root


def _write_anytk3d_checkout(root: Path, version: str) -> Path:
    return _write_checkout(
        root, project="ANYtk3D", package_name="anytk3d", version=version
    )


def _write_any3dview_checkout(root: Path, version: str) -> Path:
    return _write_checkout(
        root, project="ANY3dView", package_name="any3dview", version=version
    )


def _write_anymesher_checkout(root: Path, version: str) -> Path:
    return _write_checkout(
        root, project="ANYmesher", package_name="anymesher", version=version
    )


@pytest.mark.parametrize(
    ("environment_constant", "project", "package_name", "minimum", "maximum"),
    (
        ("ANYMATERIAL_SOURCE_ROOT_ENV", "ANYmaterial", "anymaterial", "0.2.0", "0.3.0"),
        ("ANYGEOMETRY_SOURCE_ROOT_ENV", "ANYgeometry", "anygeometry", "0.4.2", "0.5.0"),
        ("ANYSOLVER_SOURCE_ROOT_ENV", "ANYsolver", "anysolver", "0.4.1", "0.5.0"),
        ("ANYFILEIO_SOURCE_ROOT_ENV", "ANYfileio", "anyfileio", "0.3.1", "0.4.0"),
        ("ANYBUCKLING_SOURCE_ROOT_ENV", "ANYbuckling", "anybuckling", "0.1.1", "0.2.0"),
    ),
)
def test_bound_source_environment_overrides_are_validated(
    tmp_path,
    environment_constant,
    project,
    package_name,
    minimum,
    maximum,
):
    namespace = _launcher_namespace()
    shared = _write_checkout(
        tmp_path / "shared", project=project, package_name=package_name, version=minimum
    )
    override = _write_checkout(
        tmp_path / "override", project=project, package_name=package_name, version=minimum
    )
    environment_name = namespace[environment_constant]

    assert namespace["select_bound_source_root"](
        environment_name,
        project=project,
        package_name=package_name,
        minimum=minimum,
        maximum=maximum,
        environ={environment_name: str(override)},
        shared_root=shared,
    ) == override.resolve()

    incompatible = _write_checkout(
        tmp_path / "incompatible",
        project=project,
        package_name=package_name,
        version=maximum,
    )
    with pytest.raises(RuntimeError, match=f"Invalid {environment_name} override"):
        namespace["select_bound_source_root"](
            environment_name,
            project=project,
            package_name=package_name,
            minimum=minimum,
            maximum=maximum,
            environ={environment_name: str(incompatible)},
            shared_root=shared,
        )


def test_compatible_latest_release_graph_passes_without_importing_tk():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    find_spec = _sibling_specs(namespace)

    assert namespace["ecosystem_compatibility_problems"](versions.__getitem__) == ()
    assert namespace["ecosystem_source_problems"](find_spec) == ()
    assert (
        namespace["require_compatible_ecosystem"](versions.__getitem__, find_spec)
        is None
    )


def test_incompatible_major_release_graph_is_rejected_by_declared_caps():
    namespace = _launcher_namespace()
    versions = {name: "1.0.0" for name in _compatible_versions()}

    assert namespace["ecosystem_compatibility_problems"](versions.__getitem__) == (
        "ANY3dView[gpu]>=0.5.5,<0.6: installed metadata reports 1.0.0",
        "ANYbuckling>=0.1.1,<0.2: installed metadata reports 1.0.0",
        "ANYfileio[semantics]>=0.3.1,<0.4: installed metadata reports 1.0.0",
        "ANYgeometry>=0.4.2,<0.5: installed metadata reports 1.0.0",
        "ANYmaterial>=0.2.0,<0.3: installed metadata reports 1.0.0",
        "ANYmesher>=0.4.0,<0.5: installed metadata reports 1.0.0",
        "ANYsolver>=0.4.1,<0.5: installed metadata reports 1.0.0",
        "ANYtk3D>=0.5.5,<0.6: installed metadata reports 1.0.0",
    )


def test_missing_semantics_metadata_warns_without_blocking_valid_sources(capsys):
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    find_spec = _sibling_specs(namespace)

    def read_version(name: str) -> str:
        if name == "ANYfileio":
            raise metadata.PackageNotFoundError(name)
        return versions[name]

    namespace["require_compatible_ecosystem"](read_version, find_spec)

    message = capsys.readouterr().err
    assert "ANYfileio[semantics]>=0.3.1,<0.4: distribution metadata is missing" in message
    assert "validated sibling source checkouts" in message
    assert "pip install --upgrade" in message
    assert "ANYstructure" in message


def test_wrong_source_origin_is_rejected_without_importing_the_module(tmp_path):
    namespace = _launcher_namespace()
    expected = _sibling_specs(namespace)

    def find_spec(module_name: str):
        if module_name == "anysolver":
            return SimpleNamespace(
                origin=str(tmp_path / "site-packages" / "anysolver" / "__init__.py"),
                submodule_search_locations=(),
            )
        return expected(module_name)

    problems = namespace["ecosystem_source_problems"](find_spec)

    assert len(problems) == 1
    assert problems[0].startswith("ANYsolver: anysolver resolves from ")
    assert str(namespace["_ANYSOLVER_ROOT"] / "src") in problems[0]


def test_mixed_trusted_namespace_and_untrusted_executable_origin_is_rejected(
    tmp_path,
):
    namespace = _launcher_namespace()
    expected = _sibling_specs(namespace)

    def find_spec(module_name: str):
        if module_name == "anysolver":
            return SimpleNamespace(
                origin=str(tmp_path / "untrusted" / "anysolver" / "__init__.py"),
                submodule_search_locations=(
                    str(namespace["_ANYSOLVER_ROOT"] / "src" / "anysolver"),
                ),
            )
        return expected(module_name)

    problems = namespace["ecosystem_source_problems"](find_spec)

    assert len(problems) == 1
    assert problems[0].startswith("ANYsolver: anysolver resolves from ")
    assert str(tmp_path / "untrusted") in problems[0]


def test_repair_command_has_one_dependency_ordered_editable_graph():
    namespace = _launcher_namespace()
    command = namespace["editable_repair_command"]()
    projects = namespace["EDITABLE_BOOTSTRAP_PROJECTS"]

    assert command.startswith(
        f'"{namespace["sys"].executable}" -m pip install --upgrade --no-deps '
    )
    positions = [command.index(f'-e "{project}"') for project in projects]
    assert positions == sorted(positions)
    assert str(namespace["_ANY3DVIEW_ROOT"]) + "[gpu]" in projects
    mesher_project = str(namespace["_ANYMESHER_ROOT"])
    assert mesher_project in projects
    assert mesher_project == str(namespace["_ANYMESHER_ROOT"])
    assert str(namespace["_ANYFILEIO_ROOT"]) + "[semantics]" in projects
    assert all("ANYio" not in project for project in projects)
    fileio_source = next(
        source
        for distribution, module, source in namespace["ECOSYSTEM_SOURCES"]
        if distribution == "ANYfileio" and module == "anyfileio"
    )
    assert fileio_source == namespace["_ANYFILEIO_ROOT"] / "src"
    assert str(namespace["_ANYTK3D_ROOT"]) in projects
    assert projects[-1] == str(namespace["_ROOT"])
    documented = "python -m " + command.partition(" -m ")[2]
    documented = documented.replace(
        str(namespace["_ROOT"]),
        r"C:\Github\ANYstructure",
    )
    for selected_name, repository in (
        ("_ANY3DVIEW_ROOT", "ANY3dView"),
        ("_ANYMATERIAL_ROOT", "ANYmaterial"),
        ("_ANYGEOMETRY_ROOT", "ANYgeometry"),
        ("_ANYMESHER_ROOT", "ANYmesh"),
        ("_ANYFILEIO_ROOT", "ANYfileIO"),
        ("_ANYSOLVER_ROOT", "ANYsolver"),
        ("_ANYBUCKLING_ROOT", "ANYbuckling"),
        ("_ANYTK3D_ROOT", "ANYtk3D"),
    ):
        documented = documented.replace(
            str(namespace[selected_name]),
            rf"C:\Github\{repository}",
        )
    assert documented in (ROOT / "README.md").read_text(encoding="utf-8")


def test_anyfileio_uses_only_the_canonical_repository_and_source_path():
    launcher = (ROOT / "run_gui.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )

    assert 'repository: audunarn/ANYfileIO' in workflow
    assert 'path: .ecosystem/ANYfileIO' in workflow
    assert '.ecosystem/ANYfileIO[semantics]' in workflow
    assert 'repository: audunarn/ANYio' not in workflow
    assert '.ecosystem/ANYio' not in workflow
    assert '_ANYFILEIO_ROOT / "src"' in launcher
    assert '_ROOT.parent / "ANYio"' not in launcher
    assert '("ANYfileio", "anyfileio",' in launcher


def test_ci_binds_exact_release_graph_revisions_and_fails_closed_for_solver():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    expected_refs = {
        "d8a233ef4c5e38d25dbba0eb20e6cfa8d44ec5a2",
        "7d36c97dd0dbec8884f8894a4258ece83ad61271",
        "dd954f088a4cb95e267280cc4777b09e16232bd9",
        "27e428188a891705288fef82bab0b166e330aff2",
        "b48ba51c7b79e6d64b3f99c1fb131b9b602e7e1d",
        "5017827b0e88b4b52d7fee0fad6a1f405e2d33cf",
        "a871d5a3c466666b79f3ce3a015a2cfd7534376b",
        "2caa92325885938c594f27145ed16069d807e364",
    }
    for revision in expected_refs:
        assert workflow.count(f"ref: {revision}") == 2
    assert workflow.count("repository: audunarn/") == 16
    assert workflow.count("          ref: ") == 16


def test_checkout_locator_prefers_actions_ecosystem_graph(tmp_path):
    namespace = _launcher_namespace()
    repository_root = tmp_path / "ANYstructure"
    embedded = _write_checkout(
        repository_root / ".ecosystem" / "ANYmesh",
        project="ANYmesher",
        package_name="anymesher",
        version="0.4.0",
    )
    _write_checkout(
        tmp_path / "ANYmesh",
        project="ANYmesher",
        package_name="anymesher",
        version="0.3.2",
    )

    selected = namespace["_checkout_root"](
        "ANYmesh", repository_root=repository_root
    )

    assert selected == embedded.resolve()


def test_stale_solver_metadata_is_rejected_before_gui_import():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYsolver"] = "0.2.9"

    problems = namespace["ecosystem_compatibility_problems"](versions.__getitem__)

    assert problems == (
        "ANYsolver>=0.4.1,<0.5: installed metadata reports 0.2.9",
    )


def test_stale_solver_metadata_does_not_block_qualified_source(capsys):
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYsolver"] = "0.2.9"

    assert namespace["require_compatible_ecosystem"](
        versions.__getitem__, _sibling_specs(namespace)
    ) is None
    warning = capsys.readouterr().err
    assert "ANYsolver>=0.4.1,<0.5: installed metadata reports 0.2.9" in warning
    assert "The application can continue" in warning


def test_solver_prerelease_does_not_satisfy_final_release_floor():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYsolver"] = "0.4.1rc1"

    assert namespace["ecosystem_compatibility_problems"](versions.__getitem__) == (
        "ANYsolver>=0.4.1,<0.5: installed metadata reports 0.4.1rc1",
    )


def test_stale_mesher_metadata_is_rejected_before_gui_import():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYmesher"] = "0.2.2"

    problems = namespace["ecosystem_compatibility_problems"](versions.__getitem__)

    assert problems == (
        "ANYmesher>=0.4.0,<0.5: installed metadata reports 0.2.2",
    )


def test_old_shared_anymesher_is_rejected_in_favour_of_qualified_fallback(
    tmp_path,
):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.2.1")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.4.0")

    selected = namespace["select_anymesher_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_any3dview_source_must_meet_minimum_055(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_any3dview_checkout(tmp_path / "shared", "0.4.0")
    safe = _write_any3dview_checkout(tmp_path / "safe", "0.5.5")

    selected = namespace["select_any3dview_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_any3dview_environment_override_is_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_any3dview_checkout(tmp_path / "shared", "0.5.5")
    safe = _write_any3dview_checkout(tmp_path / "safe", "0.5.5")
    override = _write_any3dview_checkout(tmp_path / "override", "0.4.0")

    with pytest.raises(RuntimeError, match="at least 0.5.5 is required"):
        namespace["select_any3dview_source_root"](
            {namespace["ANY3DVIEW_SOURCE_ROOT_ENV"]: str(override)},
            shared_root=shared,
            safe_root=safe,
        )


def test_shared_anymesher_is_used_when_it_meets_minimum_040(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.4.0")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.4.0")

    selected = namespace["select_anymesher_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == shared.resolve()


def test_anymesher_environment_override_is_explicit_and_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.4.0")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.4.0")
    override = _write_anymesher_checkout(tmp_path / "override", "0.2.2")
    environment = {namespace["ANYMESHER_SOURCE_ROOT_ENV"]: str(override)}

    with pytest.raises(RuntimeError) as raised:
        namespace["select_anymesher_source_root"](
            environment, shared_root=shared, safe_root=safe
        )

    message = str(raised.value)
    assert namespace["ANYMESHER_SOURCE_ROOT_ENV"] in message
    assert "declares 0.2.2; at least 0.4.0 is required" in message


def test_valid_anymesher_environment_override_wins(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.4.0")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.4.0")
    override = _write_anymesher_checkout(tmp_path / "override", "0.4.0")
    environment = {namespace["ANYMESHER_SOURCE_ROOT_ENV"]: str(override)}

    selected = namespace["select_anymesher_source_root"](
        environment, shared_root=shared, safe_root=safe
    )

    assert selected == override.resolve()


def test_dirty_shared_anytk3d_is_rejected_in_favour_of_qualified_fallback(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.3.0")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.5")

    selected = namespace["select_anytk3d_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_shared_anytk3d_is_used_when_it_meets_minimum_055(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.5")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.5")

    selected = namespace["select_anytk3d_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == shared.resolve()


def test_anytk3d_environment_override_is_explicit_and_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.5")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.5")
    override = _write_anytk3d_checkout(tmp_path / "override", "0.3.0")
    environment = {namespace["ANYTK3D_SOURCE_ROOT_ENV"]: str(override)}

    with pytest.raises(RuntimeError) as raised:
        namespace["select_anytk3d_source_root"](
            environment, shared_root=shared, safe_root=safe
        )

    message = str(raised.value)
    assert namespace["ANYTK3D_SOURCE_ROOT_ENV"] in message
    assert "declares 0.3.0; at least 0.5.5 is required" in message


def test_valid_anytk3d_environment_override_wins(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.5")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.5")
    override = _write_anytk3d_checkout(tmp_path / "override", "0.5.9")
    environment = {namespace["ANYTK3D_SOURCE_ROOT_ENV"]: str(override)}

    selected = namespace["select_anytk3d_source_root"](
        environment, shared_root=shared, safe_root=safe
    )

    assert selected == override.resolve()


def test_next_minor_viewer_overrides_are_rejected(tmp_path):
    namespace = _launcher_namespace()
    view_shared = _write_any3dview_checkout(tmp_path / "view-shared", "0.5.5")
    view_safe = _write_any3dview_checkout(tmp_path / "view-safe", "0.5.5")
    view_override = _write_any3dview_checkout(tmp_path / "view-override", "0.6.0")
    tk_shared = _write_anytk3d_checkout(tmp_path / "tk-shared", "0.5.5")
    tk_safe = _write_anytk3d_checkout(tmp_path / "tk-safe", "0.5.5")
    tk_override = _write_anytk3d_checkout(tmp_path / "tk-override", "0.6.0")

    with pytest.raises(RuntimeError, match="must remain below 0.6.0"):
        namespace["select_any3dview_source_root"](
            {namespace["ANY3DVIEW_SOURCE_ROOT_ENV"]: str(view_override)},
            shared_root=view_shared,
            safe_root=view_safe,
        )
    with pytest.raises(RuntimeError, match="must remain below 0.6.0"):
        namespace["select_anytk3d_source_root"](
            {namespace["ANYTK3D_SOURCE_ROOT_ENV"]: str(tk_override)},
            shared_root=tk_shared,
            safe_root=tk_safe,
        )


def test_next_unqualified_anymesher_override_is_rejected(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.3.2")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.3.2")
    override = _write_anymesher_checkout(tmp_path / "override", "0.5.0")

    with pytest.raises(RuntimeError, match="must remain below 0.5.0"):
        namespace["select_anymesher_source_root"](
            {namespace["ANYMESHER_SOURCE_ROOT_ENV"]: str(override)},
            shared_root=shared,
            safe_root=safe,
        )


def test_production_publish_uses_verified_prebuilt_release_assets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )
    manual = workflow.split("  publish-production:\n", 1)[0]
    production = workflow.split("  publish-production:\n", 1)[1]

    assert "release:\n    types: [published]" in workflow
    assert "workflow_dispatch:" in workflow
    assert "if: github.event_name == 'workflow_dispatch'" in workflow
    assert (
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
        in manual
    )
    assert (
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
        in manual
    )
    assert (
        "actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4"
        in manual
    )
    assert "@v6" not in workflow
    assert "@v5" not in workflow
    assert "@v4" not in workflow
    assert "github.event.release.prerelease == false" in production
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in production
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in production
    assert "ref: ${{ github.event.release.tag_name }}" in production
    assert "fetch-depth: 0" in production
    assert 'gh release download "$RELEASE_TAG"' in production
    assert "--pattern" not in production
    assert "tools/verify_release_authority.py" in production
    assert "docs/release/anystructure-6.4.0-ledger.json" in production
    assert "--protected-ref refs/remotes/origin/master" in production
    assert "--expected-terminal ACCEPTED_ANYSTRUCTURE_6_4_0_RELEASE" in production
    assert "ANYstructure-6.4.0-SHA256SUMS.txt" in production
    assert "--artifact anystructure-6.4.0-py3-none-any.whl" in production
    assert "--artifact anystructure-6.4.0.tar.gz" in production
    assert (
        "pypa/gh-action-pypi-publish@"
        "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
    ) in production
    assert "@release/v1" not in production
    assert "packages-dir: dist/" in production
    assert "python -m build" not in production
    assert "timeout-minutes:" not in workflow
