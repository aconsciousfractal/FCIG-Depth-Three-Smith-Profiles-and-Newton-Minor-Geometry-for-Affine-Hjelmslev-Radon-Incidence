# Bounded p=3 cross-chart certificate

This package reconstructs the Newton source at `p=3` directly from the
cyclotomic remainder relation. It verifies all 378 first-chart kernel labels,
classifies 360 individually zero cross-chart labels, and proves that the
remaining `162 x 18` cross matrix has rank 18. It then computes the divided
cross carry for every zero-cross label and checks membership by two distinct
finite-field criteria: the appropriate line-row space and the corresponding
annihilator differences.

Run the normal and optimized lanes sequentially:

```powershell
python verify_cross_chart_p3.py
python -O verify_cross_chart_p3.py
```

Both runs are read-only and must reproduce `RESULT.json`. This is a bounded
exceptional-prime certificate. It is not an interpolation argument and does
not replace the uniform proof for primes at least five.
