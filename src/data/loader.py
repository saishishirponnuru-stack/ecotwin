"""
Data loading module for EcoTwin.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

def load_ai4i_dataset(path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the AI4I 2020 Predictive Maintenance Dataset.
    
    Args:
        path: Path to the dataset CSV file.
        
    Returns:
        pd.DataFrame containing the dataset.
    """
    try:
        path = Path(path)
        logger.info(f"Loading AI4I dataset from {path}")
        df = pd.read_csv(path)
        
        # Validate schema (basic validation)
        expected_cols = [
            'UDI', 'Product ID', 'Type', 'Air temperature [K]', 
            'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 
            'Tool wear [min]', 'Machine failure', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF'
        ]
        
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing expected columns in AI4I dataset: {missing_cols}")
            
        return df
    except Exception as e:
        logger.error(f"Failed to load AI4I dataset: {e}")
        raise

def load_steel_dataset(path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the Steel Industry Energy Dataset.
    
    Args:
        path: Path to the dataset CSV file.
        
    Returns:
        pd.DataFrame containing the dataset.
    """
    try:
        path = Path(path)
        logger.info(f"Loading Steel dataset from {path}")
        df = pd.read_csv(path)
        return df
    except Exception as e:
        logger.error(f"Failed to load Steel dataset: {e}")
        raise

def load_processed_dataset(path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the processed final dataset.
    
    Args:
        path: Path to the processed dataset CSV/Parquet file.
        
    Returns:
        pd.DataFrame containing the dataset.
    """
    try:
        path = Path(path)
        logger.info(f"Loading processed dataset from {path}")
        if path.suffix == '.parquet':
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)
        return df
    except Exception as e:
        logger.error(f"Failed to load processed dataset: {e}")
        raise
