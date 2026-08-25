# ANY Ecosystem Guide

> **Purpose:** Keep every ANY contribution correct, interoperable, traceable and
> releasable—regardless of whether it is written by a person or an AI assistant.

- **Applies to:** every contributor and every ANY repository.
- **Canonical source:** `ANYopenSoft/ECOSYSTEM_GUIDE.md`.
- **Local rule:** repository documentation may add constraints, but may not
  weaken this guide. Integrated root copies must remain byte-identical.

## Non-negotiables

| Priority | Rule |
|---|---|
| **Ownership** | Domain truth lives in its canonical repository and is consumed through public contracts. |
| **Correctness** | Sound theory and independently verifiable results outrank performance. |
| **Safety** | Ambiguity, unsupported input and incomplete evidence fail closed. |
| **Traceability** | Claims bind exact source, inputs, environment, commands and artifacts. |
| **Compatibility** | Breaking changes require an explicit decision and migration path. |
| **Delivery** | Required tests and CI are green before merge or release. |

## 1. Structure and ownership

| Area | Canonical owner |
|---|---|
| Geometry, topology, identity, tolerances, spatial/intersection truth | `ANYgeometry` |
| Discretization and mesh generation | `ANYmesh` (distribution: `ANYmesher`) |
| Material definitions and material provenance | `ANYmaterial` |
| Interchange and file semantics | `ANYfileIO` / `ANYio` during their migration |
| Optional OCCT interchange backend | `ANYfileio-occt` |
| Solver mathematics, elements, assembly and numerical results | `ANYsolver` |
| Prescriptive and semi-analytical buckling rules | `ANYbuckling` |
| FEM projects, jobs, orchestration and result artifacts | `ANYfem` |
| Engineering application consuming the public owners above | `ANYstructure` |
| Backend-neutral 3D scene/view contracts | `ANY3dView` |
| Tk presentation adapter | `ANYtk3D` |
| Time-series processing | `ANYtimeseries` |
| Intelligence/automation consumers; no duplicated engineering truth | `ANYintelligent` |
| Governance, ecosystem documentation and public coordination | `ANYopenSoft` |
| Product/workspace orchestration; no duplicated domain truth | `ANYworkspaceAI` |
| Experimental/reserved repositories | `ANYtrade`, `anyfea3d` |

Dependencies point from owners to consumers. A consumer must use a public owner
contract, not copy its algorithms, constants, schemas or data. During the
`ANYfileIO`/`ANYio` transition, each task must name one authoritative line and
provide an explicit compatibility path. Headless contracts precede GUI work. SI
units and provenance are required at repository boundaries.

### Engineering doctrine

- Correctness and sound theory outrank speed.
- Hidden corrections, empirical gate-tuning, invented stiffness and silent
  fallback are prohibited.
- Ambiguity fails closed with a typed, actionable error.

## 2. Required development practice

1. Define the intended behavior, owner, compatibility impact and acceptance
   evidence before nontrivial implementation.
2. Keep changes narrow. Do not mix unrelated cleanup, formatting or capability
   expansion into the same change.
3. Treat AI output as untrusted input. A responsible contributor reviews every
   line, verifies licenses and provenance, and runs the same gates required for
   human-written work. Never provide secrets, customer data or restricted
   material to an unapproved model or service.
4. Preserve public compatibility. Breaking changes require an explicit ecosystem
   decision, migration path and later version-policy change; they cannot ship as
   a patch.
5. Never weaken a test, tolerance or validation rule merely to obtain a pass.

## 3. Testing gates

> **Merge rule:** all applicable gates must pass from a clean checkout.

- Every behavior change has focused unit tests; every defect fix has a regression
  that fails without the fix.
- Public interfaces have contract tests. Cross-repository changes test both owner
  and consumer against declared supported versions.
- Numerical and physics changes include independent analytical, published or
  separately implemented references. Comparing code with itself is not
  qualification.
- Physics tests cover units, signs, frames, invariance, conservation/equilibrium,
  limiting cases, convergence and invalid inputs as applicable. Tolerances must
  follow theory or quantified numerical error, never observed output alone.
- Failure, cancellation, timeout, stale-data and fallback paths are tested.
  Fallback is permitted only when explicit, safe and reported.
- Distributions are built and checked; an installed wheel is imported and
  smoke-tested outside the source tree. GUI/executable changes also receive a
  packaged-artifact smoke test on each claimed platform.
- Supported Python and operating-system claims are exercised in CI. A platform or
  version may be removed only by an explicit compatibility decision.
- Skips and expected failures require a recorded reason, owner and removal
  condition. Flaky tests are defects, not acceptable retries.
- Required CI must be green. A red, missing or cancelled gate is not evidence.

Documentation-only changes may use documentation/format checks when they cannot
affect runtime, packaging, commands or public contracts.

## 4. Qualification and traceability

Every qualification claim must identify:

- requirement, issue or decision and the exact qualified scope;
- repository, commit, tree, package version and dependency versions;
- commands, toolchain, Python, OS and relevant hardware;
- input identities, units, origins, licenses and SHA-256 hashes where practical;
- test and benchmark outputs, tolerances, limitations and failed/omitted cases;
- produced artifact identities and the reviewer/approver.

Evidence is immutable or content-addressed and reproducible from recorded inputs.
Generated, transformed and experimental data retain lineage. Standards, material
tables, reference results and third-party models require edition/source and
usage-rights records. Performance evidence never substitutes for correctness.
Claims must not exceed the executed matrix or reference quality.

## 5. Version and release policy

Versions use `MAJOR.MINOR.PATCH`.

> **Current release rule:** increment **PATCH only** until this policy is
> explicitly replaced.

- repository releases increment `A.B.X -> A.B.(X+1)`;
- major and minor increments are reserved and require a new ecosystem decision;
- patch releases must remain backward compatible; incompatible work is deferred
  or protected by a compatible migration/shim;
- package metadata, runtime `__version__`, tests, manifests and release
  documentation must agree;
- tags are `vA.B.X` and must match the built artifact version exactly;
- schemas and file formats carry their own versions and backward-read/migration
  rules; a package bump does not silently change a schema;
- PyPI publication always uses GitHub Actions OIDC Trusted Publishing. API tokens,
  passwords and manual credential uploads are prohibited.

A version bump does not prove qualification. Release requires the testing and
traceability gates above, reviewed artifacts, and explicit publication authority.
