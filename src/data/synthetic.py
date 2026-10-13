"""
Synthetic data augmentation for EcoTwin.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def augment_with_factory_context(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Augments the processed dataframe with synthetic factory context variables.
    
    Args:
        df: The processed manufacturing DataFrame containing timestamps.
        seed: Random seed for reproducibility.
        
    Returns:
        DataFrame augmented with machine_id, shift, maintenance info, etc.
    """
    np.random.seed(seed)
    df_aug = df.copy()
    n = len(df_aug)
    
    # a) machine_id: assign each record to one of 4 machines
    df_aug['machine_id'] = np.random.choice(['M-01', 'M-02', 'M-03', 'M-04'], size=n)
    
    # Apply synthetic energy penalties/drifts based on machine_id
    # M-02 has systematic penalty (degradation) -> +10% energy
    m02_mask = df_aug['machine_id'] == 'M-02'
    df_aug.loc[m02_mask, 'energy_kwh'] *= 1.10
    
    # M-04 has increasing energy over time (drift) -> up to +20% over the dataset
    m04_mask = df_aug['machine_id'] == 'M-04'
    drift_factor = np.linspace(1.0, 1.20, n)
    # We apply the drift factor proportionally to where the record is in the timeline
    df_aug.loc[m04_mask, 'energy_kwh'] *= drift_factor[m04_mask]
    
    # Update sec_kwh_per_part as well
    df_aug['sec_kwh_per_part'] = df_aug['energy_kwh']
    
    # b) shift: Day (06-14), Evening (14-22), Night (22-06)
    hours = df_aug['timestamp'].dt.hour
    
    def determine_shift(h):
        if 6 <= h < 14:
            return 'Day'
        elif 14 <= h < 22:
            return 'Evening'
        else:
            return 'Night'
            
    df_aug['shift'] = hours.apply(determine_shift)
    
    # Add slight energy variation based on shift (e.g., Night shift slightly less efficient)
    shift_multipliers = {'Day': 1.0, 'Evening': 1.02, 'Night': 1.05}
    df_aug['energy_kwh'] *= df_aug['shift'].map(shift_multipliers)
    df_aug['sec_kwh_per_part'] = df_aug['energy_kwh']
    
    # c) maintenance_status: OK/Due/Overdue based on tool_wear_min thresholds
    def get_maint_status(wear):
        if wear > 200:
            return 'Overdue'
        elif wear > 150:
            return 'Due'
        return 'OK'
        
    df_aug['maintenance_status'] = df_aug['tool_wear_min'].apply(get_maint_status)
    
    # d) maintenance_days_since: synthetic but correlated with tool wear
    # Assume 1 min of tool wear roughly equates to 0.5 days since maintenance
    noise = np.random.normal(0, 2, n)
    df_aug['maintenance_days_since'] = np.maximum(0, (df_aug['tool_wear_min'] * 0.5) + noise).round(1)
    
    # e) electricity_tariff: ₹/kWh based on shift (peak/offpeak)
    # Peak (Evening) = 8 Rs, Normal (Day) = 6 Rs, Offpeak (Night) = 5 Rs
    tariff_map = {'Day': 6.0, 'Evening': 8.0, 'Night': 5.0}
    df_aug['electricity_tariff'] = df_aug['shift'].map(tariff_map)
    
    # f) idle_time_seconds: synthetic idle time between operations
    # Exponential distribution for idle times
    df_aug['idle_time_seconds'] = np.random.exponential(scale=30, size=n).round(1)
    
    # g) ambient_temperature: seasonal pattern (Indian climate)
    # Roughly 15C to 45C over the year
    day_of_year = df_aug['timestamp'].dt.dayofyear
    # Sine wave peaking around day 150 (end of May)
    yearly_temp_variation = 30 + 10 * np.sin(2 * np.pi * (day_of_year - 60) / 365)
    daily_temp_variation = 5 * np.sin(2 * np.pi * (hours - 8) / 24)
    df_aug['ambient_temperature'] = (yearly_temp_variation + daily_temp_variation + np.random.normal(0, 1, n)).round(1)
    
    # h) production_batch_id: batch grouping (every 50 parts is a batch)
    df_aug['production_batch_id'] = [f"B-{(i // 50):04d}" for i in range(n)]
    
    return df_aug
