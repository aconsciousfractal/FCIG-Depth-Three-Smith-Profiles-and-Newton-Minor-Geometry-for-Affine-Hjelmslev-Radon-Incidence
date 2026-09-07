# Reviewer quickstart

This package separates proof review, bounded computation and release
integrity. The paper contains the all-prime proof; the software checks the
shipped formulas, finite certificates and exact repository surface.

## 1. Verify the package

```powershell
python -m pip install --require-hashes -r requirements.lock
$PythonAbsolute = (Get-Command python).Source
$GitAbsolute = (Get-Command git).Source
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
& $PythonAbsolute -I -S -B -O scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
```

Each run checks the source and release manifests, public PDF, current Git
commit and tree, structured formula object and canonical companion receipt. It must
end with `PASS`. Verification is offline and writes no result file.

## 2. Run the focused hostile suite

```powershell
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --module pytest -- `
  -q -p no:cacheprovider `
  --basetemp "$env:TEMP\fcig-depth3-reviewer-pytest" `
  tests/test_depth3_smith_profiles.py tests/test_release_assurance.py
```

The suite attacks non-prime inputs, branch selection, formula atoms,
boundary/generator confusion, generated-TeX drift, undeclared paths, reparse
points, active PDF content, private production residue, ambient Git
redirection and replacement/graft/alternate-object rewriting.  It also checks
that ordinary successors, merges, tags and remotes do not invalidate content
verification.

## 3. Read the mathematical spine

The principal dependency chain is:

1. maximal-order quotient and exact point-fibre transfer;
2. depth-three modular rank and cyclic top-shell count;
3. tripotent-sector reduction to a truncated q-Pascal common image;
4. exact q-Lucas block product and supported-column classification;
5. boundary generation and the q-Newton minors theorem;
6. closed threshold inversion, Hilbert/Fitting data and
   `epsilon_1(p,3)`;
7. typed cross-chart divided-carry closure;
8. assembly of all six Smith multiplicities.

The companion receipt additionally records the exact coefficient arrays
obtained after the substitutions `p=6h+1` and `p=6h+5`; every entry must be
a nonnegative integer.

Scrutinize in particular the strict minimum in the Newton minors, the
distinction between boundary columns and minimal generators, the exceptional
`p=2,3` branches, and the cross-chart combine-before-division step.

## 4. Inspect public boundaries

- [docs/PUBLIC_CLAIM_BOUNDARY.md](docs/PUBLIC_CLAIM_BOUNDARY.md) states
  affirmative claims and explicit nonclaims.
- [docs/SOURCE_AND_ATTRIBUTION.md](docs/SOURCE_AND_ATTRIBUTION.md)
  separates imported inputs, adjacent literature and manuscript arguments.
- [docs/REPRODUCIBILITY_BOUNDARY.md](docs/REPRODUCIBILITY_BOUNDARY.md)
  states exactly what software recomputes.
- [AI_USE.md](AI_USE.md) records the model's mathematical role and the
  author's responsibility for the final content.
- [LICENSE_SCOPE.md](LICENSE_SCOPE.md) separates manuscript copyright from
  MIT software and documentation.

No third-party paper, dataset or source tree is bundled.

## 5. Replay the exceptional certificates

The `p=2,3` replay is intentionally separate because part of it constructs the
point-by-line matrices `B_3^T` of shapes `64 x 96` and `729 x 972`. It also
authenticates the exceptional first-transfer congruence, a direct `p=2`
two-chart rank calculation, and the bounded `p=3` cross-chart calculation.
Run all eight lanes strictly sequentially;
never launch normal and optimized copies in parallel:

```powershell
python companion/exceptional_profiles/verify_exceptional_profiles.py
python -O companion/exceptional_profiles/verify_exceptional_profiles.py
python companion/exceptional_profiles/verify_o1_exceptional.py
python -O companion/exceptional_profiles/verify_o1_exceptional.py
python companion/cross_chart_p3/verify_cross_chart_p3.py
python -O companion/cross_chart_p3/verify_cross_chart_p3.py
python companion/epsilon1_p2/verify_epsilon1_p2.py
python -O companion/epsilon1_p2/verify_epsilon1_p2.py
```

Each normal/optimized pair must reproduce its tracked result byte-for-byte.
These finite checks are bounded certificates, not an all-prime interpolation
argument.

## 6. Build and inspect the paper

Follow [REPRODUCE.md](REPRODUCE.md). Two clean fixed-epoch builds must be
byte-identical on the declared toolchain. Inspect every rendered page,
equation, table, citation, link and metadata field. The release checker
requires A4, `/Lang=en-US`, plain running pages and the author on the first
page only.

The PDF is not claimed to conform to PDF/UA; the exact limitation and source
fallback are stated in [ACCESSIBILITY.md](ACCESSIBILITY.md).

## Explicit exclusions

- no closed Smith profile at arbitrary depth;
- no projective-to-affine incidence-matrix identification;
- no finite-computation proof of an all-prime theorem;
- no general Rees/strictness theorem for arbitrary filtered intersections;
- no novelty, priority or exhaustive source-search conclusion;
