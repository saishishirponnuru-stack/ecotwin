"""
Data processing and feature engineering for EcoTwin.

DATA PROVENANCE & TRANSPARENCY:
The raw AI4I 2020 dataset does NOT contain physical electrical energy (kWh) meter readings.
Instead, electrical power and energy are PHYSICALLY DERIVED using first-principles
electro-mechanical engineering formulas:

1. Mechanical Power (Watts):
   P_mech = Torque (N*m) * Angular Velocity (rad/s)
          = Torque * (RPM * 2 * pi / 60)

2. Electrical Power (Watts):
   P_elec = P_mech / motor_efficiency
   (Assuming nominal IE2 industrial induction/servo motor efficiency = 0.85)

3. Cycle Time (Minutes):
   Calibrated by manufactured part variant:
   Type L (Low complexity)   = 1.5 min
   Type M (Medium complexity) = 3.0 min
   Type H (High complexity)   = 5.0 min

4. Derived Energy per Part (kWh):
   E_part = (P_elec * (cycle_time_minutes / 60)) / 1000.0

5. Specific Energy Consumption (SEC):
   SEC = E_part / 1.0 (kWh/part)

NOTE: These derived values represent analytical physics baseline values, NOT
measured factory meter telemetry.
"""

import logging
from typing import Optional, Union
import numpy as np
import pandas as pd

from src.utils.constants import TIER_1_SENSOR_MEASUREMENT, TIER_2_PHYSICALLY_DERIVED

logger = logging.getLogger(__name__)

# Nominal IE2 industrial motor efficiency (85%)
MOTOR_EFFICIENCY: float = 0.85


def compute_analytical_energy(
    torque_nm: Union[float, np.ndarray, pd.Series],
    rotational_speed_rpm: Union[float, np.ndarray, pd.Series],
    cycle_time_minutes: Union[float, np.ndarray, pd.Series],
    motor_efficiency: float = MOTOR_EFFICIENCY,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Computes theoretical electrical energy per part using first-principles physics.
    
    Formula:
        P_mech (W) = torque_nm * (rotational_speed_rpm * 2 * pi / 60)
        P_elec (W) = P_mech / motor_efficiency
        Energy (kWh) = (P_elec * (cycle_time_minutes / 60)) / 1000
        
    Args:
        torque_nm: Spindle torque in Newton-meters [N*m]
        rotational_speed_rpm: Spindle speed in revolutions per minute [RPM]
        cycle_time_minutes: Machining cycle duration in minutes [min]
        motor_efficiency: Electrical-to-mechanical conversion efficiency [0.0 - 1.0]
        
    Returns:
        Derived electrical energy in kilowatt-hours [kWh]
    """
    if motor_efficiency <= 0.0 or motor_efficiency > 1.0:
        raise ValueError(f"Motor efficiency must be in (0.0, 1.0], got {motor_efficiency}")
        
    p_mech_watts = torque_nm * (rotational_speed_rpm * 2.0 * np.pi / 60.0)
    p_elec_watts = p_mech_watts / motor_efficiency
    cycle_time_hours = cycle_time_minutes / 60.0
    energy_kwh = (p_elec_watts * cycle_time_hours) / 1000.0
    return energy_kwh


def process_manufacturing_data(df_ai4i: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the raw AI4I dataset, maps column names, and computes
    first-principles physical energy derivations.
    
    Args:
        df_ai4i: Raw DataFrame from AI4I 2020 dataset.
        
    Returns:
        Cleaned DataFrame with original sensor values (Tier 1) and
        physically derived power/energy metrics (Tier 2).
    """
    df = df_ai4i.copy()
    
    # 1. Clean and rename columns to snake_case
    column_mapping = {
        'UDI': 'udi',
        'Product ID': 'product_id',
        'Type': 'product_type',
        'Air temperature [K]': 'air_temp_k',
        'Process temperature [K]': 'process_temp_k',
        'Rotational speed [rpm]': 'rotational_speed_rpm',
        'Torque [Nm]': 'torque_nm',
        'Tool wear [min]': 'tool_wear_min',
        'Machine failure': 'machine_failure',
        'TWF': 'twf',
        'HDF': 'hdf',
        'PWF': 'pwf',
        'OSF': 'osf',
        'RNF': 'rnf',
    }
    df = df.rename(columns=column_mapping)
    
    # 2. Physics Derivation: Mechanical Power (W)
    df['mechanical_power_watts'] = df['torque_nm'] * (df['rotational_speed_rpm'] * 2.0 * np.pi / 60.0)
    # Retain 'power_watts' for backward compatibility
    df['power_watts'] = df['mechanical_power_watts']
    
    # 3. Physics Derivation: Cycle time calibrated by product type
    def get_cycle_time(ptype: str) -> float:
        if ptype == 'L':
            return 1.5
        elif ptype == 'M':
            return 3.0
        elif ptype == 'H':
            return 5.0
        return 3.0
        
    df['cycle_time_minutes'] = df['product_type'].apply(get_cycle_time)
    
    # 4. Physics Derivation: Electrical Power (W) and Energy (kWh)
    df['electrical_power_watts'] = df['mechanical_power_watts'] / MOTOR_EFFICIENCY
    cycle_time_hours = df['cycle_time_minutes'] / 60.0
    
    # Energy in kWh per part
    df['energy_kwh'] = (df['electrical_power_watts'] * cycle_time_hours) / 1000.0
    df['derived_energy_kwh'] = df['energy_kwh']
    
    # Specific Energy Consumption (SEC) in kWh/part
    df['sec_kwh_per_part'] = df['energy_kwh']
    df['derived_sec_kwh_per_part'] = df['sec_kwh_per_part']
    
    # 5. Process temperature delta (Process Temp - Air Temp) [Kelvin]
    df['temp_diff_k'] = df['process_temp_k'] - df['air_temp_k']
    
    # 6. Add sequential base timeline starting from 2024-01-01
    start_time = pd.Timestamp('2024-01-01 00:00:00')
    time_deltas = pd.to_timedelta(df['cycle_time_minutes'].cumsum(), unit='m')
    df['timestamp'] = start_time + time_deltas
    
    return df
