"""Fixed-parameter two- and three-level DRAG propagation.

Time is in ns; all internal frequencies are angular frequencies in rad/ns.
No calibration, phase optimization, or renormalization is performed here.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp
from .su2 import final_state


@dataclass(frozen=True)
class DragParameters:
    levels: int
    duration_ns: float
    anharmonicity_MHz: float
    kappa: float
    carrier_offset_MHz: float
    beta_ns: float

    def __post_init__(self):
        if self.levels not in (2, 3):
            raise ValueError("Only two- and three-level models are supported.")
        values = [self.duration_ns, self.anharmonicity_MHz, self.kappa,
                  self.carrier_offset_MHz, self.beta_ns]
        if not np.all(np.isfinite(values)) or self.duration_ns <= 0 or self.kappa <= 0:
            raise ValueError("Finite fixed parameters, positive T and positive kappa are required.")

    @property
    def omega0(self):
        return self.kappa * np.pi / self.duration_ns


def configuration_issues(config):
    issues = []
    for model in ("two_level", "three_level"):
        for key in ("kappa", "carrier_offset_MHz", "beta_ns"):
            value = config.get(model, {}).get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value):
                issues.append(f"{model}.{key}: fixed numerical value not supplied")
        kappa = config.get(model, {}).get("kappa")
        if isinstance(kappa, (int, float)) and kappa <= 0:
            issues.append(f"{model}.kappa: must be positive")
    if config.get("convention_confirmed_for_manuscript") is not True:
        issues.append("DRAG quadrature, rotating-frame Hamiltonian, and detuning conventions unconfirmed")
    if not config.get("calibration_source"):
        issues.append("calibration_source: provenance of fixed inputs not supplied")
    return issues


def parameters_from_config(config, model):
    issues = configuration_issues(config)
    if issues:
        raise ValueError("Figure 3 is not reproducible from the available inputs:\n" + "\n".join(issues))
    return DragParameters(levels={"two_level": 2, "three_level": 3}[model],
                          duration_ns=config["duration_ns"],
                          anharmonicity_MHz=config["anharmonicity_MHz"], **config[model])


def envelopes(t, amplitude_ratio, params):
    """Both I and Q scale with the same relative amplitude error."""
    peak = np.asarray(amplitude_ratio) * params.omega0
    theta = np.pi * t / params.duration_ns
    in_phase = peak * np.sin(theta)**2
    derivative = peak * np.pi / params.duration_ns * np.sin(2 * theta)
    return in_phase, params.beta_ns * derivative


def hamiltonian(t, amplitude_ratio, detuning_ratio, params, phase=0.0):
    a, d = np.broadcast_arrays(amplitude_ratio, detuning_ratio)
    in_phase, quadrature = envelopes(t, a, params)
    coupling = (in_phase + 1j * quadrature) * np.exp(1j * phase)
    delta = 2 * np.pi * params.carrier_offset_MHz / 1000 + d * params.omega0
    anharmonicity = 2 * np.pi * params.anharmonicity_MHz / 1000
    n = np.arange(params.levels)
    h = np.zeros(a.shape + (params.levels, params.levels), dtype=complex)
    h[..., n, n] = -delta[..., None] * n + 0.5 * anharmonicity * n * (n - 1)
    for j in range(params.levels - 1):
        h[..., j, j + 1] = np.sqrt(j + 1) * coupling / 2
        h[..., j + 1, j] = h[..., j, j + 1].conj()
    return h


def drag_primitive(amplitude_ratio, detuning_ratio, params, *, rtol=2e-11,
                   atol=2e-13, max_step_fraction=1/32, batch_size=128):
    """Integrate dU/dt=-i H(t) U once per grid point; retain the full unitary.

    Small batches limit memory. DOP853 is checked with tighter tolerances in
    the notebook; it is never used to vary a pulse or find a calibration.
    """
    a, d = np.broadcast_arrays(amplitude_ratio, detuning_ratio)
    shape, dimension = a.shape, params.levels
    aflat, dflat = a.ravel(), d.ravel()
    matrices = np.empty((a.size, dimension, dimension), dtype=complex)
    for start in range(0, a.size, batch_size):
        aa, dd = aflat[start:start + batch_size], dflat[start:start + batch_size]
        count = len(aa)
        u0 = np.broadcast_to(np.eye(dimension, dtype=complex), (count, dimension, dimension)).copy()

        def rhs(t, vector):
            u = vector.reshape(count, dimension, dimension)
            return (-1j * (hamiltonian(t, aa, dd, params) @ u)).ravel()

        solution = solve_ivp(rhs, (0, params.duration_ns), u0.ravel(), method="DOP853",
                             rtol=rtol, atol=atol, max_step=params.duration_ns * max_step_fraction,
                             t_eval=[params.duration_ns])
        if not solution.success:
            raise RuntimeError(solution.message)
        matrices[start:start + count] = solution.y[:, -1].reshape(count, dimension, dimension)
    return matrices.reshape(shape + (dimension, dimension))


def populations(primitive, phases):
    """Return P0, P1 and P2, retaining loss from the computational subspace."""
    state = final_state(primitive, phases)
    p = np.abs(state)**2
    p2 = p[..., 2] if p.shape[-1] == 3 else np.zeros(p.shape[:-1])
    return p[..., 0], p[..., 1], p2
