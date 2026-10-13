"""Data validation and physical constraint verification utilities for EcoTwin.

This module enforces industrial data integrity, prevents division-by-zero
in Specific Energy Consumption (SEC) calculations, validates What-If
simulation parameters, and protects machine learning models from
out-of-distribution extrapolation.
"""

import logging
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.utils.constants import FEATURE_RANGES, PRODUCT_TYPES

logger = logging.getLogger(__name__)


class ValidationReport(NamedTuple):
    """Structured report returned by dataset validation checks."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


def validate_energy_data(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    allow_zero_energy: bool = True,
) -> ValidationReport:
    """Validate manufacturing and energy telemetry dataframes.

    Checks:
      1. Non-empty DataFrame structure.
      2. Presence of required schema columns.
      3. Absence of negative energy or power values.
      4. Physical sanity of temperatures (Kelvin > 0), speeds (RPM >= 0),
         torque (>= 0), and tool wear (>= 0).
      5. Excessive missing / null values.

    Args:
        df: Input pandas DataFrame to validate.
        required_columns: List of column names that must be present. If None,
            checks for standard energy/operational fields if present.
        allow_zero_energy: Whether 0.0 energy is permissible (e.g. idle/standby).
            If False, values <= 0 will be flagged as errors.

    Returns:
        ValidationReport: NamedTuple containing `is_valid` (bool), `errors` (list of str),
        and `warnings` (list of str).
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(df, pd.DataFrame):
        return ValidationReport(
            is_valid=False,
            errors=[f"Input must be a pandas DataFrame, got {type(df).__name__}"],
            warnings=[],
        )

    if df.empty:
        return ValidationReport(
            is_valid=False,
            errors=["DataFrame is empty (0 rows)."],
            warnings=[],
        )

    # 1. Required column presence
    if required_columns is not None:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

    # 2. Check for null / NaN counts
    null_counts = df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if not cols_with_nulls.empty:
        for col, count in cols_with_nulls.items():
            pct = (count / len(df)) * 100.0
            if pct > 10.0:
                errors.append(f"Column '{col}' has excessive missing values: {count} ({pct:.1f}%)")
            else:
                warnings.append(f"Column '{col}' contains {count} ({pct:.1f}%) null values")

    # 3. Non-negative Energy & Power checks
    energy_col_candidates = [
        "energy_kwh",
        "Usage_kWh",
        "mechanical_power_w",
        "electrical_power_kw",
        "power_w",
        "power_kw",
    ]
    for col in energy_col_candidates:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            negative_count = (series < 0).sum()
            if negative_count > 0:
                errors.append(
                    f"Column '{col}' contains {negative_count} negative energy/power values (min: {series.min()})"
                )
            if not allow_zero_energy:
                zero_count = (series == 0).sum()
                if zero_count > 0:
                    warnings.append(f"Column '{col}' contains {zero_count} zero values.")

    # 4. Physical telemetry sanity checks
    # Temperatures: Must be in reasonable Kelvin range (270K - 370K) if named in K
    temp_cols = [c for c in df.columns if "temperature" in c.lower() or "[k]" in c.lower()]
    for col in temp_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if (series <= 0).any():
                errors.append(f"Temperature column '{col}' has values <= 0 K.")
            if (series < 270.0).any() or (series > 370.0).any():
                warnings.append(
                    f"Temperature column '{col}' has values outside typical shop floor range (270-370 K): "
                    f"[{series.min():.1f}, {series.max():.1f}]"
                )

    # Rotational speed (RPM >= 0)
    speed_cols = [c for c in df.columns if "speed" in c.lower() or "rpm" in c.lower()]
    for col in speed_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if (series < 0).any():
                errors.append(f"Rotational speed column '{col}' has negative values.")

    # Torque (Nm >= 0)
    torque_cols = [c for c in df.columns if "torque" in c.lower()]
    for col in torque_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if (series < 0).any():
                errors.append(f"Torque column '{col}' has negative values.")

    # Tool wear (min >= 0)
    tool_wear_cols = [c for c in df.columns if "tool wear" in c.lower() or "tool_wear" in c.lower()]
    for col in tool_wear_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if (series < 0).any():
                errors.append(f"Tool wear column '{col}' has negative values.")

    # Power Factor (0.0 to 1.0 or 0 to 100)
    pf_cols = [c for c in df.columns if "power_factor" in c.lower() or "pf" in c.lower()]
    for col in pf_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            # If percentage scaled (0-100)
            if series.max() > 1.0:
                if (series < 0.0).any() or (series > 100.0).any():
                    errors.append(f"Power factor percentage '{col}' out of range [0, 100].")
            else:
                if (series < 0.0).any() or (series > 1.0).any():
                    errors.append(f"Power factor '{col}' out of range [0.0, 1.0].")

    is_valid = len(errors) == 0
    return ValidationReport(is_valid=is_valid, errors=errors, warnings=warnings)


def safe_sec_calculation(
    energy: Union[float, int, np.ndarray, pd.Series],
    units: Union[float, int, np.ndarray, pd.Series],
    default: float = 0.0,
    eps: float = 1e-6,
) -> Union[float, np.ndarray, pd.Series]:
    """Safely calculate Specific Energy Consumption (SEC = Energy / Units).

    Guarantees protection against:
      - Zero production units (division by zero / NaN / Inf).
      - Negative production units or energy values.
      - Works uniformly across scalar numbers, numpy arrays, and pandas Series.

    Formula:
      SEC = Energy / Units  if Units > eps, else default

    Args:
        energy: Energy consumption (kWh) or mechanical energy (Joules/kWh).
        units: Number of produced parts or production mass (kg).
        default: Fallback SEC value when production is zero or invalid (default: 0.0).
        eps: Minimum positive threshold to consider production non-zero.

    Returns:
        SEC value with identical shape and container type as inputs.
    """
    # Case 1: Pandas Series
    if isinstance(energy, pd.Series) or isinstance(units, pd.Series):
        s_energy = pd.Series(energy) if not isinstance(energy, pd.Series) else energy
        s_units = pd.Series(units) if not isinstance(units, pd.Series) else units

        # Align series index
        if not s_energy.index.equals(s_units.index):
            s_units = s_units.reindex(s_energy.index, fill_value=0.0)

        valid_mask = (s_units > eps) & (s_energy >= 0)
        sec = pd.Series(default, index=s_energy.index, dtype=float)
        sec.loc[valid_mask] = s_energy.loc[valid_mask] / s_units.loc[valid_mask]
        return sec

    # Case 2: Numpy Array
    if isinstance(energy, np.ndarray) or isinstance(units, np.ndarray):
        arr_energy = np.asarray(energy, dtype=float)
        arr_units = np.asarray(units, dtype=float)

        valid_mask = (arr_units > eps) & (arr_energy >= 0)
        sec_arr = np.full_like(arr_energy, fill_value=default, dtype=float)
        np.divide(arr_energy, arr_units, out=sec_arr, where=valid_mask)
        return sec_arr

    # Case 3: Scalar float / int
    try:
        f_energy = float(energy)
        f_units = float(units)
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid numerical input to safe_sec_calculation: %s", exc)
        return default

    if f_units <= eps or f_energy < 0 or np.isnan(f_units) or np.isnan(f_energy):
        return default

    return f_energy / f_units


def validate_prediction_input(
    params: Dict[str, Any],
    ranges_dict: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Tuple[bool, List[str]]:
    """Validate user input parameters for What-If scenario simulations.

    Ensures that incoming operational adjustments are within plausible
    physical bounds and known machine learning training bounds,
    preventing erratic predictions.

    Args:
        params: Dictionary of feature names and prospective setpoints.
        ranges_dict: Mapping of feature names to (min, max) allowable bounds.
            Defaults to FEATURE_RANGES from constants.py.

    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
    """
    if ranges_dict is None:
        ranges_dict = FEATURE_RANGES

    errors: List[str] = []

    if not isinstance(params, dict):
        return False, [f"Prediction params must be a dict, got {type(params).__name__}"]

    if not params:
        return False, ["Prediction params dictionary cannot be empty."]

    # Check Product Type if present
    if "product_type" in params:
        p_type = str(params["product_type"]).upper()
        if p_type not in PRODUCT_TYPES:
            errors.append(
                f"Invalid product_type '{params['product_type']}'. Must be one of {list(PRODUCT_TYPES.keys())}"
            )

    # Check numeric bounds against ranges_dict
    for feature_name, value in params.items():
        if feature_name == "product_type":
            continue

        if value is None or (isinstance(value, float) and np.isnan(value)):
            errors.append(f"Parameter '{feature_name}' cannot be null/NaN.")
            continue

        if not isinstance(value, (int, float, np.number)):
            errors.append(f"Parameter '{feature_name}' must be numeric, got {type(value).__name__}.")
            continue

        val_float = float(value)
        if feature_name in ranges_dict:
            min_bound, max_bound = ranges_dict[feature_name]
            if val_float < min_bound or val_float > max_bound:
                errors.append(
                    f"Parameter '{feature_name}' value {val_float} is out of allowable training range "
                    f"[{min_bound}, {max_bound}]."
                )

    return (len(errors) == 0), errors


def clamp_to_training_range(
    value: float,
    feature_name: str,
    ranges_dict: Optional[Dict[str, Tuple[float, float]]] = None,
) -> float:
    """Clamp a feature value strictly within its calibrated training range.

    Prevents machine learning model extrapolation failures when user-defined
    what-if simulations test extreme boundary conditions.

    Args:
        value: Numerical value to evaluate.
        feature_name: Feature identifier matching ranges_dict keys.
        ranges_dict: Mapping of feature names to (min, max) bounds.
            Defaults to FEATURE_RANGES from constants.py.

    Returns:
        float: The original value if within bounds, or the clamped bound.
    """
    if ranges_dict is None:
        ranges_dict = FEATURE_RANGES

    if feature_name not in ranges_dict:
        logger.debug(
            "Feature '%s' not found in training ranges; skipping clamping.",
            feature_name,
        )
        return float(value)

    min_val, max_val = ranges_dict[feature_name]

    if value < min_val:
        logger.warning(
            "Clamping '%s': input %.3f is below training minimum %.3f. Clamped to %.3f.",
            feature_name,
            value,
            min_val,
            min_val,
        )
        return float(min_val)

    if value > max_val:
        logger.warning(
            "Clamping '%s': input %.3f is above training maximum %.3f. Clamped to %.3f.",
            feature_name,
            value,
            max_val,
            max_val,
        )
        return float(max_val)

    return float(value)
