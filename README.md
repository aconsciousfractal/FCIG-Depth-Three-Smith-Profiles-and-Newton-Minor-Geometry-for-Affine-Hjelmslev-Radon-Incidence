# Depth-Three Smith Profiles and Newton-Minor Geometry for Affine Hjelmslev--Radon Incidence

Companion repository for the paper

> **Depth-Three Smith Profiles and Newton-Minor Geometry for Affine
> Hjelmslev--Radon Incidence**
> Oleksiy Babanskyy, 2026.

Paper: [PDF](paper/Depth-Three-Smith-Profiles-and-Newton-Minor-Geometry-for-Affine-Hjelmslev-Radon-Incidence.pdf) ·
[LaTeX source](paper/main.tex) · [bibliography](paper/references.bib) ·
[AI-use disclosure](AI_USE.md)

The paper studies the integer line-by-point incidence matrix of the affine
plane over `Z/p^3 Z`, with primitive normal directions modulo units. It
determines the complete `p`-primary Smith profile for every prime. The new
uniform layer identifies the first unresolved integral obstruction with a
truncated q-Pascal common image and computes its determinantal ideals by a
q-Newton basis.

## Main depth-three result

For the transpose of the affine incidence matrix `B_3`,

```text
coker(B_3^T)_(p)
  = direct-sum_{i=1}^5 (Z/p^i Z)^[m_i(p)],
```

with exponent `p^5`. The six Smith multiplicities
`(m_0,...,m_5)` are explicit polynomials on
`p = 1 mod 6` and `p = 5 mod 6`, with separately proved exact rows

```text
p=2: (30, 6, 19, 6, 2, 1)
p=3: (240, 168, 195, 108, 15, 3).
```

The complete branch formulas are displayed in the paper and represented
machine-readably in [companion/formulas.json](companion/formulas.json).
They satisfy

```text
sum_i m_i(p)       = p^6
sum_i i*m_i(p)     = (3*p^6 - p^5 - p^3 - p)/2
```

for every prime. Finite calculations are supporting checks, not a proof by
interpolation.

## Structural output beyond the Smith row

The Newton-minor analysis also determines the common-image Hilbert series,
Fitting data, boundary-column count and minimal number of generators. The
public controls distinguish the last two quantities:

| `p` | boundary columns | minimal generators | `epsilon_1(p,3)` |
|---:|---:|---:|---:|
| 3 | 3 | 3 | 18 |
| 5 | 12 | 8 | 250 |
| 7 | 28 | 15 | 1635 |
| 11 | 71 | 40 | 15741 |

The typed cross-chart divided-carry theorem then closes the remaining
transfer defect before the exact Smith bookkeeping is applied.

## What the companion checks

The standalone companion:

- validates the structured formula object and both residue-class branches;
- proves the rank and weighted-order identities symbolically over the
  rationals;
- expands all twelve residue-class multiplicities after `p=6h+1` and
  `p=6h+5` and proves every coefficient is a nonnegative integer;
- evaluates every prime up to 251 and five tracked exact profile controls;
- reconstructs the Newton boundary, generator and length controls above;
- binds the exceptional `p=2,3` result to two exact algorithms;
- reconstructs `epsilon_1(2,3)=1` directly from first- and two-chart ranks
  `8` and `9`, without using a Smith-profile multiplicity as input;
- rejects non-prime and incorrectly typed inputs;
- verifies the declared repository surface, title-named PDF, source and
  release manifests, and a clean checkout of the current Git `HEAD`.

The exceptional replay constructs the canonical incidence matrices and uses
minimum-valuation local Smith elimination and Bockstein layer peeling. It is
bounded to `p=2,3` and is never extrapolated.

## Quick verification

Use an isolated Python environment and the hash-locked dependency set:

```powershell
python -m pip install --require-hashes -r requirements.lock
$PythonAbsolute = (Get-Command python).Source
$GitAbsolute = (Get-Command git).Source
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
& $PythonAbsolute -I -S -B -O scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --module pytest -- `
  -q -p no:cacheprovider `
  --basetemp "$env:TEMP\fcig-depth3-pytest" `
  tests/test_depth3_smith_profiles.py tests/test_release_assurance.py
```

Both verifier runs must end with `PASS`. Tests are deterministic, access no
network and write no scientific result file. The expensive exceptional replay
is documented separately and must be run sequentially:

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

See [REPRODUCE.md](REPRODUCE.md) for POSIX commands, fixed-epoch paper builds
and exact integrity layers.

## Repository layout

| Path | Role |
|---|---|
| `paper/` | article source, generated formula fragment, cited-only bibliography and title-named PDF |
| `companion/` | structured all-prime formulas and exact arithmetic |
| `companion/exceptional_profiles/` | bounded Smith-profile and first-transfer certificates for `p=2,3` |
| `companion/cross_chart_p3/` | bounded `p=3` Newton and divided-carry certificate |
| `companion/epsilon1_p2/` | exact two-chart rank certificate for `epsilon_1(2,3)=1` |
| `tests/` | mathematical, hostile and release-integrity controls |
| `scripts/` | one-command verifier and fail-closed release checks |
| `docs/` | claim, attribution and reproducibility boundaries |
| `.github/workflows/verify.yml` | Python replay and double paper build |

## Citation, licence and accessibility

- Citation metadata: [CITATION.cff](CITATION.cff).
- Licence boundary: [LICENSE_SCOPE.md](LICENSE_SCOPE.md).
- Dependency notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Accessibility status: [ACCESSIBILITY.md](ACCESSIBILITY.md).
- Claim boundary: [docs/PUBLIC_CLAIM_BOUNDARY.md](docs/PUBLIC_CLAIM_BOUNDARY.md).
- AI-use disclosure and author responsibility: [AI_USE.md](AI_USE.md).

Copyright in the manuscript is retained by Oleksiy Babanskyy. The MIT licence
applies to original companion software and supporting documentation, not to
the manuscript or compiled paper.

No novelty, firstness, priority or exhaustive-literature claim is made.
