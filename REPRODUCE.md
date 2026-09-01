# Reproducing the package

## Supported environment

- CPython 3.12, 3.13 or 3.14 on x86-64 Windows or x86-64 Linux;
- exact packages and hashes from `requirements.lock`;
- LuaLaTeX, Biber and latexmk for the paper;
- Poppler and pypdf 6.14.2 for independent PDF inspection.

The reference Windows build uses MiKTeX 25.12, LuaHBTeX 1.24.0 and Biber 2.21
with explicit passes. The workflow performs the equivalent latexmk build and
semantic checks on Ubuntu.

## Install the locked environment

```bash
python -m pip install --require-hashes -r requirements.lock
```

`requirements.txt` lists direct dependencies for readability;
`requirements.lock` is the installation contract. Dependency installation
may access a package index. Verification and paper-build commands below are
offline.

## Exact replay

The verifier binds its result to the current commit and tree.  It accepts an
ordinary Git history, including corrective commits, merges, tags, remotes and
detached CI checkouts.  The checkout itself must be clean and its tracked path
census must agree with the declared release surface.

On PowerShell:

```powershell
$PythonAbsolute = (Get-Command python).Source
$GitAbsolute = (Get-Command git).Source
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
& $PythonAbsolute -I -S -B -O scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/verify.py
```

On POSIX:

```bash
PYTHON_ABSOLUTE=$(python -I -S -c 'import sys; print(sys.executable)')
GIT_ABSOLUTE=$(command -v git)
"$PYTHON_ABSOLUTE" -I -S -B scripts/runtime_bootstrap.py \
  --git-executable "$GIT_ABSOLUTE" --target scripts/verify.py
"$PYTHON_ABSOLUTE" -I -S -B -O scripts/runtime_bootstrap.py \
  --git-executable "$GIT_ABSOLUTE" --target scripts/verify.py
```

Each run prints a canonical companion receipt and ends with `PASS`. The
optimized run guards against validation that depends on Python `assert`.
The bootstrap records absolute Python/Git identities, strips ambient
selection variables and supplies a minimal subprocess environment.

## Hostile suite

PowerShell:

```powershell
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --module pytest -- `
  -q -p no:cacheprovider `
  --basetemp "$env:TEMP\fcig-depth3-pytest" `
  tests/test_depth3_smith_profiles.py tests/test_release_assurance.py
```

POSIX:

```bash
"$PYTHON_ABSOLUTE" -I -S -B scripts/runtime_bootstrap.py \
  --git-executable "$GIT_ABSOLUTE" --module pytest -- \
  -q -p no:cacheprovider --basetemp /tmp/fcig-depth3-pytest \
  tests/test_depth3_smith_profiles.py tests/test_release_assurance.py
```

An optional optimized pytest run is a compatibility smoke test only because
Python optimization removes ordinary assertions from test bodies.

## Bounded exceptional replay

The pure-standard-library `p=2` obstruction certificate constructs the two
`32 x 32` chart matrices over `F_2`, verifies their ranks by RREF and an
independent bitset lane, and obtains `epsilon_1(2,3)=9-8=1`. Run its two
small lanes sequentially:

```powershell
& $PythonAbsolute -I -B companion/epsilon1_p2/verify_epsilon1_p2.py
& $PythonAbsolute -I -B -O companion/epsilon1_p2/verify_epsilon1_p2.py
```

The exceptional engine depends on NumPy and constructs the point-by-line
matrices `B_3^T`, of shapes `64 x 96` and `729 x 972`. Run strictly
sequentially:

```powershell
& $PythonAbsolute -B companion/exceptional_profiles/verify_exceptional_profiles.py
& $PythonAbsolute -O -B companion/exceptional_profiles/verify_exceptional_profiles.py
& $PythonAbsolute -B companion/exceptional_profiles/verify_o1_exceptional.py
& $PythonAbsolute -O -B companion/exceptional_profiles/verify_o1_exceptional.py
& $PythonAbsolute -B companion/cross_chart_p3/verify_cross_chart_p3.py
& $PythonAbsolute -O -B companion/cross_chart_p3/verify_cross_chart_p3.py
```

The Smith lanes reproduce `companion/exceptional_profiles/RESULT.json`; the
other three pairs reproduce their own tracked result files. Do not launch any
of these processes concurrently. The main verifier authenticates all tracked
results and receipts without repeating the expensive computations.

## Integrity layers

```powershell
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/check_manifest.py
& $PythonAbsolute -I -S -B scripts/runtime_bootstrap.py `
  --git-executable $GitAbsolute --target scripts/check_release.py
```

`MANIFEST_SHA256.txt` covers every environment-independent source file
except itself, `RELEASE_SHA256.txt` and the compiled PDF. The release
manifest authenticates the source manifest and title-named PDF.

The release checker rejects undeclared paths, symlinks/reparse points,
alternate streams, local workspace paths, private production codes, active
PDF content, multiple EOF markers, non-A4 output, missing language or front
matter, replacement refs, grafts, alternates and a dirty checkout.  It checks
Git object connectivity without imposing a branching, tagging or remote
policy.

## Deterministic paper build

Run from `paper/` on Windows:

```powershell
$env:SOURCE_DATE_EPOCH = "1788134400"
$env:FORCE_SOURCE_DATE = "1"
$Stem = "Depth-Three-Smith-Profiles-and-Newton-Minor-Geometry-for-Affine-Hjelmslev-Radon-Incidence"
lualatex -interaction=nonstopmode -halt-on-error -file-line-error "-jobname=$Stem" main.tex
biber $Stem
lualatex -interaction=nonstopmode -halt-on-error -file-line-error "-jobname=$Stem" main.tex
lualatex -interaction=nonstopmode -halt-on-error -file-line-error "-jobname=$Stem" main.tex
```

On POSIX, `SOURCE_DATE_EPOCH=1788134400 FORCE_SOURCE_DATE=1 latexmk
-lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex`
is the equivalent workflow command.

The title-named output is
`Depth-Three-Smith-Profiles-and-Newton-Minor-Geometry-for-Affine-Hjelmslev-Radon-Incidence.pdf`.
Build in two clean temporary copies and require byte equality. Independently
inspect all pages, fonts, links, metadata and extracted text. TeX engines may
write user-level caches outside the checkout; those caches are environmental
and are not release inputs.

## Limits

The formula replay, exceptional matrices and hostile mutations are checks,
not a replacement for the paper's proof. This package makes no arbitrary-depth
Smith formula, novelty, priority, exhaustive-search or PDF/UA claim.
