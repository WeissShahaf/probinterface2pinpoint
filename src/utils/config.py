"""
Configuration management module
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """
    Manage configuration settings for probe conversion.
    
    Supports loading from:
    - YAML files
    - JSON files
    - Environment variables
    - Default values
    """
    
    DEFAULT_CONFIG = {
        'conversion': {
            'coordinate_system': {
                'units': 'micrometers',
                'origin': 'tip',
                'axes': 'RAS'
            },
            'orientation': 'vertical',
            'auto_align': True,
        },
        'validation': {
            'strict_mode': False,
            'check_bounds': True,
            'max_warnings': 10,
        },
        'output': {
            'include_metadata': True,
            'compress_geometry': False,
            'format_version': '1.0',
        },
        'processing': {
            'simplify_mesh': True,
            'max_mesh_faces': 10000,
            'electrode_matching_tolerance': 10.0,  # micrometers
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': None,
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from file if provided
        if config_path:
            self.load_from_file(config_path)
        
        # Override with environment variables
        self.load_from_env()
        
        # Look for default config file in current directory
        default_paths = ['config.yaml', 'config.yml', 'config.json', '.probe_converter.yaml']
        for path in default_paths:
            if os.path.exists(path):
                self.logger.info(f"Loading config from {path}")
                self.load_from_file(path)
                break
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load configuration from file.
        
        Args:
            filepath: Path to configuration file
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            self.logger.warning(f"Config file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r') as f:
                if filepath.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif filepath.suffix == '.json':
                    data = json.load(f)
                else:
                    self.logger.error(f"Unknown config file format: {filepath.suffix}")
                    return
            
            # Merge with existing config
            self.config = self._deep_merge(self.config, data)
            self.logger.info(f"Loaded configuration from {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config file: {str(e)}")
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            'PROBE_CONVERTER_UNITS': ['conversion', 'coordinate_system', 'units'],
            'PROBE_CONVERTER_ORIGIN': ['conversion', 'coordinate_system', 'origin'],
            'PROBE_CONVERTER_STRICT': ['validation', 'strict_mode'],
            'PROBE_CONVERTER_LOG_LEVEL': ['logging', 'level'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested(self.config, config_path, self._parse_value(value))
                self.logger.debug(f"Set {'.'.join(config_path)} from {env_var}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        self._set_nested(self.config, keys, value)
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            update: Dictionary with updates
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _set_nested(self, data: Dict, keys: list, value: Any) -> None:
        """
        Set nested dictionary value.
        
        Args:
            data: Dictionary to modify
            keys: List of keys
            value: Value to set
        """
        for key in keys[:-1]:
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            data = data[key]
        
        data[keys[-1]] = value
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse string value to appropriate type.
        
        Args:
            value: String value
            
        Returns:
            Parsed value
        """
        # Try to parse as JSON first
        try:
            return json.loads(value)
        except:
            pass
        
        # Check for boolean
        if value.lower() in ['true', 'yes', '1']:
            return True
        elif value.lower() in ['false', 'no', '0']:
            return False
        
        # Check for number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except:
            pass
        
        # Return as string
        return value
    
    def save(self, filepath: str, format: str = 'yaml') -> None:
        """
        Save current configuration to file.
        
        Args:
            filepath: Output file path
            format: Output format ('yaml' or 'json')
        """
        filepath = Path(filepath)
        
        try:
            with open(filepath, 'w') as f:
                if format == 'yaml':
                    yaml.dump(self.config, f, default_flow_style=False)
                elif format == 'json':
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"Unknown format: {format}")
            
            self.logger.info(f"Saved configuration to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
            raise
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if valid
        """
        valid = True
        
        # Check units
        valid_units = ['micrometers', 'um', 'millimeters', 'mm', 'nanometers', 'nm']
        units = self.get('conversion.coordinate_system.units')
        if units not in valid_units:
            self.logger.error(f"Invalid units: {units}")
            valid = False
        
        # Check origin
        valid_origins = ['tip', 'center', 'top']
        origin = self.get('conversion.coordinate_system.origin')
        if origin not in valid_origins:
            self.logger.error(f"Invalid origin: {origin}")
            valid = False
        
        # Check log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level = self.get('logging.level')
        if level not in valid_levels:
            self.logger.error(f"Invalid log level: {level}")
            valid = False
        
        return valid
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting."""
        self.set(key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self.config.copy()
