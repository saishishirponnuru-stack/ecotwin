"""
Tests for Data Integrity, Provenance Tiers, and Leak-Free Baselines
===================================================================
Validates Milestone 1 data engineering corrections:
1. Data provenance tiers and column mappings
2. Physics derivations and unit conversions (Watts, kWh)
3. Absence of target leakage in NON_LEAKY_FEATURES
4. Analytical physics baseline calculation
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.constants import (
    TIER_1_SENSOR_MEASUREMENT,
    TIER_2_PHYSICALLY_DERIVED,
    TIER_3_CALIBRATED_CONTEXT,
    TIER_4_MODEL_OUTPUT,
    TIER_5_SIMULATION_RESULT,
    COLUMN_DATA_TIERS,
)
from src.data.processor import (
    MOTOR_EFFICIENCY,
    compute_analytical_energy,
    process_manufacturing_data,
)
from src.models.predictor import (
    AnalyticalEnergyBaseline,
    EnergyPredictor,
)


def test_data_provenance_tiers_defined():
    """Verify all 5 tiers are distinct and column mappings exist."""
    tiers = {
        TIER_1_SENSOR_MEASUREMENT,
        TIER_2_PHYSICALLY_DERIVED,
        TIER_3_CALIBRATED_CONTEXT,
        TIER_4_MODEL_OUTPUT,
        TIER_5_SIMULATION_RESULT,
    }
    assert len(tiers) == 5

    # Check key columns
    assert COLUMN_DATA_TIERS["torque_nm"] == TIER_1_SENSOR_MEASUREMENT
    assert COLUMN_DATA_TIERS["rotational_speed_rpm"] == TIER_1_SENSOR_MEASUREMENT
    assert COLUMN_DATA_TIERS["power_watts"] == TIER_2_PHYSICALLY_DERIVED
    assert COLUMN_DATA_TIERS["energy_kwh"] == TIER_2_PHYSICALLY_DERIVED
    assert COLUMN_DATA_TIERS["machine_id"] == TIER_3_CALIBRATED_CONTEXT
    assert COLUMN_DATA_TIERS["predicted_kwh"] == TIER_4_MODEL_OUTPUT


def test_compute_analytical_energy_physics_units():
    """
    Verify physics equation:
    Torque = 40.0 Nm
    Speed = 1500 RPM
    Angular velocity omega = 1500 * 2 * pi / 60 = 157.0796 rad/s
    P_mech = 40.0 * 157.0796 = 6283.185 W
    P_elec = 6283.185 / 0.85 = 7391.983 W
    Cycle time = 3.0 min = 0.05 hours
    Energy = 7391.983 * 0.05 / 1000 = 0.369599 kWh
    """
    torque = 40.0
    speed = 1500.0
    cycle_time = 3.0
    efficiency = 0.85

    computed_energy = compute_analytical_energy(
        torque_nm=torque,
        rotational_speed_rpm=speed,
        cycle_time_minutes=cycle_time,
        motor_efficiency=efficiency,
    )

    expected_p_mech = torque * (speed * 2.0 * np.pi / 60.0)
    expected_p_elec = expected_p_mech / efficiency
    expected_energy = (expected_p_elec * (cycle_time / 60.0)) / 1000.0

    assert abs(computed_energy - expected_energy) < 1e-9
    assert abs(computed_energy - 0.369599) < 1e-4


def test_compute_analytical_energy_efficiency_bounds():
    """Verify invalid motor efficiency raises ValueError."""
    with pytest.raises(ValueError):
        compute_analytical_energy(40.0, 1500.0, 3.0, motor_efficiency=0.0)
    with pytest.raises(ValueError):
        compute_analytical_energy(40.0, 1500.0, 3.0, motor_efficiency=1.5)


def test_no_target_leakage_in_non_leaky_features():
    """
    Crucial validation: NON_LEAKY_FEATURES must NOT contain columns
    that algebraically define energy_kwh.
    """
    forbidden_features = {"power_watts", "mechanical_power_watts", "electrical_power_watts", "cycle_time_minutes", "energy_kwh", "sec_kwh_per_part"}
    leaky_found = forbidden_features.intersection(set(EnergyPredictor.NON_LEAKY_FEATURES))
    assert len(leaky_found) == 0, f"Found target leakage in NON_LEAKY_FEATURES: {leaky_found}"


def test_analytical_baseline_predictor():
    """Verify AnalyticalEnergyBaseline class evaluates without fitting."""
    baseline = AnalyticalEnergyBaseline(motor_efficiency=MOTOR_EFFICIENCY)
    df_sample = pd.DataFrame({
        "torque_nm": [40.0, 20.0],
        "rotational_speed_rpm": [1500.0, 3000.0],
        "cycle_time_minutes": [3.0, 1.5],
    })

    predictions = baseline.predict(df_sample)
    assert len(predictions) == 2
    assert (predictions >= 0).all()

    # Part 1: 40 Nm, 1500 rpm, 3.0 min -> ~0.3696 kWh
    assert abs(predictions[0] - 0.369599) < 1e-4
    # Part 2: 20 Nm, 3000 rpm, 1.5 min:
    # 20 * 3000 * 2pi/60 = same power as 40*1500!
    # Cycle time is 1.5 min (half), so energy is exactly half: ~0.1848 kWh
    assert abs(predictions[1] - (predictions[0] / 2.0)) < 1e-6


def test_processor_maintains_backward_compatibility():
    """Verify process_manufacturing_data maintains all legacy columns while adding enhancements."""
    # Create minimal AI4I-like dataframe
    df_mock = pd.DataFrame({
        "UDI": [1, 2],
        "Product ID": ["M001", "L002"],
        "Type": ["M", "L"],
        "Air temperature [K]": [298.1, 298.2],
        "Process temperature [K]": [308.6, 308.7],
        "Rotational speed [rpm]": [1500, 1400],
        "Torque [Nm]": [40.0, 46.0],
        "Tool wear [min]": [0, 5],
        "Machine failure": [0, 0],
        "TWF": [0, 0],
        "HDF": [0, 0],
        "PWF": [0, 0],
        "OSF": [0, 0],
        "RNF": [0, 0],
    })

    processed = process_manufacturing_data(df_mock)

    # Legacy expected columns
    for col in ["power_watts", "cycle_time_minutes", "energy_kwh", "sec_kwh_per_part", "timestamp"]:
        assert col in processed.columns, f"Missing legacy column: {col}"

    # Enhanced transparency columns
    assert "mechanical_power_watts" in processed.columns
    assert "electrical_power_watts" in processed.columns
    assert "temp_diff_k" in processed.columns

    # Verify thermal delta calculation
    assert abs(processed.loc[0, "temp_diff_k"] - (308.6 - 298.1)) < 1e-5
