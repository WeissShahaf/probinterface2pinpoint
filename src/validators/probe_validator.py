"""
Probe data validation module
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Container for validation results."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)


class ProbeValidator:
    """
    Validate probe data for completeness and correctness.
    
    Validates:
    - Required fields and data types
    - Coordinate ranges and units
    - Electrode spacing and arrangement
    - 3D model compatibility
    - Format-specific requirements
    """
    
    def __init__(self, config: Optional[Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Validation settings
        self.strict_mode = False
        self.check_bounds = True
        
        if hasattr(config, 'get'):
            validation_config = config.get('validation', {})
            self.strict_mode = validation_config.get('strict_mode', False)
            self.check_bounds = validation_config.get('check_bounds', True)
    
    def validate(self, probe_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate probe data structure and content.
        
        Args:
            probe_data: Probe data dictionary
            
        Returns:
            ValidationResult object
        """
        result = ValidationResult()
        
        # Check required fields
        self._validate_required_fields(probe_data, result)
        
        # Validate electrodes
        if 'electrodes' in probe_data:
            self._validate_electrodes(probe_data['electrodes'], result)
        
        # Validate 3D model if present
        if 'model_3d' in probe_data:
            self._validate_3d_model(probe_data['model_3d'], result)
        
        # Validate coordinate system
        if 'coordinate_system' in probe_data:
            self._validate_coordinate_system(probe_data['coordinate_system'], result)
        
        # Check data consistency
        self._validate_consistency(probe_data, result)
        
        # Determine overall validity
        result.is_valid = len(result.errors) == 0
        
        # Log results
        if result.is_valid:
            self.logger.info("Probe data validation passed")
        else:
            self.logger.error(f"Validation failed with {len(result.errors)} errors")
            for error in result.errors:
                self.logger.error(f"  - {error}")
        
        if result.warnings:
            for warning in result.warnings:
                self.logger.warning(f"  - {warning}")
        
        return result
    
    def validate_pinpoint(self, path: Union[str, Path, Dict[str, Any]]) -> ValidationResult:
        """
        Validate Pinpoint format (folder or legacy JSON file).

        Supports:
        - New multi-file format: folder with metadata.json, site_map.csv, model.obj
        - Legacy format: single JSON file (for backwards compatibility)

        Args:
            path: Path to Pinpoint folder, JSON file, or dict (legacy)

        Returns:
            ValidationResult object
        """
        result = ValidationResult()

        # Handle dict input (legacy format)
        if isinstance(path, dict):
            return self._validate_legacy_pinpoint(path)

        # Convert to Path object
        path_obj = Path(path)

        # Check if folder or file
        if path_obj.is_dir():
            # Validate multi-file folder format
            return self._validate_pinpoint_folder(path_obj)
        elif path_obj.is_file():
            # Validate legacy JSON format
            try:
                with open(path_obj, 'r') as f:
                    data = json.load(f)
                return self._validate_legacy_pinpoint(data)
            except Exception as e:
                result.errors.append(f"Failed to load JSON file: {str(e)}")
                result.is_valid = False
                return result
        else:
            result.errors.append(f"Path does not exist: {path}")
            result.is_valid = False
            return result

    def _validate_pinpoint_folder(self, folder_path: Path) -> ValidationResult:
        """
        Validate Pinpoint multi-file folder format.

        Args:
            folder_path: Path to probe folder

        Returns:
            ValidationResult object
        """
        result = ValidationResult()

        # Check required files exist
        metadata_path = folder_path / 'metadata.json'
        site_map_path = folder_path / 'site_map.csv'
        model_path = folder_path / 'model.obj'

        if not metadata_path.exists():
            result.errors.append("Missing required file: metadata.json")
        if not site_map_path.exists():
            result.errors.append("Missing required file: site_map.csv")

        # Model is optional
        if model_path.exists():
            result.info['has_model'] = True
        else:
            result.info['has_model'] = False

        # Validate metadata.json
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                self._validate_metadata(metadata, result)
            except Exception as e:
                result.errors.append(f"Failed to load metadata.json: {str(e)}")

        # Validate site_map.csv
        if site_map_path.exists():
            try:
                with open(site_map_path, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    self._validate_site_map(rows, result)
            except Exception as e:
                result.errors.append(f"Failed to load site_map.csv: {str(e)}")

        # Validate model.obj (if exists)
        if model_path.exists():
            try:
                with open(model_path, 'r') as f:
                    obj_content = f.read()
                self._validate_obj_model(obj_content, result)
            except Exception as e:
                result.errors.append(f"Failed to load model.obj: {str(e)}")

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_metadata(self, metadata: Dict[str, Any], result: ValidationResult) -> None:
        """Validate metadata.json schema."""
        required_fields = ['name', 'type', 'producer', 'sites', 'shanks']

        for field in required_fields:
            if field not in metadata:
                result.errors.append(f"metadata.json missing required field: {field}")

        # Validate types
        if 'sites' in metadata and not isinstance(metadata['sites'], int):
            result.errors.append(f"metadata.json 'sites' must be integer, got {type(metadata['sites'])}")

        if 'shanks' in metadata and not isinstance(metadata['shanks'], int):
            result.errors.append(f"metadata.json 'shanks' must be integer, got {type(metadata['shanks'])}")

        result.info['metadata'] = metadata

    def _validate_site_map(self, rows: List[Dict[str, str]], result: ValidationResult) -> None:
        """Validate site_map.csv format."""
        if not rows:
            result.errors.append("site_map.csv is empty")
            return

        # Check required columns
        required_columns = {'index', 'x', 'y', 'z', 'w', 'h', 'd', 'default'}
        first_row = rows[0]
        missing_cols = required_columns - set(first_row.keys())

        if missing_cols:
            result.errors.append(f"site_map.csv missing columns: {missing_cols}")

        # Validate numeric values
        for i, row in enumerate(rows):
            try:
                # Check numeric fields
                for field in ['x', 'y', 'z', 'w', 'h', 'd']:
                    if field in row:
                        float(row[field])
                if 'index' in row:
                    int(row['index'])
            except ValueError:
                result.errors.append(f"site_map.csv row {i} has invalid numeric value")

        result.info['site_count'] = len(rows)

    def _validate_obj_model(self, obj_content: str, result: ValidationResult) -> None:
        """Validate OBJ model format (basic check)."""
        lines = obj_content.split('\n')

        vertex_count = 0
        face_count = 0

        for line in lines:
            line = line.strip()
            if line.startswith('v '):
                vertex_count += 1
            elif line.startswith('f '):
                face_count += 1

        if vertex_count == 0:
            result.errors.append("model.obj has no vertices")
        if face_count == 0:
            result.errors.append("model.obj has no faces")

        result.info['model_vertices'] = vertex_count
        result.info['model_faces'] = face_count

    def _validate_legacy_pinpoint(self, pinpoint_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate legacy Pinpoint JSON format (backwards compatibility).

        Args:
            pinpoint_data: Pinpoint-formatted data dict

        Returns:
            ValidationResult object
        """
        result = ValidationResult()

        # Check Pinpoint-specific requirements
        required_fields = ['format_version', 'probe', 'electrodes']

        for field in required_fields:
            if field not in pinpoint_data:
                result.errors.append(f"Missing required Pinpoint field: {field}")

        # Validate format version
        if 'format_version' in pinpoint_data:
            version = pinpoint_data['format_version']
            if not isinstance(version, str):
                result.errors.append(f"format_version must be a string, got {type(version)}")

        # Validate probe info
        if 'probe' in pinpoint_data:
            probe_info = pinpoint_data['probe']
            if not isinstance(probe_info, dict):
                result.errors.append("probe must be a dictionary")
            elif 'name' not in probe_info:
                result.warnings.append("probe missing 'name' field")

        # Validate electrodes
        if 'electrodes' in pinpoint_data:
            electrodes = pinpoint_data['electrodes']
            if not isinstance(electrodes, list):
                result.errors.append("electrodes must be a list")
            else:
                for i, electrode in enumerate(electrodes):
                    if 'position' not in electrode:
                        result.errors.append(f"Electrode {i} missing position")
                    elif not isinstance(electrode['position'], dict):
                        result.errors.append(f"Electrode {i} position must be a dictionary")
                    else:
                        for coord in ['x', 'y', 'z']:
                            if coord not in electrode['position']:
                                result.errors.append(f"Electrode {i} missing {coord} coordinate")

        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_required_fields(
        self,
        probe_data: Dict[str, Any],
        result: ValidationResult
    ) -> None:
        """Check for required fields in probe data."""
        if self.strict_mode:
            required = ['name', 'electrodes', 'coordinate_system']
        else:
            required = ['electrodes']
        
        for field in required:
            if field not in probe_data:
                result.errors.append(f"Missing required field: {field}")
    
    def _validate_electrodes(
        self,
        electrodes: List[Dict[str, Any]],
        result: ValidationResult
    ) -> None:
        """Validate electrode data."""
        if not isinstance(electrodes, list):
            result.errors.append("Electrodes must be a list")
            return
        
        if len(electrodes) == 0:
            result.errors.append("No electrodes found")
            return
        
        # Collect statistics
        x_coords = []
        y_coords = []
        z_coords = []
        
        for i, electrode in enumerate(electrodes):
            # Check required fields
            if 'x' not in electrode or 'y' not in electrode:
                result.errors.append(f"Electrode {i} missing position data")
                continue
            
            # Check data types
            try:
                x = float(electrode['x'])
                y = float(electrode['y'])
                z = float(electrode.get('z', 0))
                
                x_coords.append(x)
                y_coords.append(y)
                z_coords.append(z)
                
            except (TypeError, ValueError):
                result.errors.append(f"Electrode {i} has invalid coordinate values")
        
        if x_coords:
            # Check coordinate ranges
            if self.check_bounds:
                self._check_coordinate_bounds(x_coords, y_coords, z_coords, result)
            
            # Check spacing
            self._check_electrode_spacing(x_coords, y_coords, z_coords, result)
            
            # Add info
            result.info['electrode_count'] = len(electrodes)
            result.info['coordinate_ranges'] = {
                'x': [min(x_coords), max(x_coords)],
                'y': [min(y_coords), max(y_coords)],
                'z': [min(z_coords), max(z_coords)] if any(z != 0 for z in z_coords) else [0, 0],
            }
    
    def _validate_3d_model(
        self,
        model_data: Dict[str, Any],
        result: ValidationResult
    ) -> None:
        """Validate 3D model data."""
        if 'vertices' in model_data:
            vertices = model_data['vertices']
            if not isinstance(vertices, list):
                result.errors.append("3D model vertices must be a list")
            elif len(vertices) == 0:
                result.errors.append("3D model has no vertices")
            else:
                # Check vertex format
                if not all(isinstance(v, list) and len(v) == 3 for v in vertices[:10]):
                    result.errors.append("3D model vertices must be [x, y, z] lists")
        
        if 'faces' in model_data:
            faces = model_data['faces']
            if not isinstance(faces, list):
                result.errors.append("3D model faces must be a list")
            elif len(faces) > 0:
                # Check face format
                if not all(isinstance(f, list) and len(f) >= 3 for f in faces[:10]):
                    result.errors.append("3D model faces must be lists of vertex indices")
    
    def _validate_coordinate_system(
        self,
        coord_system: Dict[str, Any],
        result: ValidationResult
    ) -> None:
        """Validate coordinate system specification."""
        valid_units = ['micrometers', 'um', 'millimeters', 'mm', 'nanometers', 'nm']
        valid_origins = ['tip', 'center', 'top']
        
        if 'units' in coord_system:
            if coord_system['units'] not in valid_units:
                result.warnings.append(f"Unknown coordinate units: {coord_system['units']}")
        
        if 'origin' in coord_system:
            if coord_system['origin'] not in valid_origins:
                result.warnings.append(f"Unknown origin type: {coord_system['origin']}")
    
    def _validate_consistency(
        self,
        probe_data: Dict[str, Any],
        result: ValidationResult
    ) -> None:
        """Check consistency between different data components."""
        # Check electrode-model alignment
        if 'electrodes' in probe_data and 'model_3d' in probe_data:
            electrodes = probe_data['electrodes']
            model = probe_data['model_3d']
            
            if 'bounds' in model:
                # Check if electrodes are within model bounds
                model_min = model['bounds']['min']
                model_max = model['bounds']['max']
                
                outside_count = 0
                for electrode in electrodes:
                    x, y, z = electrode.get('x', 0), electrode.get('y', 0), electrode.get('z', 0)
                    
                    if (x < model_min[0] - 100 or x > model_max[0] + 100 or
                        y < model_min[1] - 100 or y > model_max[1] + 100 or
                        z < model_min[2] - 100 or z > model_max[2] + 100):
                        outside_count += 1
                
                if outside_count > len(electrodes) * 0.1:  # More than 10% outside
                    result.warnings.append(
                        f"{outside_count} electrodes are outside 3D model bounds "
                        "(may need alignment)"
                    )
        
        # Check shank consistency
        if 'shanks' in probe_data and 'electrodes' in probe_data:
            shank_ids = set()
            for electrode in probe_data['electrodes']:
                if 'shank_id' in electrode:
                    shank_ids.add(electrode['shank_id'])
            
            declared_shanks = {s['id'] for s in probe_data['shanks']}
            
            if shank_ids != declared_shanks:
                result.warnings.append(
                    f"Mismatch between electrode shank IDs {shank_ids} "
                    f"and declared shanks {declared_shanks}"
                )
    
    def _check_coordinate_bounds(
        self,
        x_coords: List[float],
        y_coords: List[float],
        z_coords: List[float],
        result: ValidationResult
    ) -> None:
        """Check if coordinates are within reasonable bounds."""
        # Typical probe dimensions in micrometers
        MAX_DIMENSION = 50000  # 50mm
        MIN_SPACING = 0.01  # 10nm (below this is suspicious)
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        z_range = max(z_coords) - min(z_coords)
        
        if x_range > MAX_DIMENSION:
            result.warnings.append(f"X-range ({x_range:.1f}) exceeds typical probe size")
        if y_range > MAX_DIMENSION:
            result.warnings.append(f"Y-range ({y_range:.1f}) exceeds typical probe size")
        if z_range > MAX_DIMENSION:
            result.warnings.append(f"Z-range ({z_range:.1f}) exceeds typical probe size")
        
        # Check for suspiciously small values
        if 0 < x_range < MIN_SPACING:
            result.warnings.append(f"X-range ({x_range:.6f}) suspiciously small")
        if 0 < y_range < MIN_SPACING:
            result.warnings.append(f"Y-range ({y_range:.6f}) suspiciously small")
    
    def _check_electrode_spacing(
        self,
        x_coords: List[float],
        y_coords: List[float],
        z_coords: List[float],
        result: ValidationResult
    ) -> None:
        """Check electrode spacing for regularity."""
        if len(x_coords) < 2:
            return
        
        # Calculate pairwise distances
        points = np.array(list(zip(x_coords, y_coords, z_coords)))
        
        # Find nearest neighbor distances
        min_distances = []
        for i, point in enumerate(points):
            distances = np.linalg.norm(points - point, axis=1)
            distances[i] = np.inf  # Exclude self
            min_distances.append(distances.min())
        
        min_spacing = min(min_distances)
        max_spacing = max(min_distances)
        
        # Check for too small spacing
        if min_spacing < 1.0:  # Less than 1 micrometer
            result.warnings.append(
                f"Minimum electrode spacing ({min_spacing:.3f}) "
                "is unusually small"
            )
        
        # Check for irregular spacing
        spacing_std = np.std(min_distances)
        spacing_mean = np.mean(min_distances)
        
        if spacing_std > spacing_mean * 0.5:  # High variance
            result.info['spacing_irregular'] = True
            result.info['spacing_stats'] = {
                'min': float(min_spacing),
                'max': float(max_spacing),
                'mean': float(spacing_mean),
                'std': float(spacing_std),
            }
