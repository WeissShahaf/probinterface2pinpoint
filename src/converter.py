"""
Main converter module for transforming probe data from SpikeInterface to Pinpoint format
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import numpy as np
import pandas as pd

from parsers import SpikeInterfaceParser, CSVParser, STLParser
from formatters import PinpointFormatter
from transformers import CoordinateTransformer, GeometryTransformer
from validators import ProbeValidator
from utils.logger import setup_logger
from utils.config import Config


class ProbeConverter:
    """
    Main converter class for transforming probe data between formats.
    
    This class orchestrates the conversion process:
    1. Parse input data (SpikeInterface JSON, CSV mapping, STL models)
    2. Transform coordinates and geometry
    3. Validate data integrity
    4. Format output for Pinpoint
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the probe converter.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.logger = setup_logger(__name__)
        self.config = Config(config_path)
        
        # Initialize parsers
        self.si_parser = SpikeInterfaceParser()
        self.csv_parser = CSVParser()
        self.stl_parser = STLParser()
        
        # Initialize transformers
        self.coord_transformer = CoordinateTransformer(self.config)
        self.geom_transformer = GeometryTransformer()
        
        # Initialize formatter and validator
        self.formatter = PinpointFormatter(self.config)
        self.validator = ProbeValidator(self.config)
        
        self.logger.info("ProbeConverter initialized successfully")
    
    def convert_probe(
        self,
        spikeinterface_file: str,
        electrode_csv: Optional[str] = None,
        stl_file: Optional[str] = None,
        output_file: str = "output.json",
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Convert a single probe from SpikeInterface format to Pinpoint format.
        
        Args:
            spikeinterface_file: Path to SpikeInterface JSON file
            electrode_csv: Path to CSV file with electrode mappings (optional)
            stl_file: Path to STL 3D model file (optional)
            output_file: Path for output Pinpoint JSON file
            validate: Whether to validate the output
            
        Returns:
            Dictionary containing the Pinpoint-formatted probe data
        """
        self.logger.info(f"Starting conversion for {spikeinterface_file}")
        
        try:
            # Step 1: Parse input data
            probe_data = self._parse_inputs(
                spikeinterface_file, 
                electrode_csv, 
                stl_file
            )
            
            # Step 2: Transform coordinates
            transformed_data = self._transform_data(probe_data)
            
            # Step 3: Validate if requested
            if validate:
                validation_result = self.validator.validate(transformed_data)
                if not validation_result.is_valid:
                    self.logger.warning(f"Validation warnings: {validation_result.warnings}")
                    if validation_result.errors:
                        raise ValueError(f"Validation errors: {validation_result.errors}")
            
            # Step 4: Format for Pinpoint
            pinpoint_data = self.formatter.format(transformed_data)
            
            # Step 5: Save output
            self._save_output(pinpoint_data, output_file)
            
            self.logger.info(f"Successfully converted probe to {output_file}")
            return pinpoint_data
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {str(e)}")
            raise
    
    def batch_convert(
        self,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.json"
    ) -> List[str]:
        """
        Batch convert multiple probes.
        
        Args:
            input_dir: Directory containing input files
            output_dir: Directory for output files
            pattern: File pattern to match (default: *.json)
            
        Returns:
            List of successfully converted file paths
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        converted_files = []
        
        for si_file in input_path.glob(f"spikeinterface/{pattern}"):
            try:
                # Look for corresponding CSV and STL files
                base_name = si_file.stem
                csv_file = input_path / "csv" / f"{base_name}.csv"
                stl_file = input_path / "stl" / f"{base_name}.stl"
                
                # Check if files exist
                csv_path = str(csv_file) if csv_file.exists() else None
                stl_path = str(stl_file) if stl_file.exists() else None

                # Convert (output_path is now directory, not file)
                self.convert_probe(
                    str(si_file),
                    csv_path,
                    stl_path,
                    str(output_path)
                )
                converted_files.append(str(output_path / base_name))
                
            except Exception as e:
                self.logger.error(f"Failed to convert {si_file}: {str(e)}")
                continue
        
        self.logger.info(f"Batch conversion complete. Converted {len(converted_files)} files.")
        return converted_files
    
    def _parse_inputs(
        self,
        spikeinterface_file: str,
        electrode_csv: Optional[str] = None,
        stl_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse all input files and combine data.
        
        Returns:
            Combined probe data dictionary
        """
        # Parse SpikeInterface data
        probe_data = self.si_parser.parse(spikeinterface_file)
        
        # Add CSV electrode data if provided
        if electrode_csv:
            electrode_data = self.csv_parser.parse(electrode_csv)
            probe_data = self._merge_electrode_data(probe_data, electrode_data)
        
        # Add 3D model data if provided
        if stl_file:
            model_data = self.stl_parser.parse(stl_file)
            probe_data['model_3d'] = model_data
        
        return probe_data
    
    def _merge_electrode_data(
        self,
        probe_data: Dict[str, Any],
        electrode_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Merge electrode CSV data with probe data.
        
        Args:
            probe_data: Parsed probe data
            electrode_data: Parsed electrode DataFrame
            
        Returns:
            Merged probe data
        """
        # Convert electrode DataFrame to dict for merging
        electrodes_dict = electrode_data.to_dict('records')
        
        # Match electrodes by ID or index
        if 'electrodes' in probe_data:
            for i, electrode in enumerate(probe_data['electrodes']):
                # Find matching electrode in CSV data
                electrode_id = electrode.get('id', i)
                csv_match = next(
                    (e for e in electrodes_dict if e.get('electrode_id') == electrode_id),
                    None
                )
                
                if csv_match:
                    # Update electrode with CSV data
                    electrode.update(csv_match)
        else:
            # If no electrodes in probe data, use CSV data directly
            probe_data['electrodes'] = electrodes_dict
        
        return probe_data
    
    def _transform_data(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply coordinate and geometry transformations.
        
        Args:
            probe_data: Input probe data
            
        Returns:
            Transformed probe data
        """
        # Transform electrode coordinates
        if 'electrodes' in probe_data:
            transformed_coords = self.coord_transformer.transform_electrodes(
                probe_data['electrodes']
            )
            probe_data['electrodes'] = transformed_coords
        
        # Transform geometry if 3D model is present
        if 'model_3d' in probe_data:
            transformed_model = self.geom_transformer.transform_model(
                probe_data['model_3d'],
                probe_data.get('electrodes', [])
            )
            probe_data['model_3d'] = transformed_model
        
        # Add coordinate system metadata
        probe_data['coordinate_system'] = self.coord_transformer.get_output_system()
        
        return probe_data
    
    def _save_output(self, data: Dict[str, Any], output_path: str) -> None:
        """
        Save formatted data to Pinpoint multi-file format.

        Creates folder structure:
        - <output_path>/<probe_name>/metadata.json
        - <output_path>/<probe_name>/site_map.csv
        - <output_path>/<probe_name>/model.obj (if 3D model exists)

        Args:
            data: Formatted probe data (multi-file dict from PinpointFormatter)
            output_path: Path to output directory
        """
        try:
            # Create probe folder
            probe_name = data['probe_name']
            folder_path = Path(output_path) / probe_name
            folder_path.mkdir(parents=True, exist_ok=True)

            # Write metadata.json
            metadata_path = folder_path / 'metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(data['metadata'], f, indent=2)
            self.logger.info(f"  + Wrote metadata.json")

            # Write site_map.csv
            site_map_path = folder_path / 'site_map.csv'
            if data['site_map']:
                with open(site_map_path, 'w', newline='') as f:
                    fieldnames = ['index', 'x', 'y', 'z', 'w', 'h', 'd',
                                 'default', 'layer1', 'layer2']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data['site_map'])
                self.logger.info(f"  + Wrote site_map.csv ({len(data['site_map'])} sites)")
            else:
                self.logger.warning("  ! No site map data to write")

            # Write model.obj (if exists)
            if data.get('model'):
                model_path = folder_path / 'model.obj'
                with open(model_path, 'w', encoding='utf-8') as f:
                    f.write(data['model'])
                self.logger.info(f"  + Wrote model.obj")
            else:
                self.logger.info(f"  - No 3D model data (skipping model.obj)")

            self.logger.info(f"Saved Pinpoint probe to {folder_path}")

        except Exception as e:
            self.logger.error(f"Failed to save output: {str(e)}")
            # Cleanup partial folder on failure
            if 'folder_path' in locals() and folder_path.exists():
                import shutil
                try:
                    shutil.rmtree(folder_path)
                    self.logger.info(f"Cleaned up partial output folder: {folder_path}")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to cleanup partial folder: {cleanup_error}")
            raise
    
    def validate_output(self, output_path: str) -> bool:
        """
        Validate a converted Pinpoint folder or file.

        Args:
            output_path: Path to Pinpoint folder (or legacy JSON file)

        Returns:
            True if valid, False otherwise
        """
        try:
            result = self.validator.validate_pinpoint(output_path)

            if result.is_valid:
                self.logger.info(f"{output_path} is valid Pinpoint format")
            else:
                self.logger.error(f"{output_path} validation failed: {result.errors}")

            return result.is_valid

        except Exception as e:
            self.logger.error(f"Failed to validate {output_path}: {str(e)}")
            return False
