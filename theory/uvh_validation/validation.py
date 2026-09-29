"""Independent numerical checks and finite-domain measurements."""
import numpy as np
from scipy.stats import qmc
from .catalog import CATALOG, phases
from .su2 import taylor_coefficients, universal_probability


def cancellation_report(names, tolerance=1e-10):
    rows, coefficient_rows = [], []
    for name in names:
        order = CATALOG[name]["cancelled_order"]
        coefficients = taylor_coefficients(phases(name), order + 1)
        target_error = abs(coefficients[0, 0] - 0.5)
        residual = max((abs(v) for (m, n), v in coefficients.items()
                        if 1 <= m + n <= order), default=0.0)
        leading = [v for (m, n), v in coefficients.items() if m + n == order + 1]
        rows.append(dict(sequence=name, cancelled_order=order,
                         target_error=target_error, max_cancelled_coefficient=residual,
                         leading_rms=float(np.sqrt(np.mean(np.square(leading)))),
                         passed=bool(max(target_error, residual) < tolerance)))
        coefficient_rows.extend(dict(sequence=name, epsilon_power=m, alpha_power=n, coefficient=v)
                                for (m, n), v in coefficients.items())
    return rows, coefficient_rows


def disk_area_percent(names, sample_power=20, seed=20260924, radius=0.2, threshold=1e-4):
    """Evaluate Eq. (18) with a reproducible scrambled Sobol disk sample.

    r=R*sqrt(u) gives uniform area, not uniform radius. Chunks limit memory.
    This measures fixed pulse lists and never changes their phases.
    """
    uv = qmc.Sobol(d=2, scramble=True, seed=seed).random_base2(sample_power)
    counts = {name: 0 for name in names}
    for offset in range(0, len(uv), 65536):
        points = uv[offset:offset + 65536]
        radii = radius * np.sqrt(points[:, 0])
        theta = 2 * np.pi * points[:, 1]
        e, a = radii * np.cos(theta), radii * np.sin(theta)
        for name in names:
            error = np.abs(universal_probability(e, a, phases(name)) - 0.5)
            counts[name] += int(np.count_nonzero(error <= threshold))
    return {name: 100.0 * count / len(uv) for name, count in counts.items()}
