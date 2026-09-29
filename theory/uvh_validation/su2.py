"""Exact two-level propagation and probability Taylor coefficients.

Phases are in radians; lists are chronological. The first basis state is |0>.
"""

from math import factorial
import numpy as np


def universal_primitive(epsilon, alpha, phase=0.0):
    """Equation (1), with beta absorbed into the programmed phase."""
    epsilon, alpha = np.broadcast_arrays(epsilon, alpha)
    if np.any(np.abs(epsilon) > 0.5):
        raise ValueError("The SU(2) primitive requires |epsilon| <= 1/2.")
    u = np.empty(epsilon.shape + (2, 2), dtype=complex)
    u[..., 0, 0] = np.sqrt(0.5 - epsilon) * np.exp(1j * alpha)
    u[..., 1, 1] = u[..., 0, 0].conj()
    u[..., 0, 1] = -1j * np.sqrt(0.5 + epsilon) * np.exp(1j * phase)
    u[..., 1, 0] = -u[..., 0, 1].conj()
    return u


def square_primitive(amplitude_ratio, detuning_ratio):
    """exp(-i H T), with Omega0*T=pi/2 and H from Section IV.

    amplitude_ratio = Omega/Omega0; detuning_ratio = Delta/Omega0.
    This sets the duration once, independent of both control errors.
    """
    a, d = np.broadcast_arrays(amplitude_ratio, detuning_ratio)
    radius = np.hypot(a, d)
    c = np.cos(np.pi * radius / 4)
    s_over_radius = (np.pi / 4) * np.sinc(radius / 4)
    u = np.empty(a.shape + (2, 2), dtype=complex)
    u[..., 0, 0] = c - 1j * d * s_over_radius
    u[..., 1, 1] = c + 1j * d * s_over_radius
    u[..., 0, 1] = -1j * a * s_over_radius
    u[..., 1, 0] = u[..., 0, 1]
    return u


def phase_shift(primitive, phase):
    """D U D^dagger, D_jj=exp(-i*j*phase), for two or three levels."""
    dimension = primitive.shape[-1]
    if primitive.shape[-2] != dimension:
        raise ValueError("A square propagator is required.")
    d = np.exp(-1j * np.arange(dimension) * phase)
    return primitive * d[:, None] * d.conj()[None, :]


def final_state(primitive, phases):
    """Apply U_phiN ... U_phi1 to |0>, preserving coherent leakage."""
    state = np.zeros(primitive.shape[:-1], dtype=complex)
    state[..., 0] = 1.0
    for phase in phases:
        state = np.einsum("...ij,...j->...i", phase_shift(primitive, phase), state)
    return state


def probability(primitive, phases):
    """Unconditional |1> population, without postselection or renormalization."""
    return np.abs(final_state(primitive, phases)[..., 1]) ** 2


def universal_probability(epsilon, alpha, phases):
    return probability(universal_primitive(epsilon, alpha), phases)


def square_to_universal(primitive):
    """Exact map on the plotted square-pulse domain; beta=0 there."""
    return np.abs(primitive[..., 1, 0]) ** 2 - 0.5, np.angle(primitive[..., 0, 0])


def taylor_coefficients(phases, degree):
    """Evaluate Eqs. (10)-(12) at fixed phases; no phase search or fitting.

    Dictionary (m,n) -> ordinary coefficient of epsilon**m * alpha**n.
    Coefficients already include 1/(m! n!). Truncation uses total degree.
    """
    indices = [(m, d - m) for d in range(degree + 1) for m in range(d + 1)]
    half_binomial = [1.0]
    for m in range(1, degree + 1):
        half_binomial.append(half_binomial[-1] * (1.5 - m) / m)
    product = {key: np.zeros((2, 2), dtype=complex) for key in indices}
    product[0, 0] = np.eye(2, dtype=complex)
    for phase in phases:
        pulse = {}
        for m, n in indices:
            diagonal = half_binomial[m] * (-2) ** m / np.sqrt(2)
            u = np.diag([diagonal * 1j**n / factorial(n),
                         diagonal * (-1j)**n / factorial(n)]).astype(complex)
            if n == 0:
                b = -1j * half_binomial[m] * 2**m / np.sqrt(2)
                u[0, 1] = b * np.exp(1j * phase)
                u[1, 0] = b * np.exp(-1j * phase)
            pulse[m, n] = u
        result = {}
        for m, n in indices:
            result[m, n] = sum(
                (pulse[p, q] @ product[m - p, n - q]
                 for p in range(m + 1) for q in range(n + 1)),
                np.zeros((2, 2), dtype=complex),
            )
        product = result
    amplitude = {key: value[1, 0] for key, value in product.items()}
    coefficients = {}
    for m, n in indices:
        value = sum(amplitude[p, q] * amplitude[m - p, n - q].conjugate()
                    for p in range(m + 1) for q in range(n + 1))
        if abs(value.imag) > 1e-10:
            raise ArithmeticError("Probability coefficient acquired an imaginary part.")
        coefficients[m, n] = float(value.real)
    return coefficients
