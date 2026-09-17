# Mode-shape and buckling performance gate

## Scope

This gate compares the frozen spectral baseline (`ANYsolver c31a223`,
`ANYstructure 10ad181`) with the spectral-performance candidate.  The
qualified Q4/S3 mechanics, mass policies, tolerances, residual filters,
qualification evidence, selectors, and defaults are unchanged.

All reported timing runs used one numerical-library thread.  The complete
route is the actual ANYstructure adapter from prepared generated geometry
through static solution, prestress recovery, eigenvalue buckling, residual
checks, and usable mode visualization.

## Accepted changes

- Buckling mode visualization no longer performs an unrelated full physical
  stress recovery for every mode.  It reports translational mode amplitude,
  matching its existing label, while the accepted static state retains the
  single physical recovery.
- Supported unshifted buckling explicitly supplies the inverse of the elastic
  stiffness metric to ARPACK.  An immutable analysis session may retain this
  elastic factor only; geometric stiffness and the eigenproblem are rebuilt
  for every changed prestress state.  Current-state factors remain solve-local.
- Supported reference-elastic modal extraction uses zero-shift inverse
  iteration instead of the slow unshifted smallest-magnitude search.  Singular
  free-body, descriptor, shifted, prestressed, and current-state routes retain
  their existing admission and factor-ownership rules.
- `RuntimeAnalysisContext` now admits eligible reference-elastic
  static-plus-buckling runs.  It retains model, stiffness, constraints and
  elastic factors, while structural/mass changes invalidate the context.
  Cylinder runs that install a buckling-only lid gauge remain excluded.
- Modal and buckling diagnostics now expose phase timings, reduced matrix
  dimensions/nonzeros/storage, factor fill, factor memory, cache disposition,
  and mode-visualization time.

## Results

Representative coarse girder panel: 405 nodes, 364 qualified Q4 shells,
274 legacy B2 beams, 2,430 total DOFs and 2,347 reduced DOFs.

| Route | Baseline median | Candidate median | Improvement | Candidate MAD / p95 |
|---|---:|---:|---:|---:|
| Static + 5 buckling modes, complete route (7 runs) | 8.704 s | 5.214 s | 1.67x / 40.1% | 0.032 / 5.260 s |
| Static + 10 buckling modes, complete route (3-run screen) | 13.230 s | 6.395 s | 2.07x / 51.7% | 0.002 / 6.397 s |
| Repeated changed-load static + 5 buckling modes | about 8.7 s (spectral context ineligible) | about 3.7 s | about 2.35x | diagnostic screen |
| Modal-only, 5 modes, retained model/factors (7 runs) | exceeded 120 s inactivity bound | 1.568 s | greater than 76x lower-bound | 0.007 / 1.611 s |

The 5- and 10-mode buckling factors were unchanged to displayed binary64
precision.  The optimized modal result has maximum original-pencil residual
below `8e-12`, mass-orthogonality error below `2e-15`, and matches an
independent dense solve by frequency and clustered modal subspace.

The installed candidate wheels were exercised outside both source trees
through the actual ANYstructure adapter.  The complete 5-mode route returned
`ok`, the same five buckling factors, and five usable mode visualizations.

## Verification

- 213 relevant ANYsolver modal, buckling, analysis-session, runtime and
  qualified-shell tests passed.  Protected CI exposed and this branch closes a
  pre-existing trusted-scope exception-precedence defect: finalization still
  runs, while its generic cleanup error can no longer replace the specific
  operation-time capability rejection.
- Dedicated regressions cover the unshifted modal zero-shift factor, elastic
  buckling inverse reuse, the singular-stiffness fallback, dense-reference
  eigenvalues/subspaces, visualization without stress recovery, and spectral
  context eligibility.
- Independent implementation re-review reported no remaining P0/P1/P2
  findings and confirmed that mechanics, selectors and defaults are unchanged.
- The established static-only tests remain in the retained regression set.
- Wheel build and isolated import succeeded for ANYsolver 0.4.6 and
  ANYstructure 6.4.1; no release or version change is part of this gate.

## Deferred options

Further vectorization of mode-to-node serialization is not promoted: after the
stress-recovery removal, visualization is only about 0.06 s for five modes and
0.12 s for ten, so it cannot clear the 10% complete-route threshold.
Alternative sparse backends and GPU factorization are also deferred on this
fixture: factorization is below 0.01 s.  The new dominant buckling costs are
qualified authority/residual checks and prestress/geometric-operator assembly;
those require a separate safety-reviewed optimization rather than a backend
swap.
