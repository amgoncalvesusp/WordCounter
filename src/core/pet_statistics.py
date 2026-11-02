"""Descriptive PET statistics on consecutive annual changes, never on levels.

Excess kurtosis uses the corrected sample estimator returned by Excel CURT/KURT;
the reported Pearson value is that estimate plus three, not the raw moment ratio.
L-kurtosis is the ratio of unbiased sample L-moments l4/l2 (Hosking's PWM method).

Sources:
https://support.microsoft.com/en-us/excel/functions/kurt-function
https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/probmome.htm
https://doi.org/10.1111/j.2517-6161.1990.tb01775.x
"""

from math import comb, fsum, isfinite
from numbers import Integral, Real
from typing import Sequence


def _validated_levels(points: Sequence[tuple[int, float]]) -> list[dict]:
    try:
        observations = iter(points)
    except TypeError as error:
        raise ValueError("Informe uma série de pares (ano, valor).") from error
    levels = []
    years = set()
    for point in observations:
        try:
            year, value = point
        except (TypeError, ValueError) as error:
            raise ValueError("Cada observação deve conter ano e valor.") from error
        if isinstance(year, bool) or not isinstance(year, Integral) or not 1 <= year <= 9999:
            raise ValueError("O ano deve ser inteiro entre 1 e 9999.")
        if year in years:
            raise ValueError(f"Ano duplicado na série: {year}.")
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"O valor de {year} deve ser numérico, finito e não negativo.")
        try:
            number = float(value)
        except (ValueError, OverflowError) as error:
            raise ValueError(f"O valor de {year} deve ser finito.") from error
        if not isfinite(number) or number < 0:
            raise ValueError(f"O valor de {year} deve ser finito e não negativo.")
        years.add(year)
        levels.append({"year": int(year), "value": number})
    return sorted(levels, key=lambda row: row["year"])


def _annual_changes(levels: list[dict], method: str) -> tuple[list[dict], list[str]]:
    changes = []
    warnings = []
    for previous, current in zip(levels, levels[1:]):
        year, value = current["year"], current["value"]
        old_year, old_value = previous["year"], previous["value"]
        change = None
        if year != old_year + 1:
            warnings.append(
                f"Lacuna entre {old_year} e {year}: variação anual não calculada."
            )
        elif method == "relative" and old_value == 0:
            warnings.append(
                f"Base zero em {old_year}: variação relativa de {year} não calculada."
            )
        else:
            change = value - old_value
            if method == "relative":
                change = (change / old_value) * 100
            if not isfinite(change):
                warnings.append(f"Variação de {year} não finita: observação excluída.")
                change = None
        changes.append({
            "year": year, "previous_year": old_year, "previous_value": old_value,
            "value": value, "change": change,
        })
    return changes, warnings


def _shape_estimates(values: list[float]) -> tuple[float, float] | None:
    # Scale before taking powers, so finite changes cannot overflow the moments.
    scale = max(abs(value) for value in values)
    if scale == 0:
        return None
    scaled = [value / scale for value in values]
    mean = fsum(scaled) / len(scaled)
    centered = [value - mean for value in scaled]
    spread = max(abs(value) for value in centered)
    if spread == 0:
        return None
    sample = sorted(value / spread for value in centered)
    n = len(sample)
    sum2 = fsum(value * value for value in sample)
    sum4 = fsum(value ** 4 for value in sample)
    excess = (
        n * (n + 1) * (n - 1) * sum4 / ((n - 2) * (n - 3) * sum2 * sum2)
        - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    )
    b = [
        fsum(comb(i, order) / comb(n - 1, order) * sample[i]
             for i in range(order, n)) / n
        for order in range(4)
    ]
    l2 = 2 * b[1] - b[0]
    l4 = 20 * b[3] - 30 * b[2] + 12 * b[1] - b[0]
    return excess, l4 / l2


def analyze_series(
    points: Sequence[tuple[int, float]], method: str = "difference"
) -> dict:
    """Analyze nonnegative annual levels without modifying the input.

    ``difference`` returns current minus previous value (percentage points when
    levels are percentages). ``relative`` returns 100 * difference / previous.
    Missing years and zero relative baselines stay undefined, never imputed.
    ``n_changes`` counts only valid consecutive annual changes. Both shape
    estimators require at least four such changes and nonconstant changes.
    The warning below 20 changes is a heuristic, not an inferential threshold.
    """
    if method not in ("difference", "relative"):
        raise ValueError("Método inválido: use 'difference' ou 'relative'.")
    levels = _validated_levels(points)
    changes, warnings = _annual_changes(levels, method)
    valid = [row["change"] for row in changes if row["change"] is not None]
    excess = l_kurtosis = None
    if len(valid) < 4:
        warnings.append(
            "São necessárias ao menos 4 variações anuais válidas para calcular "
            "curtose e L-curtose."
        )
    else:
        estimates = _shape_estimates(valid)
        if estimates is None:
            warnings.append("Variações constantes: curtose e L-curtose são indefinidas.")
        else:
            excess, l_kurtosis = estimates
        if len(valid) < 20:
            warnings.append(
                "Série curta (<20 variações): estimativas podem ser instáveis; "
                "20 é um limiar heurístico, não um teste de significância."
            )
    return {
        "method": method, "levels": levels, "changes": changes,
        "n_levels": len(levels), "n_changes": len(valid),
        "pearson_kurtosis": None if excess is None else excess + 3,
        "excess_kurtosis": excess, "l_kurtosis": l_kurtosis,
        "warnings": warnings,
    }
