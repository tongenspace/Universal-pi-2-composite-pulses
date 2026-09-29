"""Mathematical and numerical regression checks, independent of plot appearance."""
import json
import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.linalg import expm
from scipy.integrate import solve_ivp
from uvh_validation.catalog import CATALOG, ROOT, phases
from uvh_validation.su2 import (universal_primitive, square_primitive, phase_shift,
                                final_state, probability, universal_probability,
                                square_to_universal, taylor_coefficients)
from uvh_validation.drag import (DragParameters, configuration_issues, parameters_from_config,
                                 hamiltonian, drag_primitive, populations, envelopes)
from uvh_validation.validation import cancellation_report


def test_catalog_structure_and_precision():
    for name, row in CATALOG.items():
        p = row["phases_pi"]
        assert len(p) == row["pulse_count"] == int(name[3:-1])
        assert p[0] == "0"
        assert all(0 <= float(x) < 2 for x in p)
        if name.endswith("s"):
            assert p == p[::-1]
        assert all(x == "0" or len(x.split(".")[1]) == 15 for x in p)


def test_universal_primitive_is_su2():
    u = universal_primitive(np.linspace(-0.5, 0.5, 11), 0.21, 0.8)
    assert_allclose(u.conj().swapaxes(-1, -2) @ u, np.broadcast_to(np.eye(2), u.shape), atol=5e-16)
    assert_allclose(np.linalg.det(u), 1, atol=5e-16)


def test_short_analytic_probabilities():
    e, a = np.meshgrid(np.linspace(-0.2, 0.2, 17), np.linspace(-0.3, 0.3, 19))
    assert_allclose(universal_probability(e, a, [0]), 0.5 + e, atol=3e-16)
    for phi in (np.pi/2, 3*np.pi/2):
        expected = (1 - 4*e**2)*np.cos(a - phi/2)**2
        assert_allclose(universal_probability(e, a, [0, phi]), expected, atol=1e-15)


def test_square_against_matrix_exponential_and_chronological_product():
    for a, d in [(0, 0), (0.8, -0.2), (1, 0), (1.13, 0.17)]:
        u = square_primitive(a, d)
        total = np.eye(2, dtype=complex)
        for phi in phases("UVH5d"):
            h = np.array([[d, a*np.exp(1j*phi)], [a*np.exp(-1j*phi), -d]])/2
            uphi = expm(-1j * h * np.pi/2)
            assert_allclose(phase_shift(u, phi), uphi, atol=7e-16)
            total = uphi @ total
        assert_allclose(final_state(u, phases("UVH5d")), total[:, 0], atol=2e-15)


@pytest.mark.parametrize("name", list(CATALOG))
def test_published_cancellation_conditions(name):
    rows, _ = cancellation_report([name])
    assert rows[0]["passed"], rows[0]


def test_coefficients_reproduce_analytic_lowest_order():
    c = taylor_coefficients(phases("UVH4a"), 2)
    assert_allclose([c[2, 0], c[1, 1], c[0, 2]], [4 - 4*np.sqrt(2), 0, -0.5], atol=5e-15)
    c = taylor_coefficients(phases("UVH5s"), 2)
    assert_allclose(c[2, 0], -0.5, atol=8e-15)
    assert abs(c[0, 2] - 1.46767) < 5e-6


def test_taylor_series_against_exact_propagation():
    for name in ("UVH5a", "UVH7a", "UVH13s"):
        c = taylor_coefficients(phases(name), 5)
        e, a = 0.002, -0.003
        approximation = sum(v*e**m*a**n for (m, n), v in c.items())
        assert abs(approximation - universal_probability(e, a, phases(name))) < 2e-12


def test_exact_map_and_palindromic_symmetry():
    aa, dd = np.meshgrid(np.linspace(0.8, 1.2, 29), np.linspace(-0.2, 0.2, 31))
    u = square_primitive(aa, dd)
    e, a = square_to_universal(u)
    for name in CATALOG:
        p = probability(u, phases(name))
        assert_allclose(p, universal_probability(e, a, phases(name)), atol=6e-15)
        if name.endswith("s"):
            assert_allclose(p, probability(square_primitive(aa, -dd), phases(name)), atol=5e-15)


def test_published_uvh7_pair_is_identical_at_numerical_precision():
    aa, dd = np.meshgrid(np.linspace(0.8, 1.2, 53), np.linspace(-0.2, 0.2, 51))
    u = square_primitive(aa, dd)
    assert_allclose(probability(u, phases("UVH7a")), probability(u, phases("UVH7d")), atol=2e-14, rtol=0)


def test_incomplete_figure3_config_never_uses_silent_defaults():
    config = json.loads((ROOT/"data/figure3_parameters.json").read_text())
    config["two_level"]["kappa"] = None
    assert configuration_issues(config)
    with pytest.raises(ValueError, match="not reproducible"):
        parameters_from_config(config, "two_level")


def test_drag_resonant_limit_and_endpoints():
    params = DragParameters(2, 16, -250, 1, 0, 0)
    assert_allclose(envelopes(0, 1, params), [0, 0], atol=1e-16)
    assert_allclose(envelopes(16, 1, params), [0, 0], atol=1e-16)
    a = np.array([0.8, 1.0, 1.2])
    u = drag_primitive(a, 0, params)
    assert_allclose(u, square_primitive(a, 0), atol=3e-13)
    for name in ("UVH1s", "UVH5s", "UVH13s"):
        assert_allclose(probability(u, phases(name)), probability(square_primitive(a, 0), phases(name)), atol=3e-12)


@pytest.mark.parametrize("levels", [2, 3])
def test_drag_phase_covariance_and_direct_sequence_integration(levels):
    # Nonzero values here exercise the solver, not the missing Figure 3 calibration.
    params = DragParameters(levels, 16, -250, 1.01, 0.4, 0.3)
    a, d = 1.08, -0.12
    phi = phases("UVH5s")[1]
    h = hamiltonian(3.7, a, d, params)
    assert_allclose(h, h.conj().T, atol=1e-16)
    assert_allclose(hamiltonian(3.7, a, d, params, phi), phase_shift(h, phi), atol=3e-16)
    u = drag_primitive(a, d, params)
    assert_allclose(u.conj().T @ u, np.eye(levels), atol=5e-10)
    state = np.eye(levels, dtype=complex)[:, 0]
    for phi in phases("UVH5s"):
        result = solve_ivp(lambda t, y: -1j*hamiltonian(t, a, d, params, phi) @ y,
                           (0, params.duration_ns), state, method="DOP853",
                           rtol=2e-13, atol=2e-15, max_step=0.2)
        assert result.success
        state = result.y[:, -1]
    assert_allclose(final_state(u, phases("UVH5s")), state, atol=5e-10)
    p0, p1, p2 = populations(u, phases("UVH5s"))
    assert abs(p0+p1+p2-1) < 5e-10
    if levels == 3:
        assert p2 > 1e-10
