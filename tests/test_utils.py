"""Unit tests for EcoTwin constants and validators."""

import unittest
import numpy as np
import pandas as pd

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
    SHIFTS,
)
from src.utils.validators import (
    clamp_to_training_range,
    safe_sec_calculation,
    validate_energy_data,
    validate_prediction_input,
)


class TestConstants(unittest.TestCase):
    """Verify configured constants match specifications."""

    def test_regulatory_and_tariff_constants(self):
        self.assertEqual(GRID_EMISSION_FACTOR, 0.716)
        self.assertEqual(BASE_TARIFF_INR, 8.50)
        self.assertEqual(PEAK_MULTIPLIER, 1.20)
        self.assertEqual(OFFPEAK_MULTIPLIER, 0.80)
        self.assertEqual(POWER_FACTOR_PENALTY_THRESHOLD, 0.90)

    def test_anomaly_thresholds(self):
        self.assertIn("watch", ANOMALY_THRESHOLDS)
        self.assertIn("warning", ANOMALY_THRESHOLDS)
        self.assertIn("critical", ANOMALY_THRESHOLDS)
        self.assertEqual(ANOMALY_THRESHOLDS["watch"], 1.5)
        self.assertEqual(ANOMALY_THRESHOLDS["warning"], 2.0)
        self.assertEqual(ANOMALY_THRESHOLDS["critical"], 3.0)

    def test_facility_and_products(self):
        self.assertEqual(MACHINE_IDS, ["M-01", "M-02", "M-03", "M-04"])
        self.assertEqual(set(PRODUCT_TYPES.keys()), {"L", "M", "H"})
        self.assertEqual(set(SHIFTS.keys()), {"Shift_1", "Shift_2", "Shift_3"})
        self.assertEqual(MOTOR_EFFICIENCY, 0.85)
        self.assertEqual(DRIVE_EFFICIENCY, 0.92)


class TestValidators(unittest.TestCase):
    """Test validation and clamping utility functions."""

    def test_safe_sec_calculation_scalars(self):
        # Normal positive calculation
        self.assertAlmostEqual(safe_sec_calculation(12.0, 4.0), 3.0)
        # Zero production units handled safely
        self.assertEqual(safe_sec_calculation(12.0, 0.0), 0.0)
        # Negative production units handled safely
        self.assertEqual(safe_sec_calculation(12.0, -2.0), 0.0)
        # Negative energy handled safely
        self.assertEqual(safe_sec_calculation(-12.0, 4.0), 0.0)
        # NaN handled safely
        self.assertEqual(safe_sec_calculation(np.nan, 4.0), 0.0)

    def test_safe_sec_calculation_series_and_arrays(self):
        energy = pd.Series([10.0, 20.0, 0.0, 30.0])
        units = pd.Series([2.0, 0.0, 5.0, 10.0])
        res = safe_sec_calculation(energy, units)
        self.assertIsInstance(res, pd.Series)
        self.assertEqual(res.tolist(), [5.0, 0.0, 0.0, 3.0])

        arr_e = np.array([10.0, 20.0])
        arr_u = np.array([2.0, 0.0])
        res_arr = safe_sec_calculation(arr_e, arr_u)
        self.assertIsInstance(res_arr, np.ndarray)
        np.testing.assert_array_almost_equal(res_arr, np.array([5.0, 0.0]))

    def test_clamp_to_training_range(self):
        # Below minimum
        clamped_low = clamp_to_training_range(500.0, "rotational_speed_rpm")
        self.assertEqual(clamped_low, 1000.0)
        # Above maximum
        clamped_high = clamp_to_training_range(4000.0, "rotational_speed_rpm")
        self.assertEqual(clamped_high, 3000.0)
        # Within range
        nominal = clamp_to_training_range(1500.0, "rotational_speed_rpm")
        self.assertEqual(nominal, 1500.0)
        # Unknown feature passes through untouched
        unknown = clamp_to_training_range(999.0, "non_existent_feature")
        self.assertEqual(unknown, 999.0)

    def test_validate_prediction_input(self):
        valid_input = {
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 45.0,
            "product_type": "M",
        }
        is_v, errs = validate_prediction_input(valid_input)
        self.assertTrue(is_v)
        self.assertEqual(len(errs), 0)

        # Invalid out of bounds
        invalid_input = {
            "rotational_speed_rpm": 9000.0,
            "product_type": "INVALID_TYPE",
        }
        is_v, errs = validate_prediction_input(invalid_input)
        self.assertFalse(is_v)
        self.assertEqual(len(errs), 2)

    def test_validate_energy_data(self):
        # Valid DataFrame
        df_ok = pd.DataFrame({
            "energy_kwh": [1.2, 3.4],
            "rotational_speed_rpm": [1500, 1600],
            "torque_nm": [40.0, 45.0],
        })
        rep_ok = validate_energy_data(df_ok)
        self.assertTrue(rep_ok.is_valid)

        # Negative energy error
        df_bad = pd.DataFrame({
            "energy_kwh": [-2.0, 3.4],
            "torque_nm": [40.0, -5.0],
        })
        rep_bad = validate_energy_data(df_bad)
        self.assertFalse(rep_bad.is_valid)
        self.assertTrue(any("negative energy" in e for e in rep_bad.errors))
        self.assertTrue(any("Torque" in e for e in rep_bad.errors))


if __name__ == "__main__":
    unittest.main()
