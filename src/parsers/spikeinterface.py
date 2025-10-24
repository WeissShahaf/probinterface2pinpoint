"""
Parser for SpikeInterface probe format
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np


class SpikeInterfaceParser:
    """
    Parse probe data from SpikeInterface/probeinterface JSON format.
    
    SpikeInterface format typically includes:
    - Probe metadata (name, manufacturer, type)
    - Electrode positions (x, y coordinates in micrometers)
    - Contact shapes and sizes
    - Shank information for multi-shank probes
    - Channel mapping
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, filepath: str) -> Dict[str, Any]:
        """
        Parse a SpikeInterface probe JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Dictionary containing parsed probe data
        """
        self.logger.info(f"Parsing SpikeInterface file: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                raw_data = json.load(f)
            
            # Handle different possible formats
            if isinstance(raw_data, list):
                # Multiple probes in file
                probe_data = self._parse_probe_list(raw_data, filepath)
            elif 'probes' in raw_data:
                # Probe group format
                probe_data = self._parse_probe_group(raw_data, filepath)
            else:
                # Single probe format
                probe_data = self._parse_single_probe(raw_data, filepath)
            
            # Add source metadata
            probe_data['source_format'] = 'spikeinterface'
            probe_data['source_file'] = filepath
            
            self.logger.info(f"Successfully parsed {len(probe_data.get('electrodes', []))} electrodes")
            return probe_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse SpikeInterface file: {str(e)}")
            raise
    
    def _parse_single_probe(self, data: Dict[str, Any], filepath: str = None) -> Dict[str, Any]:
        """
        Parse a single probe definition.

        Args:
            data: Raw probe data
            filepath: Path to source file (for filename fallback)

        Returns:
            Standardized probe data
        """
        # Extract name from annotations if available
        annotations = data.get('annotations', {})
        name = (
            data.get('name') or
            annotations.get('name') or
            annotations.get('model_name') or
            'Unknown Probe'
        )

        # If name is still generic and we have a filepath, use filename
        if name in ('Unknown Probe', 'Probe Group') and filepath:
            from pathlib import Path
            name = Path(filepath).stem  # Extract filename without extension
            self.logger.info(f"Using filename as probe name: {name}")

        manufacturer = (
            data.get('manufacturer') or
            annotations.get('manufacturer') or
            ''
        )

        probe_data = {
            'name': name,
            'manufacturer': manufacturer,
            'probe_type': data.get('probe_type', ''),
            'ndim': data.get('ndim', 2),
            'si_units': data.get('si_units', 'um'),
        }
        
        # Parse electrodes/contacts
        electrodes = []
        
        if 'contact_positions' in data:
            # Modern format with contact_positions
            positions = np.array(data['contact_positions'])
            for i, pos in enumerate(positions):
                electrode = {
                    'id': i,
                    'x': float(pos[0]),
                    'y': float(pos[1]) if len(pos) > 1 else 0.0,
                    'z': float(pos[2]) if len(pos) > 2 else 0.0,
                }

                # Add contact shape if available
                if 'contact_shapes' in data:
                    if isinstance(data['contact_shapes'], list):
                        electrode['shape'] = data['contact_shapes'][i] if i < len(data['contact_shapes']) else 'circle'
                    else:
                        electrode['shape'] = data['contact_shapes']

                # Add contact size if available
                if 'contact_shape_params' in data:
                    shape_params = data['contact_shape_params']
                    if isinstance(shape_params, dict):
                        electrode['shape_params'] = shape_params
                    elif isinstance(shape_params, list) and i < len(shape_params):
                        electrode['shape_params'] = shape_params[i]

                # Add shank_id if available
                if 'shank_ids' in data:
                    shank_ids = data['shank_ids']
                    if isinstance(shank_ids, list) and i < len(shank_ids):
                        shank_id_str = str(shank_ids[i]).strip()
                        if shank_id_str:  # Only convert if not empty
                            try:
                                electrode['shank_id'] = int(shank_id_str)
                            except ValueError:
                                # If conversion fails, skip shank_id
                                pass

                electrodes.append(electrode)
        
        elif 'electrodes' in data:
            # Legacy format with electrodes array
            for e in data['electrodes']:
                electrode = {
                    'id': e.get('id', e.get('electrode_id', 0)),
                    'x': float(e.get('x', 0)),
                    'y': float(e.get('y', 0)),
                    'z': float(e.get('z', 0)),
                }
                
                # Copy additional properties
                for key in ['shape', 'size', 'channel', 'shank_id', 'row', 'column']:
                    if key in e:
                        electrode[key] = e[key]
                
                electrodes.append(electrode)
        
        probe_data['electrodes'] = electrodes
        
        # Parse shank information if multi-shank
        if 'shank_ids' in data:
            probe_data['shanks'] = self._parse_shanks(data, electrodes)
        
        # Add device channel mapping if available
        if 'device_channel_indices' in data:
            probe_data['channel_mapping'] = data['device_channel_indices']
        
        # Add probe shape/contour if available
        if 'probe_planar_contour' in data:
            probe_data['contour'] = data['probe_planar_contour']
        
        return probe_data
    
    def _parse_probe_group(self, data: Dict[str, Any], filepath: str = None) -> Dict[str, Any]:
        """
        Parse a probe group (multiple probes).

        Args:
            data: Raw probe group data
            filepath: Path to source file (for filename fallback)

        Returns:
            Combined probe data
        """
        # For single probe in probes array, just use that probe's data
        probes_list = data.get('probes', [])
        if len(probes_list) == 1:
            return self._parse_single_probe(probes_list[0], filepath)

        # Multiple probes - combine them
        name = data.get('name', 'Probe Group')

        # Use filename fallback if name is generic
        if name == 'Probe Group' and filepath:
            from pathlib import Path
            name = Path(filepath).stem
            self.logger.info(f"Using filename for probe group name: {name}")

        probe_group = {
            'name': name,
            'probes': []
        }

        all_electrodes = []
        electrode_offset = 0

        for probe in probes_list:
            parsed_probe = self._parse_single_probe(probe, filepath)

            # Offset electrode IDs for multiple probes
            for electrode in parsed_probe['electrodes']:
                electrode['id'] += electrode_offset
                electrode['probe_index'] = len(probe_group['probes'])

            all_electrodes.extend(parsed_probe['electrodes'])
            electrode_offset += len(parsed_probe['electrodes'])

            probe_group['probes'].append(parsed_probe)

        # Combine all electrodes
        probe_group['electrodes'] = all_electrodes

        # Collect all contours from individual probes (for merged 3D model generation)
        contours = []
        for i, probe in enumerate(probe_group['probes']):
            if 'contour' in probe:
                contours.append({
                    'contour': probe['contour'],
                    'probe_index': i
                })

        if contours:
            # Store all contours for multi-probe model generation
            probe_group['contours'] = contours
            self.logger.info(f"Found {len(contours)} contours from {len(probes_list)} probes for model generation")

        return probe_group
    
    def _parse_probe_list(self, data: List[Dict[str, Any]], filepath: str = None) -> Dict[str, Any]:
        """
        Parse a list of probes.

        Args:
            data: List of probe definitions
            filepath: Path to source file (for filename fallback)

        Returns:
            Combined probe data
        """
        if len(data) == 1:
            return self._parse_single_probe(data[0], filepath)
        else:
            # Treat as probe group
            return self._parse_probe_group({'probes': data}, filepath)
    
    def _parse_shanks(self, data: Dict[str, Any], electrodes: List[Dict]) -> List[Dict]:
        """
        Parse shank information for multi-shank probes.
        
        Args:
            data: Raw probe data with shank info
            electrodes: List of parsed electrodes
            
        Returns:
            List of shank definitions
        """
        shank_ids = data.get('shank_ids', [])
        unique_shanks = list(set(shank_ids))
        
        shanks = []
        for shank_id in unique_shanks:
            # Get electrodes for this shank
            shank_electrodes = [
                e for e in electrodes 
                if e.get('shank_id') == shank_id or shank_ids[e['id']] == shank_id
            ]
            
            # Calculate shank bounds
            if shank_electrodes:
                x_coords = [e['x'] for e in shank_electrodes]
                y_coords = [e['y'] for e in shank_electrodes]
                
                shank = {
                    'id': shank_id,
                    'electrode_count': len(shank_electrodes),
                    'bounds': {
                        'x_min': min(x_coords),
                        'x_max': max(x_coords),
                        'y_min': min(y_coords),
                        'y_max': max(y_coords),
                    }
                }
                shanks.append(shank)
        
        return shanks
    
    def validate_probe_data(self, probe_data: Dict[str, Any]) -> bool:
        """
        Validate parsed probe data for completeness.
        
        Args:
            probe_data: Parsed probe data
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['electrodes']
        
        for field in required_fields:
            if field not in probe_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Check electrodes have positions
        for electrode in probe_data['electrodes']:
            if 'x' not in electrode or 'y' not in electrode:
                self.logger.error(f"Electrode {electrode.get('id')} missing position data")
                return False
        
        return True
