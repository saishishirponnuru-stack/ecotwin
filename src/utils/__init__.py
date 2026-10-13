"""EcoTwin Utilities Module.

Provides industrial constants, tariff structures, emissions factors,
and data validation functions for manufacturing energy intelligence.
"""

from src.utils.constants import (
    ANOMALY_THRESHOLDS,
    BASE_TARIFF_INR,
    DRIVE_EFFICIENCY,
    FEATURE_RANGES,
    GRID_EMISSION_FACTOR,
    MACHINE_IDS,
    MOTOR_EFFICIENCY,
    OFFPEAK_MULTIPLIER,
    PEAK_MULTIPLIER,
    POWER_FACTOR_PENALTY_THRESHOLD,
    PRODUCT_TYPES,
    SEC_BENCHMARK_KWH_PER_KG,
    SEC_TARGET_KWH_PER_UNIT,
    SHIFTS,
    TOTAL_ELECTROMECHANICAL_EFFICIENCY,
    TOU_SCHEDULE,
)
from src.utils.validators import (
    ValidationReport,
    clamp_to_training_range,
    safe_sec_calculation,
    validate_energy_data,
    validate_prediction_input,
)

__all__ = [
    "GRID_EMISSION_FACTOR",
    "BASE_TARIFF_INR",
    "PEAK_MULTIPLIER",
    "OFFPEAK_MULTIPLIER",
    "POWER_FACTOR_PENALTY_THRESHOLD",
    "ANOMALY_THRESHOLDS",
    "MACHINE_IDS",
    "SHIFTS",
    "PRODUCT_TYPES",
    "MOTOR_EFFICIENCY",
    "DRIVE_EFFICIENCY",
    "TOTAL_ELECTROMECHANICAL_EFFICIENCY",
    "SEC_BENCHMARK_KWH_PER_KG",
    "SEC_TARGET_KWH_PER_UNIT",
    "FEATURE_RANGES",
    "TOU_SCHEDULE",
    "ValidationReport",
    "validate_energy_data",
    "safe_sec_calculation",
    "validate_prediction_input",
    "clamp_to_training_range",
]
