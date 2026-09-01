from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "companion" / "affine_hjelmslev_radon_depth3.py"
PDF = ROOT / "paper" / (
    "Depth-Three-Smith-Profiles-and-Newton-Minor-Geometry-for-"
    "Affine-Hjelmslev-Radon-Incidence.pdf"
)


def _load():
    spec = importlib.util.spec_from_file_location("fcig_depth3_companion", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load depth-three companion")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_epsilon1_p2():
    path = ROOT / "companion" / "epsilon1_p2" / "epsilon1_p2_certificate.py"
    spec = importlib.util.spec_from_file_location("fcig_depth3_epsilon1_p2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load p=2 epsilon certificate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


def _public_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Oleksiy Babanskyy",
            "GIT_AUTHOR_EMAIL": "aconsciousfractal@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "Oleksiy Babanskyy",
            "GIT_COMMITTER_EMAIL": "aconsciousfractal@users.noreply.github.com",
        }
    )
    return environment


def _copy_candidate(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "candidate"
    subprocess.run(
        ["git", "clone", "--no-local", str(ROOT), str(target)],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "remove", "origin"],
        cwd=target,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return target


def test_structured_formula_contract_and_symbolic_identities() -> None:
    data, payload = M.load_contract(ROOT / "companion" / "formulas.json")
    assert data["schema"] == "fcig.depth3.formulas.v1"
    assert M.sha256_bytes(payload) == "E307305E6DC754C0DB06DA4E0477332050258B3C38F07F4CD151475BE9B652B7"
    M.validate_profile_identities(data)


@pytest.mark.parametrize(
    ("prime", "expected"),
    [
        (2, (30, 6, 19, 6, 2, 1)),
        (3, (240, 168, 195, 108, 15, 3)),
        (5, (4050, 4140, 4795, 2490, 140, 10)),
        (7, (26740, 34608, 36225, 19488, 567, 21)),
        (11, (363000, 545622, 561979, 297330, 3575, 55)),
    ],
)
def test_profile_controls(prime: int, expected: tuple[int, ...]) -> None:
    assert M.smith_profile(prime) == expected


def test_all_small_prime_rank_and_order_identities() -> None:
    primes = [value for value in range(2, 252) if M.is_prime(value)]
    assert len(primes) == 54
    for prime in primes:
        profile = M.smith_profile(prime)
        assert len(profile) == 6
        assert min(profile) >= 0
        assert sum(profile) == prime**6
        assert sum(index * value for index, value in enumerate(profile)) == (
            M.total_order_exponent(prime)
        )


@pytest.mark.parametrize(
    ("prime", "expected"),
    [
        (3, (3, 3, 18)),
        (5, (12, 8, 250)),
        (7, (28, 15, 1635)),
        (11, (71, 40, 15741)),
    ],
)
def test_newton_controls(prime: int, expected: tuple[int, int, int]) -> None:
    assert M.newton_data(prime) == expected
    assert M.epsilon_1(prime) == expected[2]


def test_boundary_columns_and_minimal_generators_are_not_conflated() -> None:
    assert M.newton_data(5)[:2] == (12, 8)
    assert M.newton_data(7)[:2] == (28, 15)
    assert M.newton_data(11)[:2] == (71, 40)


@pytest.mark.parametrize("value", [False, True, -7, 0, 1, 4, 9, 15, 25, 49, 2.0, "5"])
def test_nonprime_or_ill_typed_inputs_are_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="prime"):
        M.smith_profile(value)
    with pytest.raises(ValueError, match="prime"):
        M.epsilon_1(value)


@pytest.mark.parametrize("value", [2, 4, 9, 25, True])
def test_newton_domain_is_fail_closed(value: object) -> None:
    with pytest.raises(ValueError, match="odd prime"):
        M.newton_data(value)


def test_generated_tex_is_exact_formula_rendering() -> None:
    data, payload = M.load_contract(ROOT / "companion" / "formulas.json")
    expected = M.render_tex(data, M.sha256_bytes(payload))
    actual = (ROOT / "paper" / "generated" / "formulas.tex").read_text(
        encoding="utf-8"
    )
    assert actual == expected


def test_formula_mutations_are_detected() -> None:
    data, _ = M.load_contract(ROOT / "companion" / "formulas.json")
    wrong_schema = copy.deepcopy(data)
    wrong_schema["schema"] = "fcig.depth3.formulas.v0"
    with pytest.raises(AssertionError, match="schema"):
        M.validate_structure(wrong_schema)

    wrong_exception = copy.deepcopy(data)
    wrong_exception["smith_profile"]["exceptional"]["3"][1] += 1
    with pytest.raises(AssertionError, match="exceptional"):
        M.validate_structure(wrong_exception)

    wrong_formula = copy.deepcopy(data)
    wrong_formula["smith_profile"]["branches"]["mod6_1"]["multiplicities"][0][
        "expression"
    ]["factors"][0]["coefficients"][1] += 1
    with pytest.raises(AssertionError, match="symbolic rank"):
        M.validate_profile_identities(wrong_formula)


def test_exceptional_result_agrees_with_formula_object() -> None:
    result = json.loads(
        (ROOT / "companion" / "exceptional_profiles" / "RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["schema"] == "fcig.depth3.exceptional-result.v1"
    for prime in (2, 3):
        row = result["cases"][str(prime)]
        profile = tuple(int(row["profile"].get(str(index), 0)) for index in range(6))
        assert profile == M.smith_profile(prime)
        assert sum(profile) == prime**6
        assert row["weighted_order_exponent"] == M.total_order_exponent(prime)


def test_exceptional_receipt_binds_every_replay_artifact() -> None:
    directory = ROOT / "companion" / "exceptional_profiles"
    receipt = json.loads((directory / "VERIFICATION_RECEIPT.json").read_text(
        encoding="utf-8"
    ))
    assert receipt["schema"] == "fcig.depth3.exceptional-receipt.v1"
    assert receipt["status"] == "PASS"
    for name, identity in receipt["artifacts"].items():
        payload = (directory / name).read_bytes()
        assert len(payload) == identity["bytes"]
        assert hashlib.sha256(payload).hexdigest().upper() == identity["sha256"]
    expected_hash = receipt["artifacts"]["RESULT.json"]["sha256"]
    assert receipt["executions"]["normal"]["result_sha256"] == expected_hash
    assert receipt["executions"]["optimized"]["result_sha256"] == expected_hash


@pytest.mark.parametrize(
    ("relative", "schema"),
    [
        (
            "exceptional_profiles/O1_VERIFICATION_RECEIPT.json",
            "fcig.depth3.o1-exceptional-receipt.v1",
        ),
        (
            "cross_chart_p3/VERIFICATION_RECEIPT.json",
            "fcig.depth3.cross-chart-p3-receipt.v1",
        ),
        (
            "epsilon1_p2/VERIFICATION_RECEIPT.json",
            "fcig.depth3.epsilon1-p2-receipt.v1",
        ),
    ],
)
def test_bounded_transfer_receipts_bind_every_artifact(
    relative: str, schema: str,
) -> None:
    receipt_path = ROOT / "companion" / relative
    directory = receipt_path.parent
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == schema
    assert receipt["status"] == "PASS"
    for name, identity in receipt["artifacts"].items():
        payload = (directory / name).read_bytes()
        assert len(payload) == identity["bytes"]
        assert hashlib.sha256(payload).hexdigest().upper() == identity["sha256"]
    result_hash = next(
        identity["sha256"]
        for name, identity in receipt["artifacts"].items()
        if name.endswith("RESULT.json")
    )
    assert receipt["executions"]["normal"]["result_sha256"] == result_hash
    assert receipt["executions"]["optimized"]["result_sha256"] == result_hash


def test_companion_receipt_is_deterministic_and_typed() -> None:
    first = M.verify()
    second = M.verify()
    assert first == second
    assert first["schema"] == "fcig.depth3.companion-receipt.v1"
    assert first["status"] == "PASS"
    assert first["prime_identity_census"] == 54
    assert first["newton_controls"]["5"] == [12, 8, 250]
    assert first["branch_h_coefficients"]["mod6_1"][2] == [
        0, 6, 135, 1200, 5508, 13824, 15552,
    ]
    assert first["branch_h_coefficients"]["mod6_5"][5] == [10, 27, 18]


def test_residue_class_substitutions_have_nonnegative_integer_coefficients() -> None:
    data, _ = M.load_contract(ROOT / "companion" / "formulas.json")
    controls = M.branch_h_coefficients(data)
    assert set(controls) == {"mod6_1", "mod6_5"}
    assert all(len(rows) == 6 for rows in controls.values())
    assert all(
        type(value) is int and value >= 0
        for rows in controls.values()
        for coefficients in rows
        for value in coefficients
    )


def test_p2_epsilon_certificate_reconstructs_the_rank_increment() -> None:
    engine = _load_epsilon1_p2()
    result = engine.certificate()
    assert result["epsilon_1"] == 1
    assert result["rank_lanes"]["rref"] == {
        "first_chart": 8,
        "first_plus_nonunit_rows": 9,
        "first_plus_unit_rows": 8,
        "swapped_chart": 8,
        "two_chart": 9,
    }
    assert result["rank_lanes"]["bitset"]["first_chart"] == 8
    assert result["rank_lanes"]["bitset"]["two_chart"] == 9
    assert result["restriction_to_kernel"]["kernel_dimension"] == 24
    assert result["restriction_to_kernel"]["ranks"] == {
        "AS_on_kernel_A": 1,
        "nonunit_AS_on_kernel_A": 1,
        "unit_AS_on_kernel_A": 0,
    }


def test_p2_epsilon_certificate_rejects_loss_of_the_cross_chart() -> None:
    engine = _load_epsilon1_p2()
    first_chart, swapped_chart, _ = engine.build_chart_matrices()
    assert engine.rank_rref(first_chart) == 8
    assert engine.rank_rref(first_chart + swapped_chart) == 9
    zero_cross_chart = [[0] * engine.SOURCE_DIMENSION for _ in swapped_chart]
    assert engine.rank_rref(first_chart + zero_cross_chart) == 8
