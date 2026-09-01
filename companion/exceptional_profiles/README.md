# Exceptional depth-three Smith certificates

This package gives bounded exact certificates for the exceptional primes
`p=2` and `p=3`.  It does not extrapolate from finite cases.

`depth3_smith.py` is the exact finite Smith engine shipped with this
repository.  `verify_exceptional_profiles.py` constructs the canonical
point-by-line transpose `B_3^T` and computes its local Smith
valuations by two distinct exact algorithms:

1. minimum-valuation pivot elimination over `Z/p^7 Z`;
2. Bockstein layer peeling.

The two valuation lists must agree, must equal `EXPECTED.json`, and must obey
the rank and weighted-order identities.

`o1_exceptional_certificate.py` separately proves the first-transfer
congruence at `p=2,3`. It constructs a primal line-code representation of a
coarse point-fibre indicator and independently verifies orthogonality to the
full dual nullspace. Affine translation supplies every fibre. The two result
families have separate receipts and no Smith-profile value is used in the
first-transfer calculation.

Run all lanes sequentially:

```text
python verify_exceptional_profiles.py
python -O verify_exceptional_profiles.py
python verify_o1_exceptional.py
python -O verify_o1_exceptional.py
```

The inputs, canonical results and execution receipts are covered by the
public source manifest.
