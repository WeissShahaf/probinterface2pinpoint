"""
Coordinate transformation module
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np


class CoordinateTransformer:
    """
    Handle coordinate system transformations between different formats.
    
    Supports:
    - Unit conversions (micrometers, millimeters, etc.)
    - Axis reordering and flipping
    - Origin translations
    - Rotation transformations
    - Coordinate system standardization
    """
    
    # Common unit conversion factors to micrometers
    UNIT_CONVERSIONS = {
        'um': 1.0,
        'micrometers': 1.0,
        'microns': 1.0,
        'mm': 1000.0,
        'millimeters': 1000.0,
        'm': 1e6,
        'meters': 1e6,
        'nm': 0.001,
        'nanometers': 0.001,
    }
    
    def __init__(self, config: Optional[Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Default output coordinate system
        self.output_system = {
            'units': 'micrometers',
            'origin': 'tip',  # 'tip', 'center', or 'top'
            'axes': 'RAS',  # Right-Anterior-Superior (neuroimaging convention)
        }
        
        # Override with config if provided
        if hasattr(config, 'get'):
            conversion_config = config.get('conversion', {})
            if 'coordinate_system' in conversion_config:
                self.output_system.update(conversion_config['coordinate_system'])
    
    def transform_electrodes(
        self,
        electrodes: List[Dict[str, Any]],
        source_units: str = 'um',
        source_origin: str = 'tip'
    ) -> List[Dict[str, Any]]:
        """
        Transform electrode coordinates to standard system.
        
        Args:
            electrodes: List of electrode dictionaries
            source_units: Source coordinate units
            source_origin: Source origin position
            
        Returns:
            Transformed electrode list
        """
        if not electrodes:
            return electrodes
        
        self.logger.info(f"Transforming {len(electrodes)} electrodes")
        
        # Convert to numpy array for efficient transformation
        coords = np.array([
            [e.get('x', 0), e.get('y', 0), e.get('z', 0)]
            for e in electrodes
        ])
        
        # Apply unit conversion
        coords = self._convert_units(coords, source_units, self.output_system['units'])
        
        # Apply origin transformation
        coords = self._transform_origin(coords, source_origin, self.output_system['origin'])
        
        # Apply axis transformation if needed
        # coords = self._transform_axes(coords, source_axes, self.output_system['axes'])
        
        # Update electrode dictionaries
        transformed_electrodes = []
        for i, electrode in enumerate(electrodes):
            transformed = electrode.copy()
            transformed['x'] = float(coords[i, 0])
            transformed['y'] = float(coords[i, 1])
            transformed['z'] = float(coords[i, 2])
            transformed_electrodes.append(transformed)
        
        return transformed_electrodes
    
    def _convert_units(
        self,
        coords: np.ndarray,
        source_units: str,
        target_units: str
    ) -> np.ndarray:
        """
        Convert coordinate units.
        
        Args:
            coords: Coordinate array
            source_units: Source units
            target_units: Target units
            
        Returns:
            Converted coordinates
        """
        if source_units == target_units:
            return coords
        
        # Get conversion factors
        source_to_um = self.UNIT_CONVERSIONS.get(source_units.lower(), 1.0)
        target_from_um = 1.0 / self.UNIT_CONVERSIONS.get(target_units.lower(), 1.0)
        
        # Apply conversion
        conversion_factor = source_to_um * target_from_um
        
        if conversion_factor != 1.0:
            self.logger.info(f"Converting units from {source_units} to {target_units} (factor: {conversion_factor})")
            coords = coords * conversion_factor
        
        return coords
    
    def _transform_origin(
        self,
        coords: np.ndarray,
        source_origin: str,
        target_origin: str
    ) -> np.ndarray:
        """
        Transform coordinate origin.
        
        Args:
            coords: Coordinate array
            source_origin: Source origin position ('tip', 'center', 'top')
            target_origin: Target origin position
            
        Returns:
            Transformed coordinates
        """
        if source_origin == target_origin:
            return coords
        
        # Calculate current bounds
        min_coords = coords.min(axis=0)
        max_coords = coords.max(axis=0)
        center = (min_coords + max_coords) / 2
        
        # Transform based on source and target
        if source_origin == 'tip' and target_origin == 'center':
            # Move origin from tip to center
            coords = coords - center
        elif source_origin == 'center' and target_origin == 'tip':
            # Move origin from center to tip (assume tip is at min y)
            coords[:, 1] = coords[:, 1] - min_coords[1]
        elif source_origin == 'top' and target_origin == 'tip':
            # Flip y-axis (assuming y is vertical)
            coords[:, 1] = max_coords[1] - coords[:, 1]
        elif source_origin == 'tip' and target_origin == 'top':
            # Flip y-axis
            coords[:, 1] = max_coords[1] - coords[:, 1]
        
        self.logger.info(f"Transformed origin from {source_origin} to {target_origin}")
        return coords
    
    def _transform_axes(
        self,
        coords: np.ndarray,
        source_axes: str,
        target_axes: str
    ) -> np.ndarray:
        """
        Transform between different axis conventions.
        
        Args:
            coords: Coordinate array
            source_axes: Source axis convention (e.g., 'XYZ', 'RAS')
            target_axes: Target axis convention
            
        Returns:
            Transformed coordinates
        """
        if source_axes == target_axes:
            return coords
        
        # Define transformation matrices for common conventions
        transformations = {
            ('XYZ', 'RAS'): np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]),
            ('RAS', 'XYZ'): np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
        }
        
        key = (source_axes, target_axes)
        if key in transformations:
            transform_matrix = transformations[key]
            coords = coords @ transform_matrix.T
            self.logger.info(f"Transformed axes from {source_axes} to {target_axes}")
        else:
            self.logger.warning(f"No transformation defined for {source_axes} to {target_axes}")
        
        return coords
    
    def apply_rotation(
        self,
        coords: np.ndarray,
        rotation_angles: Tuple[float, float, float],
        rotation_order: str = 'XYZ'
    ) -> np.ndarray:
        """
        Apply rotation transformation.
        
        Args:
            coords: Coordinate array
            rotation_angles: Rotation angles in degrees (x, y, z)
            rotation_order: Order of rotations
            
        Returns:
            Rotated coordinates
        """
        from scipy.spatial.transform import Rotation
        
        # Convert angles to radians
        angles_rad = np.radians(rotation_angles)
        
        # Create rotation object
        if rotation_order == 'XYZ':
            r = Rotation.from_euler('xyz', angles_rad)
        elif rotation_order == 'ZYX':
            r = Rotation.from_euler('zyx', angles_rad)
        else:
            r = Rotation.from_euler(rotation_order.lower(), angles_rad)
        
        # Apply rotation
        coords = r.apply(coords)
        
        self.logger.info(f"Applied rotation: {rotation_angles} degrees in {rotation_order} order")
        return coords
    
    def align_to_atlas(
        self,
        coords: np.ndarray,
        atlas_type: str = 'allen_ccf',
        bregma_offset: Optional[Tuple[float, float, float]] = None
    ) -> np.ndarray:
        """
        Align coordinates to a brain atlas coordinate system.
        
        Args:
            coords: Coordinate array
            atlas_type: Type of atlas ('allen_ccf', 'paxinos', etc.)
            bregma_offset: Offset from bregma if known
            
        Returns:
            Atlas-aligned coordinates
        """
        if atlas_type == 'allen_ccf':
            # Allen Common Coordinate Framework
            # Origin at anterior commissure
            # Units in micrometers
            # Axes: Anterior-Posterior, Superior-Inferior, Left-Right
            
            if bregma_offset:
                # Apply bregma offset
                coords = coords + np.array(bregma_offset)
            
            # CCF specific transformations
            # (implement based on specific requirements)
            
        elif atlas_type == 'paxinos':
            # Paxinos & Watson atlas
            # Different coordinate conventions
            pass
        
        self.logger.info(f"Aligned coordinates to {atlas_type} atlas")
        return coords
    
    def get_output_system(self) -> Dict[str, Any]:
        """
        Get the output coordinate system configuration.
        
        Returns:
            Output system dictionary
        """
        return self.output_system.copy()
    
    def estimate_units(self, coords: np.ndarray) -> str:
        """
        Estimate the units of coordinates based on typical ranges.
        
        Args:
            coords: Coordinate array
            
        Returns:
            Estimated unit string
        """
        # Calculate the range of coordinates
        coord_range = coords.max(axis=0) - coords.min(axis=0)
        max_range = coord_range.max()
        
        # Typical probe dimensions
        # Neuropixels: ~10mm long -> 10000 um
        # Most probes: 1-20mm -> 1000-20000 um
        
        if max_range < 50:
            # Likely in millimeters
            estimated_units = 'mm'
        elif max_range < 500:
            # Could be scaled mm or very small probe in um
            estimated_units = 'mm'
        elif max_range > 50000:
            # Likely in nanometers
            estimated_units = 'nm'
        else:
            # Likely in micrometers (most common)
            estimated_units = 'um'
        
        self.logger.info(f"Estimated coordinate units: {estimated_units} (max range: {max_range})")
        return estimated_units
    
    def standardize_coordinates(
        self,
        probe_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Standardize all coordinates in probe data.
        
        Args:
            probe_data: Complete probe data dictionary
            
        Returns:
            Probe data with standardized coordinates
        """
        # Standardize electrode coordinates
        if 'electrodes' in probe_data:
            probe_data['electrodes'] = self.transform_electrodes(
                probe_data['electrodes'],
                source_units=probe_data.get('si_units', 'um'),
                source_origin=probe_data.get('origin', 'tip')
            )
        
        # Standardize 3D model coordinates if present
        if 'model_3d' in probe_data and 'vertices' in probe_data['model_3d']:
            vertices = np.array(probe_data['model_3d']['vertices'])
            
            # Estimate units if not specified
            model_units = probe_data['model_3d'].get('units')
            if not model_units:
                model_units = self.estimate_units(vertices)
            
            # Convert units
            vertices = self._convert_units(
                vertices,
                model_units,
                self.output_system['units']
            )
            
            probe_data['model_3d']['vertices'] = vertices.tolist()
        
        # Add coordinate system metadata
        probe_data['coordinate_system'] = self.output_system
        
        return probe_data
