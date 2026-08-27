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
        "ANY3dView": "0.5.1",
        "ANYbuckling": "0.1.1",
        "ANYfileio": "0.2.1",
        "ANYgeometry": "0.2.4",
        "ANYmaterial": "0.1.1",
        "ANYmesher": "0.3.2",
        "ANYsolver": "0.4.0",
        "ANYtk3D": "0.5.1",
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


def test_newer_ecosystem_release_graph_is_not_artificially_capped():
    namespace = _launcher_namespace()
    versions = {name: "1.0.0" for name in _compatible_versions()}

    assert namespace["ecosystem_compatibility_problems"](versions.__getitem__) == ()


def test_missing_semantics_distribution_has_actionable_repair_guidance():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    find_spec = _sibling_specs(namespace)

    def read_version(name: str) -> str:
        if name == "ANYfileio":
            raise metadata.PackageNotFoundError(name)
        return versions[name]

    with pytest.raises(RuntimeError) as raised:
        namespace["require_compatible_ecosystem"](read_version, find_spec)

    message = str(raised.value)
    assert "ANYfileio[semantics]>=0.2.1: distribution metadata is missing" in message
    assert "ANYfileIO[semantics]" in message
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
    assert str(namespace["_ROOT"].parent / "ANYsolver" / "src") in problems[0]


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
    assert mesher_project == str(namespace["_ROOT"].parent / "ANYmesh")
    assert any(project.endswith("ANYfileIO[semantics]") for project in projects)
    assert all("ANYio" not in project for project in projects)
    fileio_source = next(
        source
        for distribution, module, source in namespace["ECOSYSTEM_SOURCES"]
        if distribution == "ANYfileio" and module == "anyfileio"
    )
    assert fileio_source == namespace["_ROOT"].parent / "ANYfileIO" / "src"
    assert str(namespace["_ANYTK3D_ROOT"]) in projects
    assert projects[-1].endswith("ANYstructure")
    documented = "python -m " + command.partition(" -m ")[2]
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
    assert '_ROOT.parent / "ANYfileIO" / "src"' in launcher
    assert '_ROOT.parent / "ANYio"' not in launcher
    assert '("ANYfileio", "anyfileio",' in launcher


def test_stale_solver_metadata_is_rejected_before_gui_import():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYsolver"] = "0.2.9"

    problems = namespace["ecosystem_compatibility_problems"](versions.__getitem__)

    assert problems == ("ANYsolver>=0.4.0: installed metadata reports 0.2.9",)


def test_stale_mesher_metadata_is_rejected_before_gui_import():
    namespace = _launcher_namespace()
    versions = _compatible_versions()
    versions["ANYmesher"] = "0.2.2"

    problems = namespace["ecosystem_compatibility_problems"](versions.__getitem__)

    assert problems == (
        "ANYmesher>=0.3.2: installed metadata reports 0.2.2",
    )


def test_old_shared_anymesher_is_rejected_in_favour_of_qualified_fallback(
    tmp_path,
):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.2.1")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.3.2")

    selected = namespace["select_anymesher_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_any3dview_source_must_meet_minimum_051(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_any3dview_checkout(tmp_path / "shared", "0.4.0")
    safe = _write_any3dview_checkout(tmp_path / "safe", "0.5.1")

    selected = namespace["select_any3dview_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_any3dview_environment_override_is_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_any3dview_checkout(tmp_path / "shared", "0.5.1")
    safe = _write_any3dview_checkout(tmp_path / "safe", "0.5.1")
    override = _write_any3dview_checkout(tmp_path / "override", "0.4.0")

    with pytest.raises(RuntimeError, match="at least 0.5.1 is required"):
        namespace["select_any3dview_source_root"](
            {namespace["ANY3DVIEW_SOURCE_ROOT_ENV"]: str(override)},
            shared_root=shared,
            safe_root=safe,
        )


def test_shared_anymesher_is_used_when_it_meets_minimum_032(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.3.2")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.3.2")

    selected = namespace["select_anymesher_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == shared.resolve()


def test_anymesher_environment_override_is_explicit_and_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.3.2")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.3.2")
    override = _write_anymesher_checkout(tmp_path / "override", "0.2.2")
    environment = {namespace["ANYMESHER_SOURCE_ROOT_ENV"]: str(override)}

    with pytest.raises(RuntimeError) as raised:
        namespace["select_anymesher_source_root"](
            environment, shared_root=shared, safe_root=safe
        )

    message = str(raised.value)
    assert namespace["ANYMESHER_SOURCE_ROOT_ENV"] in message
    assert "declares 0.2.2; at least 0.3.2 is required" in message


def test_valid_anymesher_environment_override_wins(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anymesher_checkout(tmp_path / "shared", "0.3.2")
    safe = _write_anymesher_checkout(tmp_path / "safe", "0.3.2")
    override = _write_anymesher_checkout(tmp_path / "override", "0.4.0")
    environment = {namespace["ANYMESHER_SOURCE_ROOT_ENV"]: str(override)}

    selected = namespace["select_anymesher_source_root"](
        environment, shared_root=shared, safe_root=safe
    )

    assert selected == override.resolve()


def test_dirty_shared_anytk3d_is_rejected_in_favour_of_qualified_fallback(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.3.0")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.1")

    selected = namespace["select_anytk3d_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == safe.resolve()


def test_shared_anytk3d_is_used_when_it_meets_minimum_051(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.1")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.1")

    selected = namespace["select_anytk3d_source_root"](
        {}, shared_root=shared, safe_root=safe
    )

    assert selected == shared.resolve()


def test_anytk3d_environment_override_is_explicit_and_fail_closed(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.1")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.1")
    override = _write_anytk3d_checkout(tmp_path / "override", "0.3.0")
    environment = {namespace["ANYTK3D_SOURCE_ROOT_ENV"]: str(override)}

    with pytest.raises(RuntimeError) as raised:
        namespace["select_anytk3d_source_root"](
            environment, shared_root=shared, safe_root=safe
        )

    message = str(raised.value)
    assert namespace["ANYTK3D_SOURCE_ROOT_ENV"] in message
    assert "declares 0.3.0; at least 0.5.1 is required" in message


def test_valid_anytk3d_environment_override_wins(tmp_path):
    namespace = _launcher_namespace()
    shared = _write_anytk3d_checkout(tmp_path / "shared", "0.5.1")
    safe = _write_anytk3d_checkout(tmp_path / "safe", "0.5.1")
    override = _write_anytk3d_checkout(tmp_path / "override", "0.6.0")
    environment = {namespace["ANYTK3D_SOURCE_ROOT_ENV"]: str(override)}

    selected = namespace["select_anytk3d_source_root"](
        environment, shared_root=shared, safe_root=safe
    )

    assert selected == override.resolve()


def test_production_publish_uses_verified_prebuilt_release_assets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(
        encoding="utf-8"
    )
    production = workflow.split("  publish-production:\n", 1)[1]

    assert "release:\n    types: [published]" in workflow
    assert "workflow_dispatch:" in workflow
    assert "if: github.event_name == 'workflow_dispatch'" in workflow
    assert 'test "$RELEASE_TAG" = "v6.3.1"' in production
    assert 'gh release download "$RELEASE_TAG"' in production
    assert "ANYstructure-6.3.1-SHA256SUMS.txt" in production
    assert "checksum manifest does not exactly cover distributions" in production
    assert "unexpected ANYstructure distribution asset" in production
    assert "release checksum mismatch" in production
    assert "pypa/gh-action-pypi-publish@release/v1" in production
    assert "packages-dir: dist/" in production
    assert "python -m build" not in production
    assert "timeout-minutes:" not in workflow
