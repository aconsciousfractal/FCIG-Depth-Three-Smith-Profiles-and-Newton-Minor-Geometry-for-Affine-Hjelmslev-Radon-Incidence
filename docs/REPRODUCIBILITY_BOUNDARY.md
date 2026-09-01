# Reproducibility boundary

## Recomputed by the main companion

The standalone module reads only `companion/formulas.json` and tracked
certificate bytes. It:

- validates the complete structured formula grammar;
- expands both polynomial branches exactly over the rationals;
- proves the symbolic rank and weighted-order identities;
- substitutes `p=6h+1` and `p=6h+5` in all twelve multiplicities and
  verifies that every resulting coefficient is a nonnegative integer;
- evaluates every prime up to 251;
- checks the tracked exact rows for `p=2,3,5,7,11`;
- reconstructs boundary-column, minimal-generator and common-image-length
  controls for `p=3,5,7,11`;
- checks that the generated TeX fragment is exactly the formula rendering.

It uses no network, random source, untracked input or external dataset and
writes no scientific output.

## Exceptional certificates

`companion/exceptional_profiles/` constructs the canonical point--line
incidence matrices for `p=2,3` and computes their local Smith valuations by
minimum-valuation elimination and Bockstein layer peeling. The two lanes must
agree with each other and with the tracked result. A second two-lane
certificate proves the first-transfer congruence at the same primes by a
primal line-code solution and full dual-nullspace orthogonality.

`companion/cross_chart_p3/` reconstructs the 378 Newton labels at `p=3`,
proves the `162 x 18` surviving cross matrix has rank 18, and checks all 360
divided carries using two finite-field membership criteria. These replays are
bounded and sequential; none is extrapolated to another prime.

`companion/epsilon1_p2/` builds the first-chart matrix `A` and swapped-chart
matrix `AS` directly from `Phi_8(Z)=Z^4+1`. Independent RREF and bitset lanes
give `rank(A)=8` and `rank([A;AS])=9`; restriction to the 24-dimensional
kernel of `A` independently has rank one. Thus it certifies
`epsilon_1(2,3)=1` without reading any Smith-profile multiplicity.

## Proof boundary

Software does not enumerate symbolic minors for arbitrary `p`, prove the
unique Newton minimum, establish boundary generation, or prove the uniform
cross-chart theorem. Those are written mathematical arguments in the paper.
The exceptional packages prove only their explicitly bounded finite claims;
finite agreement cannot prove the all-prime formulas.

## Integrity and environment

`MANIFEST_SHA256.txt` authenticates environment-independent source bytes.
`RELEASE_SHA256.txt` separately authenticates the manifest and compiled PDF.
Release-authoritative checks enter through an isolated no-site bootstrap that
records the selected Python and Git executables and strips ambient selection
variables.

The release checker rejects undeclared files, reparse points, alternate
streams, local-path residue, active PDF content, non-A4 pages, missing
language metadata, replacement objects, grafts, alternates and a dirty
checkout.  It binds the result to the current commit and tree while allowing
ordinary corrective commits, merges, tags, remotes and detached CI checkouts.

The Python hygiene scanner is finite and declared. Its mutation suite checks
the enumerated reconstruction classes; it is not a theorem about arbitrary
obfuscation.
