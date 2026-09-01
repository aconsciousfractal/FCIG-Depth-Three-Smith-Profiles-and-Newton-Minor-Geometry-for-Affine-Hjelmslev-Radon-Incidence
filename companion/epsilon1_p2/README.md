# Exact `p=2` obstruction certificate

This bounded package computes `epsilon_1(2,3)` directly from the definition
in the paper. It does not use the exceptional Smith profile as an input.

Put `N=8`, `N0=e=4`, and work in

```text
F_2[Z]/(Phi_8(Z)) = F_2[Z]/(Z^4+1).
```

On the 32 basis vectors `X^i Y^j`, with `0 <= i < 4` and `0 <= j < 8`,
the certificate constructs the two evaluation matrices

```text
A[(t,b),(i,j)]  = [Z^b] Z^(i+t*j),
AS[(t,b),(i,j)] = [Z^b] Z^(t*i+j).
```

The second formula is the swapped truncated chart: truncation is invisible
after evaluation because `(Z-1)^4=0`. Two independent eliminations give

```text
rank_F2(A)       = 8,
rank_F2([A; AS]) = 9,
epsilon_1(2,3)   = 9 - 8 = 1.
```

The calculation also constructs a 24-dimensional basis of `ker(A)` and
checks independently that `rank(AS|ker(A))=1`. Unit-slope rows contribute
no increment, whereas the 16 nonunit rows capture the full increment. A
displayed `9 x 9` minor supplies an explicit lower-rank witness.

Run the normal and optimized lanes sequentially:

```powershell
python verify_epsilon1_p2.py
python -O verify_epsilon1_p2.py
```

Both runs are read-only and must reproduce `RESULT.json`. This certificate
is exact only for `(p,n)=(2,3)` and makes no inference for another prime.
