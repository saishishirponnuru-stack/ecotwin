"""
Data processing and feature engineering for EcoTwin.
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MOTOR_EFFICIENCY = 0.85

def process_manufacturing_data(df_ai4i: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the AI4I dataset and engineers energy features.
    
    Args:
        df_ai4i: The raw AI4I DataFrame.
        
    Returns:
        A cleaned and feature-engineered DataFrame ready for modeling.
    """
    df = df_ai4i.copy()
    
    # Clean and rename columns
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
        'RNF': 'rnf'
    }
    df = df.rename(columns=column_mapping)
    
    # Compute mechanical power: Power_W = Torque * RPM * 2*pi / 60
    # Add small epsilon to avoid zero power if needed, though 0 is physically fine.
    df['power_watts'] = df['torque_nm'] * (df['rotational_speed_rpm'] * 2 * np.pi / 60)
    
    # Compute cycle time based on product type
    # L = 1.5 mins, M = 3 mins, H = 5 mins
    def get_cycle_time(ptype):
        if ptype == 'L': return 1.5
        elif ptype == 'M': return 3.0
        elif ptype == 'H': return 5.0
        return 3.0
        
    df['cycle_time_minutes'] = df['product_type'].apply(get_cycle_time)
    
    # Energy per part (kWh)
    # Electrical Power (W) = Mechanical Power (W) / motor_efficiency
    # Energy (kWh) = Electrical Power * cycle_time_hours / 1000
    electrical_power_watts = df['power_watts'] / MOTOR_EFFICIENCY
    cycle_time_hours = df['cycle_time_minutes'] / 60.0
    
    df['energy_kwh'] = (electrical_power_watts * cycle_time_hours) / 1000.0
    
    # Compute SEC (specific energy consumption) in kWh per part
    # Since each row is 1 part, sec = energy_kwh / 1
    df['sec_kwh_per_part'] = df['energy_kwh']
    
    # Add synthetic time-based features (base timestamp setup)
    # Assume 1 part produced sequentially, starting from 2024-01-01
    start_time = pd.Timestamp('2024-01-01 00:00:00')
    time_deltas = pd.to_timedelta(df['cycle_time_minutes'].cumsum(), unit='m')
    df['timestamp'] = start_time + time_deltas
    
    return df
