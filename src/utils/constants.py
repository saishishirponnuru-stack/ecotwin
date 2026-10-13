"""Configurable industrial energy and operational constants for EcoTwin.

This module centralizes all physical, regulatory, tariff, and equipment constants
used across data ingestion, feature engineering, model training, explainability,
and what-if optimization.
"""

from typing import Any, Dict, Final, List, Tuple

# ==============================================================================
# 1. EMISSIONS & GRID REGULATORY CONSTANTS
# ==============================================================================
# Central Electricity Authority (CEA) India, CO2 Baseline Database for the Indian Power Sector (Ver 19.0)
# Weighted average grid emission factor for National Grid (kg CO2 per kWh)
GRID_EMISSION_FACTOR: Final[float] = 0.716  # kg CO2 / kWh

# Conversion helper: 1 metric ton CO2 = 1000 kg CO2
KG_CO2_PER_TON: Final[float] = 1000.0


# ==============================================================================
# 2. TARIFF & FINANCIAL CONSTANTS (Maharashtra MSEDCL Industrial Benchmark)
# ==============================================================================
# Average industrial HT-I tariff rate in INR per kWh (Maharashtra State Electricity Distribution Co.)
BASE_TARIFF_INR: Final[float] = 8.50  # INR / kWh

# Time of Use (TOU) tariff tier multipliers
PEAK_MULTIPLIER: Final[float] = 1.20      # 18:00 to 22:00 IST (+20% surcharge)
OFFPEAK_MULTIPLIER: Final[float] = 0.80   # 22:00 to 06:00 IST (-20% rebate)
NORMAL_MULTIPLIER: Final[float] = 1.00    # 06:00 to 18:00 IST (Base rate)

# Power factor regulatory thresholds (MSEDCL rules)
# Power factor below 0.90 incurs heavy penalty; PF between 0.95 and 1.00 qualifies for incentives
POWER_FACTOR_PENALTY_THRESHOLD: Final[float] = 0.90
POWER_FACTOR_INCENTIVE_THRESHOLD: Final[float] = 0.95
POWER_FACTOR_TARGET: Final[float] = 0.98

# Demand charge rate (₹/kVA of billed demand per month)
DEMAND_CHARGE_INR_PER_KVA: Final[float] = 475.0

# Structured TOU definitions
TOU_SCHEDULE: Final[Dict[str, Dict[str, Any]]] = {
    "OFFPEAK": {
        "name": "Night Off-Peak",
        "multiplier": OFFPEAK_MULTIPLIER,
        "rate_inr": BASE_TARIFF_INR * OFFPEAK_MULTIPLIER,
        "hours": [22, 23, 0, 1, 2, 3, 4, 5],
        "description": "Lowest tariff window, ideal for energy-intensive batch jobs",
    },
    "NORMAL": {
        "name": "Day Normal",
        "multiplier": NORMAL_MULTIPLIER,
        "rate_inr": BASE_TARIFF_INR * NORMAL_MULTIPLIER,
        "hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        "description": "Standard working daytime hours",
    },
    "PEAK": {
        "name": "Evening Peak",
        "multiplier": PEAK_MULTIPLIER,
        "rate_inr": BASE_TARIFF_INR * PEAK_MULTIPLIER,
        "hours": [18, 19, 20, 21],
        "description": "Maximum grid demand window, avoid non-essential heavy machinery",
    },
}


# ==============================================================================
# 3. FACILITY, MACHINES & OPERATIONAL SHIFTS
# ==============================================================================
# Monitored CNC machining / injection molding machine cells
MACHINE_IDS: Final[List[str]] = ["M-01", "M-02", "M-03", "M-04"]

# Plant shift definitions (3x 8-hour rolling shifts)
SHIFTS: Final[Dict[str, Dict[str, Any]]] = {
    "Shift_1": {
        "name": "Morning Shift",
        "hours": list(range(6, 14)),  # 06:00 to 14:00
        "start_hour": 6,
        "end_hour": 14,
        "nominal_production_target": 350,  # parts per shift
    },
    "Shift_2": {
        "name": "Evening Shift",
        "hours": list(range(14, 22)),  # 14:00 to 22:00
        "start_hour": 14,
        "end_hour": 22,
        "nominal_production_target": 350,
    },
    "Shift_3": {
        "name": "Night Shift",
        "hours": list(range(22, 24)) + list(range(0, 6)),  # 22:00 to 06:00
        "start_hour": 22,
        "end_hour": 6,
        "nominal_production_target": 300,
    },
}

# Mapping of individual hour (0-23) to shift key
HOUR_TO_SHIFT: Final[Dict[int, str]] = {
    h: ("Shift_1" if 6 <= h < 14 else ("Shift_2" if 14 <= h < 22 else "Shift_3"))
    for h in range(24)
}


# ==============================================================================
# 4. PRODUCT TYPES & TYPICAL ENERGY PROFILES
# ==============================================================================
# Product variants based on AI4I 2020 dataset (L: Low variant 50%, M: Medium 30%, H: High 20%)
PRODUCT_TYPES: Final[Dict[str, Dict[str, Any]]] = {
    "L": {
        "name": "Low Variant",
        "code": "L",
        "description": "Lightweight / high-volume consumer product",
        "share_percent": 50.0,
        "nominal_cycle_time_s": 45.0,
        "nominal_part_weight_kg": 0.25,
        "target_sec_kwh_per_unit": 0.12,
        "target_sec_kwh_per_kg": 0.48,
        "expected_torque_nm_range": (30.0, 50.0),
        "expected_speed_rpm_range": (1400.0, 1800.0),
    },
    "M": {
        "name": "Medium Variant",
        "code": "M",
        "description": "Intermediate reinforced structural component",
        "share_percent": 30.0,
        "nominal_cycle_time_s": 60.0,
        "nominal_part_weight_kg": 0.40,
        "target_sec_kwh_per_unit": 0.18,
        "target_sec_kwh_per_kg": 0.45,
        "expected_torque_nm_range": (35.0, 60.0),
        "expected_speed_rpm_range": (1350.0, 1650.0),
    },
    "H": {
        "name": "High Variant",
        "code": "H",
        "description": "Heavy-duty / high-precision engineered component",
        "share_percent": 20.0,
        "nominal_cycle_time_s": 90.0,
        "nominal_part_weight_kg": 0.75,
        "target_sec_kwh_per_unit": 0.28,
        "target_sec_kwh_per_kg": 0.37,
        "expected_torque_nm_range": (40.0, 75.0),
        "expected_speed_rpm_range": (1200.0, 1550.0),
    },
}


# ==============================================================================
# 5. ELECTRO-MECHANICAL & POWERTRAIN EFFICIENCY
# ==============================================================================
# Typical premium IE3 three-phase induction motor operating at ~75% rated load
MOTOR_EFFICIENCY: Final[float] = 0.85

# Modern variable frequency drive (VFD) / servo drive efficiency
DRIVE_EFFICIENCY: Final[float] = 0.92

# Combined electro-mechanical drivetrain efficiency
TOTAL_ELECTROMECHANICAL_EFFICIENCY: Final[float] = MOTOR_EFFICIENCY * DRIVE_EFFICIENCY  # ~0.782

# Baseline tare / auxiliary continuous load (hydraulics, cooling fan, CNC controller) in kW
AUXILIARY_BASE_LOAD_KW: Final[float] = 2.50


# ==============================================================================
# 6. SPECIFIC ENERGY CONSUMPTION (SEC) INDUSTRIAL BENCHMARKS
# ==============================================================================
# Specific Energy Consumption (SEC) benchmarks for plastics injection molding / precision machining
# Measured in kWh per kg of processed polymer / metal
SEC_BENCHMARK_KWH_PER_KG: Final[Dict[str, float]] = {
    "theoretical_thermodynamic_min": 0.15,  # Theoretical enthalpy to melt polymer (PET/PP)
    "best_in_class_all_electric": 0.35,      # High-efficiency servo-electric press
    "good_servo_hydraulic": 0.50,            # Modern variable-speed pump hydraulic press
    "average_hydraulic": 0.70,               # Standard plant operating baseline
    "poor_inefficient": 1.10,                # Worn pumps, throttling valves, uninsulated barrels
}

# Per-unit SEC target mapping (kWh per finished part)
SEC_TARGET_KWH_PER_UNIT: Final[Dict[str, float]] = {
    "L": 0.12,
    "M": 0.18,
    "H": 0.28,
}

# Threshold % deviation above baseline SEC that triggers an energy waste alert
SEC_DRIFT_ALERT_THRESHOLD_PCT: Final[float] = 15.0


# ==============================================================================
# 7. ANOMALY DETECTION THRESHOLDS (Statistical Z-Score Multipliers)
# ==============================================================================
# Statistical sigma deviation thresholds for energy and vibration/torque monitoring
ANOMALY_THRESHOLDS: Final[Dict[str, float]] = {
    "watch": 1.5,     # 1.5 sigma (~86.6% normal distribution coverage)
    "warning": 2.0,   # 2.0 sigma (~95.4% normal distribution coverage)
    "critical": 3.0,  # 3.0 sigma (~99.7% normal distribution coverage)
}


# ==============================================================================
# 8. PHYSICAL FEATURE BOUNDS & TRAINING VALIDATION RANGES
# ==============================================================================
# Physical bounds calibrated against AI4I 2020 predictive maintenance dataset
# Used for input sanity validation and preventing ML extrapolation in What-If simulations
FEATURE_RANGES: Final[Dict[str, Tuple[float, float]]] = {
    # Ambient air temperature [Kelvin]: min 295.3 K (~22°C), max 304.5 K (~31.5°C)
    "air_temperature_k": (290.0, 310.0),
    # Process temperature [Kelvin]: min 305.7 K (~32.5°C), max 313.8 K (~40.6°C)
    "process_temperature_k": (300.0, 320.0),
    # Spindle rotational speed [RPM]: min 1168, max 2886
    "rotational_speed_rpm": (1000.0, 3000.0),
    # Spindle torque [Nm]: min 3.8, max 76.6
    "torque_nm": (1.0, 100.0),
    # Cumulative tool wear [minutes]: min 0, max 253
    "tool_wear_min": (0.0, 300.0),
    # Mechanical power [Watts]: min ~500 W, max ~25,000 W
    "mechanical_power_w": (500.0, 25000.0),
    # Electrical power consumption [kW]
    "electrical_power_kw": (0.5, 35.0),
    # Power factor: 0.0 to 1.0 (or percentage 0 to 100)
    "power_factor": (0.50, 1.00),
    # Specific energy consumption [kWh/unit]
    "sec_kwh_per_unit": (0.05, 1.50),
}

# Standardized column aliases for AI4I 2020 raw dataset
AI4I_RAW_COLUMNS: Final[List[str]] = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

AI4I_COLUMN_MAPPING: Final[Dict[str, str]] = {
    "UDI": "udi",
    "Product ID": "product_id",
    "Type": "product_type",
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
    "TWF": "failure_twf",
    "HDF": "failure_hdf",
    "PWF": "failure_pwf",
    "OSF": "failure_osf",
    "RNF": "failure_rnf",
}
