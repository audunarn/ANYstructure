from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import zipfile

import pytest


pytestmark = pytest.mark.release_authority


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERIFIER = ROOT / "tools" / "verify_release_authority.py"
RELEASE_DISTRIBUTION = "ANYstructure"
RELEASE_NORMALIZED = "anystructure"
RELEASE_VERSION = "6.4.0"
RELEASE_TAG = f"v{RELEASE_VERSION}"
RELEASE_TERMINAL = "ACCEPTED_ANYSTRUCTURE_6_4_0_RELEASE"
RELEASE_WHEEL = f"{RELEASE_NORMALIZED}-{RELEASE_VERSION}-py3-none-any.whl"
RELEASE_SDIST = f"{RELEASE_NORMALIZED}-{RELEASE_VERSION}.tar.gz"
RELEASE_LEDGER = (
    Path("docs/release")
    / f"{RELEASE_NORMALIZED}-{RELEASE_VERSION}-ledger.json"
)
CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_ACTION = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
PUBLISH_ACTION = (
    "pypa/gh-action-pypi-publish@"
    "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Release Authority Test",
            "-c",
            "user.email=release-authority@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *arguments,
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _release_metadata(
    distribution: str = RELEASE_DISTRIBUTION,
) -> bytes:
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {distribution}\n"
        f"Version: {RELEASE_VERSION}\n\n"
    ).encode("utf-8")


def _write_release_wheel(
    path: Path,
    payload: bytes,
    *,
    distribution: str = RELEASE_DISTRIBUTION,
) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{RELEASE_NORMALIZED}/__init__.py", payload)
        archive.writestr(
            f"{RELEASE_NORMALIZED}-{RELEASE_VERSION}.dist-info/METADATA",
            _release_metadata(distribution),
        )


def _write_release_sdist(path: Path) -> None:
    metadata = _release_metadata()
    info = tarfile.TarInfo(
        f"{RELEASE_NORMALIZED}-{RELEASE_VERSION}/PKG-INFO"
    )
    info.size = len(metadata)
    with tarfile.open(path, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(metadata))


def _write_release_checksums(assets: Path) -> None:
    text = "".join(
        f"{hashlib.sha256((assets / name).read_bytes()).hexdigest()}  {name}\n"
        for name in sorted((RELEASE_WHEEL, RELEASE_SDIST))
    )
    (assets / "ANYstructure-6.4.0-SHA256SUMS.txt").write_text(
        text,
        encoding="ascii",
        newline="\n",
    )


def _run_release_verifier(
    tmp_path: Path,
    mutation: str = "",
) -> subprocess.CompletedProcess[str]:
    repository = tmp_path / "repository"
    remote = tmp_path / "origin.git"
    assets = tmp_path / "release-assets"
    repository.mkdir(parents=True)
    remote.mkdir()
    assets.mkdir()
    _git(repository, "init", "--quiet")
    _git(remote, "init", "--bare", "--quiet")
    (repository / "source.txt").write_text(
        "frozen artifact source\n",
        encoding="utf-8",
    )
    source_paths = ["source.txt"]
    if mutation == "textconv-diff-driver":
        (repository / ".gitattributes").write_text(
            "* diff=release-bypass\n",
            encoding="utf-8",
        )
        source_paths.append(".gitattributes")
    _git(repository, "add", *source_paths)
    _git(repository, "commit", "--quiet", "-m", "freeze artifact source")
    source_commit = _git(repository, "rev-parse", "HEAD")
    source_tree = _git(repository, "rev-parse", "HEAD^{tree}")
    _git(repository, "branch", "-M", "master")
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "--quiet", "-u", "origin", "master")

    attribute_source_commit = ""
    if mutation == "git-attr-source":
        _git(repository, "checkout", "--quiet", "-b", "attack-attributes")
        (repository / ".gitattributes").write_text(
            "* diff=release-bypass\n",
            encoding="utf-8",
        )
        _git(repository, "add", ".gitattributes")
        _git(repository, "commit", "--quiet", "-m", "attacker attributes")
        attribute_source_commit = _git(repository, "rev-parse", "HEAD")
        _git(repository, "checkout", "--quiet", "master")

    _write_release_wheel(assets / RELEASE_WHEEL, b"accepted build\n")
    if mutation == "wrong-metadata":
        _write_release_wheel(
            assets / RELEASE_WHEEL,
            b"accepted build\n",
            distribution="DifferentDistribution",
        )
    _write_release_sdist(assets / RELEASE_SDIST)
    artifact_rows = []
    for name in sorted((RELEASE_WHEEL, RELEASE_SDIST)):
        raw = (assets / name).read_bytes()
        artifact_rows.append(
            {
                "bytes": len(raw),
                "filename": name,
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
            }
        )
    ledger = {
        "artifact_source": {
            "commit": source_commit,
            "tree": source_tree,
        },
        "artifacts": artifact_rows,
        "distribution": RELEASE_DISTRIBUTION,
        "publication_authorized": True,
        "qualification": {
            "accepted_terminal": RELEASE_TERMINAL,
            "evidence_sha256": "A" * 64,
            "independent_review_sha256": "B" * 64,
        },
        "schema": "anyecosystem.release-ledger-v1",
        "tag": RELEASE_TAG,
        "version": RELEASE_VERSION,
    }
    if mutation == "wrong-byte-count":
        ledger["artifacts"][0]["bytes"] += 1
    elif mutation == "wrong-terminal":
        ledger["qualification"]["accepted_terminal"] = "REJECTED_RELEASE"
    elif mutation == "evidence-hash":
        ledger["qualification"]["evidence_sha256"] = "0" * 64
    elif mutation == "review-hash":
        ledger["qualification"]["independent_review_sha256"] = "A" * 64
    elif mutation == "noncanonical-tag-ref":
        ledger["tag"] = f"{RELEASE_TAG}^{{commit}}"
    if mutation == "wrong-source":
        ledger["artifact_source"]["tree"] = "0" * 40

    target = repository / RELEASE_LEDGER
    target.parent.mkdir(parents=True)
    if mutation == "noncanonical":
        target.write_text(json.dumps(ledger), encoding="utf-8")
    else:
        target.write_text(
            json.dumps(ledger, allow_nan=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if mutation == "duplicate-key":
        text = target.read_text(encoding="utf-8")
        target.write_text(
            text.replace(
                "{\n",
                '{\n  "schema": "duplicate-forbidden",\n',
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
    elif mutation == "nonfinite":
        text = target.read_text(encoding="utf-8")
        target.write_text(
            text.replace(
                f'"version": "{RELEASE_VERSION}"',
                '"version": NaN',
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
    _git(repository, "add", RELEASE_LEDGER.as_posix())
    if mutation == "extra-child-path":
        (repository / "unexpected.txt").write_text(
            "not ledger-only\n",
            encoding="utf-8",
        )
        _git(repository, "add", "unexpected.txt")
    _git(
        repository,
        "commit",
        "--quiet",
        "-m",
        "docs: authorize release artifacts",
    )
    _git(repository, "tag", RELEASE_TAG)
    if mutation != "unmerged-tag-child":
        _git(repository, "push", "--quiet", "origin", "HEAD:master")

    git_directory = Path(_git(repository, "rev-parse", "--git-dir"))
    if not git_directory.is_absolute():
        git_directory = repository / git_directory
    git_info = git_directory / "info"
    git_info.mkdir(exist_ok=True)
    if mutation == "moved-tag-ref":
        _git(repository, "tag", "--force", RELEASE_TAG, source_commit)
    elif mutation == "missing-tag-ref":
        _git(repository, "tag", "--delete", RELEASE_TAG)
    elif mutation == "replacement-ref":
        _git(
            repository,
            "replace",
            source_commit,
            _git(repository, "rev-parse", "HEAD"),
        )
    elif mutation == "graft-file":
        (git_info / "grafts").write_text(
            _git(repository, "rev-parse", "HEAD") + "\n",
            encoding="ascii",
        )
    elif mutation == "info-attributes":
        (git_info / "attributes").write_text(
            "* diff=release-bypass\n",
            encoding="utf-8",
        )

    _write_release_checksums(assets)
    invoked_tag = (
        f"{RELEASE_TAG}^{{commit}}"
        if mutation == "noncanonical-tag-ref"
        else RELEASE_TAG
    )
    verifier_environment = os.environ.copy()
    attacker_marker = tmp_path / "attacker.marker"
    attacker = tmp_path / "attacker.py"
    attacker.write_text(
        "from pathlib import Path\n"
        f"Path({str(attacker_marker)!r}).write_text("
        "'invoked\\n', encoding='utf-8')\n"
        "raise SystemExit(97)\n",
        encoding="utf-8",
    )
    attacker_command = shlex.join((sys.executable, str(attacker)))
    external_attributes = tmp_path / "external.attributes"
    external_attributes.write_text(
        "* diff=release-bypass\n",
        encoding="utf-8",
    )
    external_config = tmp_path / "external.gitconfig"
    external_config.write_text("", encoding="utf-8")
    _git(
        repository,
        "config",
        "--file",
        str(external_config),
        "core.attributesFile",
        str(external_attributes),
    )
    _git(
        repository,
        "config",
        "--file",
        str(external_config),
        "diff.external",
        attacker_command,
    )
    _git(
        repository,
        "config",
        "--file",
        str(external_config),
        "diff.release-bypass.textconv",
        attacker_command,
    )
    assert (
        _git(
            repository,
            "config",
            "--file",
            str(external_config),
            "--get",
            "diff.external",
        )
        == attacker_command
    )
    if mutation == "global-attributes-config":
        verifier_environment["GIT_CONFIG_GLOBAL"] = str(external_config)
    elif mutation == "system-attributes-config":
        verifier_environment["GIT_CONFIG_SYSTEM"] = str(external_config)
    elif mutation == "core-attributes-config":
        _git(
            repository,
            "config",
            "core.attributesFile",
            str(external_attributes),
        )
        _git(
            repository,
            "config",
            "diff.release-bypass.textconv",
            attacker_command,
        )
    elif mutation == "environment-external-diff":
        verifier_environment["GIT_EXTERNAL_DIFF"] = attacker_command
    elif mutation == "local-external-diff":
        _git(repository, "config", "diff.external", attacker_command)
    elif mutation == "textconv-diff-driver":
        _git(
            repository,
            "config",
            "diff.release-bypass.textconv",
            attacker_command,
        )
    elif mutation == "git-attr-source":
        verifier_environment["GIT_ATTR_SOURCE"] = attribute_source_commit
        _git(
            repository,
            "config",
            "diff.release-bypass.textconv",
            attacker_command,
        )
    if mutation == "paired-replacement":
        _write_release_wheel(
            assets / RELEASE_WHEEL,
            b"replacement build\n",
        )
        _write_release_checksums(assets)
    elif mutation == "checksum":
        (assets / "ANYstructure-6.4.0-SHA256SUMS.txt").write_text(
            "0" * 64
            + f"  {RELEASE_WHEEL}\n"
            + hashlib.sha256((assets / RELEASE_SDIST).read_bytes()).hexdigest()
            + f"  {RELEASE_SDIST}\n",
            encoding="ascii",
            newline="\n",
        )
    elif mutation == "extra-asset":
        (assets / "unregistered.txt").write_text(
            "extra\n",
            encoding="utf-8",
        )
    elif mutation == "tag":
        invoked_tag = "v6.3.0"

    return subprocess.run(
        [
            sys.executable,
            str(RELEASE_VERIFIER),
            "--repository-root",
            str(repository),
            "--ledger",
            RELEASE_LEDGER.as_posix(),
            "--assets",
            str(assets),
            "--output",
            str(tmp_path / "dist"),
            "--tag",
            invoked_tag,
            "--protected-ref",
            "refs/remotes/origin/master",
            "--expected-terminal",
            RELEASE_TERMINAL,
            "--distribution",
            RELEASE_DISTRIBUTION,
            "--version",
            RELEASE_VERSION,
            "--checksum-name",
            "ANYstructure-6.4.0-SHA256SUMS.txt",
            "--artifact",
            RELEASE_WHEEL,
            "--artifact",
            RELEASE_SDIST,
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env=verifier_environment,
    )


def test_production_workflow_uses_immutable_ledger_authority() -> None:
    workflow = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    production = workflow.split("\n  publish-production:\n", 1)[1]
    assert "types: [published]" in workflow
    assert "github.event.release.prerelease == false" in production
    assert "ref: ${{ github.event.release.tag_name }}" in production
    assert "fetch-depth: 0" in production
    assert "--protected-ref refs/remotes/origin/master" in production
    assert "--expected-terminal " + RELEASE_TERMINAL in production
    assert CHECKOUT_ACTION in production
    assert SETUP_ACTION in production
    assert PUBLISH_ACTION in production
    assert "@release/v1" not in production
    assert 'gh release download "$RELEASE_TAG"' in production
    assert "--pattern" not in production
    assert "tools/verify_release_authority.py" in production
    assert RELEASE_LEDGER.as_posix() in production
    assert "--checksum-name ANYstructure-6.4.0-SHA256SUMS.txt" in production
    assert "--artifact " + RELEASE_WHEEL in production
    assert "--artifact " + RELEASE_SDIST in production
    assert "python -m build" not in production
    assert "id-token: write" in production


def test_manual_candidate_build_path_remains_separate() -> None:
    workflow = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    manual = workflow.split("\n  publish-production:\n", 1)[0]
    assert "if: github.event_name == 'workflow_dispatch'" in manual
    assert "python -m build --outdir dist" in manual
    assert (
        "sha256sum *.whl *.tar.gz > "
        "ANYstructure-6.4.0-SHA256SUMS.txt"
    ) in manual


def test_release_authority_accepts_exact_ledger_bound_artifacts(
    tmp_path: Path,
) -> None:
    completed = _run_release_verifier(tmp_path)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "paired-replacement",
        "checksum",
        "extra-asset",
        "tag",
        "wrong-source",
        "unmerged-tag-child",
        "wrong-terminal",
        "evidence-hash",
        "review-hash",
        "wrong-byte-count",
        "wrong-metadata",
        "extra-child-path",
        "noncanonical",
        "duplicate-key",
        "nonfinite",
        "moved-tag-ref",
        "missing-tag-ref",
        "noncanonical-tag-ref",
        "replacement-ref",
        "graft-file",
        "info-attributes",
    ],
)
def test_release_authority_rejects_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    completed = _run_release_verifier(tmp_path / mutation, mutation)
    assert completed.returncode != 0, mutation
    expected_errors = {
        "graft-file": "Git grafts are forbidden",
        "info-attributes": "Git info attributes are forbidden",
        "missing-tag-ref": "release tag ref does not resolve to a commit",
        "moved-tag-ref": "release tag ref does not identify the ledger HEAD",
        "noncanonical-tag-ref": "release tag is not canonical",
        "replacement-ref": "Git replacement objects are forbidden",
    }
    if mutation in expected_errors:
        assert expected_errors[mutation] in completed.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "core-attributes-config",
        "environment-external-diff",
        "git-attr-source",
        "global-attributes-config",
        "local-external-diff",
        "system-attributes-config",
        "textconv-diff-driver",
    ],
)
def test_release_authority_neutralizes_external_git_configuration(
    tmp_path: Path,
    mutation: str,
) -> None:
    # Keep nested bare-repository refs below Windows' path ceiling.
    case = tmp_path / "g"
    completed = _run_release_verifier(case, mutation)

    assert completed.returncode == 0, completed.stderr
    assert not (case / "attacker.marker").exists()


def test_paired_asset_and_checksum_replacement_is_not_authority(
    tmp_path: Path,
) -> None:
    completed = _run_release_verifier(tmp_path, "paired-replacement")
    assert completed.returncode != 0
    assert "committed authority" in completed.stderr


def test_git_environment_scrubs_inherited_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "_anystructure_release_authority",
        RELEASE_VERIFIER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inherited = {
        "GIT_ATTR_SOURCE",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
    }
    for key in inherited:
        monkeypatch.setenv(key, "attacker-controlled")
    environment = module._git_environment()
    assert not inherited & set(environment)
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
