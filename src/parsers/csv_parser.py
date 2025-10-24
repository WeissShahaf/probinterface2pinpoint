"""
Parser for CSV electrode mapping files
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Optional
import numpy as np


class CSVParser:
    """
    Parse electrode mapping and position data from CSV files.
    
    Expected CSV columns (flexible, will auto-detect):
    - electrode_id: Unique identifier for each electrode
    - x, y, z: Spatial coordinates (usually in micrometers)
    - channel: Recording channel number
    - shank_id: Shank identifier for multi-shank probes
    - row, column: Grid position for array probes
    - Additional metadata columns as needed
    """
    
    # Common column name variations to look for
    COLUMN_MAPPINGS = {
        'electrode_id': ['electrode_id', 'electrode', 'id', 'contact_id', 'contact'],
        'x': ['x', 'x_pos', 'x_position', 'x_coord', 'x_um'],
        'y': ['y', 'y_pos', 'y_position', 'y_coord', 'y_um'],
        'z': ['z', 'z_pos', 'z_position', 'z_coord', 'z_um', 'depth'],
        'channel': ['channel', 'channel_id', 'channel_number', 'ch'],
        'shank_id': ['shank_id', 'shank', 'shank_number', 'probe'],
        'row': ['row', 'row_index', 'r'],
        'column': ['column', 'col', 'column_index', 'c'],
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, filepath: str) -> pd.DataFrame:
        """
        Parse electrode data from CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with standardized column names
        """
        self.logger.info(f"Parsing CSV file: {filepath}")
        
        try:
            # Try to read CSV with automatic delimiter detection
            df = pd.read_csv(filepath, sep=None, engine='python')
            
            # Standardize column names
            df = self._standardize_columns(df)
            
            # Validate required columns
            self._validate_dataframe(df)
            
            # Clean and convert data types
            df = self._clean_data(df)
            
            self.logger.info(f"Successfully parsed {len(df)} electrode records from CSV")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to parse CSV file: {str(e)}")
            raise
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to expected format.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with standardized column names
        """
        # Create mapping of actual columns to standard names
        column_map = {}
        
        for standard_name, variations in self.COLUMN_MAPPINGS.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower in variations:
                    column_map[col] = standard_name
                    break
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        # Log which columns were mapped
        self.logger.debug(f"Column mapping: {column_map}")
        
        return df
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame has minimum required columns.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If required columns are missing
        """
        # At minimum, we need some position data
        has_position = any(col in df.columns for col in ['x', 'y', 'z'])
        
        if not has_position:
            raise ValueError(
                "CSV must contain at least one position column (x, y, or z). "
                f"Found columns: {list(df.columns)}"
            )
        
        # If no electrode_id, create one
        if 'electrode_id' not in df.columns:
            df['electrode_id'] = range(len(df))
            self.logger.warning("No electrode_id column found, using row indices")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and convert data types.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Convert position columns to float
        for col in ['x', 'y', 'z']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Fill NaN with 0 for position columns
                if col == 'z':
                    df[col] = df[col].fillna(0)
        
        # Convert ID columns to int where possible
        for col in ['electrode_id', 'channel', 'shank_id', 'row', 'column']:
            if col in df.columns:
                # Try to convert to int, keep as is if it fails
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')
                except:
                    pass
        
        # Remove any completely empty rows
        df = df.dropna(how='all')
        
        # Sort by electrode_id if present
        if 'electrode_id' in df.columns:
            df = df.sort_values('electrode_id').reset_index(drop=True)
        
        return df
    
    def parse_with_metadata(
        self,
        filepath: str,
        metadata_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse CSV with optional metadata file.
        
        Args:
            filepath: Path to electrode CSV
            metadata_file: Path to metadata JSON/YAML (optional)
            
        Returns:
            Dictionary with electrodes DataFrame and metadata
        """
        # Parse main CSV
        df = self.parse(filepath)
        
        result = {
            'electrodes': df,
            'metadata': {}
        }
        
        # Parse metadata if provided
        if metadata_file:
            import json
            import yaml
            
            try:
                with open(metadata_file, 'r') as f:
                    if metadata_file.endswith('.json'):
                        metadata = json.load(f)
                    elif metadata_file.endswith(('.yaml', '.yml')):
                        metadata = yaml.safe_load(f)
                    else:
                        self.logger.warning(f"Unknown metadata format: {metadata_file}")
                        metadata = {}
                
                result['metadata'] = metadata
                
            except Exception as e:
                self.logger.error(f"Failed to parse metadata file: {str(e)}")
        
        return result
    
    def export_to_dict_list(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Convert DataFrame to list of dictionaries for merging.
        
        Args:
            df: Electrode DataFrame
            
        Returns:
            List of electrode dictionaries
        """
        # Replace NaN with None for cleaner JSON serialization
        df_clean = df.where(pd.notnull(df), None)
        
        # Convert to dict records
        return df_clean.to_dict('records')
    
    def infer_probe_geometry(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Infer probe geometry from electrode positions.
        
        Args:
            df: DataFrame with electrode positions
            
        Returns:
            Dictionary with inferred geometry parameters
        """
        geometry = {}
        
        # Calculate probe dimensions
        if 'x' in df.columns:
            geometry['width'] = float(df['x'].max() - df['x'].min())
            geometry['x_range'] = [float(df['x'].min()), float(df['x'].max())]
        
        if 'y' in df.columns:
            geometry['height'] = float(df['y'].max() - df['y'].min())
            geometry['y_range'] = [float(df['y'].min()), float(df['y'].max())]
        
        if 'z' in df.columns and df['z'].nunique() > 1:
            geometry['depth'] = float(df['z'].max() - df['z'].min())
            geometry['z_range'] = [float(df['z'].min()), float(df['z'].max())]
            geometry['is_3d'] = True
        else:
            geometry['is_3d'] = False
        
        # Detect array structure
        if 'row' in df.columns and 'column' in df.columns:
            geometry['array_structure'] = {
                'rows': int(df['row'].nunique()),
                'columns': int(df['column'].nunique()),
                'total_electrodes': len(df)
            }
        
        # Detect multi-shank structure
        if 'shank_id' in df.columns:
            shank_ids = df['shank_id'].unique()
            geometry['shanks'] = []
            
            for shank_id in shank_ids:
                shank_df = df[df['shank_id'] == shank_id]
                shank_info = {
                    'id': int(shank_id) if pd.api.types.is_numeric_dtype(df['shank_id']) else shank_id,
                    'electrode_count': len(shank_df)
                }
                
                if 'x' in df.columns:
                    shank_info['x_range'] = [float(shank_df['x'].min()), float(shank_df['x'].max())]
                if 'y' in df.columns:
                    shank_info['y_range'] = [float(shank_df['y'].min()), float(shank_df['y'].max())]
                
                geometry['shanks'].append(shank_info)
        
        # Estimate electrode pitch (spacing)
        if 'y' in df.columns:
            y_sorted = df['y'].sort_values().unique()
            if len(y_sorted) > 1:
                diffs = np.diff(y_sorted)
                geometry['electrode_pitch'] = float(np.median(diffs))
        
        return geometry
