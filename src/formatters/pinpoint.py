"""
Formatter for VirtualBrainLab Pinpoint format
"""

import logging
import re
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime
from utils.probe_database import ProbeDatabase


class PinpointFormatter:
    """
    Format probe data for VirtualBrainLab Pinpoint visualization.
    
    Pinpoint format specifications:
    - JSON structure with probe metadata
    - Electrode positions in standardized coordinates
    - 3D model references
    - Channel mapping information
    - Visualization parameters
    """
    
    def __init__(self, config: Optional[Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.probe_db = ProbeDatabase()  # Initialize probe database for shank thickness lookup
        self.obj_scale_factor = 100.0  # Scale down by 100x for OBJ export
    
    def format(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format probe data for Pinpoint multi-file format.

        Returns dictionary with keys:
        - 'probe_name': Sanitized folder name
        - 'metadata': Content for metadata.json
        - 'site_map': List of dicts for site_map.csv rows
        - 'model': OBJ file content string (or None if no 3D model)

        Args:
            probe_data: Standardized probe data

        Returns:
            Multi-file structure dictionary
        """
        self.logger.info("Formatting data for Pinpoint multi-file format")

        try:
            # Generate metadata.json content (top-level fields)
            metadata = self._generate_metadata(probe_data)

            # Generate site_map.csv content
            # Pass probe name for shank thickness lookup
            site_map = self._generate_site_map(
                probe_data.get('electrodes', []),
                probe_name=probe_data.get('name', '')
            )

            # Generate model.obj content
            model_obj = None
            if 'model_3d' in probe_data and self._has_geometry(probe_data['model_3d']):
                # Use 3D model from STL file
                model_obj = self._generate_obj_model(probe_data['model_3d'])
            elif 'contours' in probe_data:
                # Multi-probe group with multiple contours - merge into single model
                shank_thickness = None
                if probe_data.get('name'):
                    shank_thickness = self.probe_db.get_shank_thickness(probe_data['name'])
                model_obj = self._generate_merged_obj_from_contours(
                    probe_data['contours'],
                    shank_thickness
                )
            elif 'contour' in probe_data or 'planar_contour' in probe_data:
                # Single probe with single contour
                # Check if this is a multi-shank probe that needs separate shank geometry
                electrodes = probe_data.get('electrodes', [])
                unique_shanks = self._get_unique_shank_ids(electrodes)
                contour = probe_data.get('contour') or probe_data.get('planar_contour')

                if len(unique_shanks) > 1 and contour:
                    # Multi-shank probe - split contour into separate shanks
                    self.logger.info(f"Multi-shank probe detected ({len(unique_shanks)} shanks), splitting contour into separate shank geometries")
                    shank_thickness = None
                    if probe_data.get('name'):
                        shank_thickness = self.probe_db.get_shank_thickness(probe_data['name'])
                    model_obj = self._generate_multi_shank_obj_from_contour(
                        contour,
                        electrodes,
                        unique_shanks,
                        shank_thickness
                    )
                else:
                    # Single shank - use contour as-is
                    shank_thickness = None
                    if probe_data.get('name'):
                        shank_thickness = self.probe_db.get_shank_thickness(probe_data['name'])
                    model_obj = self._generate_obj_from_contour(contour, shank_thickness)

            # Get sanitized probe name for folder
            probe_name = self._sanitize_name(metadata['name'])

            result = {
                'probe_name': probe_name,
                'metadata': metadata,
                'site_map': site_map,
                'model': model_obj,
            }

            self.logger.info(f"Successfully formatted data for Pinpoint (probe: {probe_name})")
            return result

        except Exception as e:
            self.logger.error(f"Failed to format data: {str(e)}")
            raise
    
    def _format_probe_info(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format probe metadata.
        
        Args:
            probe_data: Source probe data
            
        Returns:
            Formatted probe info
        """
        info = {
            'name': probe_data.get('name', 'Unknown Probe'),
            'manufacturer': probe_data.get('manufacturer', ''),
            'type': probe_data.get('probe_type', ''),
            'source_format': probe_data.get('source_format', 'unknown'),
        }
        
        # Add dimensions if available
        if 'dimensions' in probe_data:
            info['dimensions'] = probe_data['dimensions']
        elif 'electrodes' in probe_data and probe_data['electrodes']:
            # Calculate from electrodes
            info['dimensions'] = self._calculate_dimensions(probe_data['electrodes'])
        
        # Add electrode count
        info['electrode_count'] = len(probe_data.get('electrodes', []))
        
        # Add coordinate system info
        info['coordinate_system'] = probe_data.get('coordinate_system', {
            'units': 'micrometers',
            'origin': 'tip',
            'axes': 'RAS'  # Right-Anterior-Superior (neuroimaging convention)
        })
        
        return info
    
    def _format_electrodes(self, electrodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format electrode data for Pinpoint.
        
        Args:
            electrodes: List of electrode dictionaries
            
        Returns:
            Formatted electrode list
        """
        formatted_electrodes = []
        
        for i, electrode in enumerate(electrodes):
            formatted = {
                'id': electrode.get('id', i),
                'position': {
                    'x': float(electrode.get('x', 0)),
                    'y': float(electrode.get('y', 0)),
                    'z': float(electrode.get('z', 0)),
                },
            }
            
            # Add channel if available
            if 'channel' in electrode:
                formatted['channel'] = electrode['channel']
            
            # Add shank ID if multi-shank
            if 'shank_id' in electrode:
                formatted['shank_id'] = electrode['shank_id']
            
            # Add shape information
            if 'shape' in electrode:
                formatted['shape'] = electrode['shape']
            else:
                formatted['shape'] = 'circle'  # Default
            
            if 'shape_params' in electrode:
                formatted['shape_params'] = electrode['shape_params']
            elif formatted['shape'] == 'circle':
                formatted['shape_params'] = {'radius': 10}  # Default 10um radius
            elif formatted['shape'] == 'square':
                formatted['shape_params'] = {'width': 20}  # Default 20um square
            
            # Add grid position if available
            if 'row' in electrode and 'column' in electrode:
                formatted['grid_position'] = {
                    'row': electrode['row'],
                    'column': electrode['column'],
                }
            
            # Add any custom properties
            custom_props = {}
            exclude_keys = {'id', 'x', 'y', 'z', 'channel', 'shank_id', 
                          'shape', 'shape_params', 'row', 'column'}
            for key, value in electrode.items():
                if key not in exclude_keys:
                    custom_props[key] = value
            
            if custom_props:
                formatted['properties'] = custom_props
            
            formatted_electrodes.append(formatted)
        
        return formatted_electrodes
    
    def _format_geometry(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format probe geometry information.
        
        Args:
            probe_data: Source probe data
            
        Returns:
            Formatted geometry
        """
        geometry = {}
        
        # Add probe contour if available
        if 'contour' in probe_data:
            geometry['contour'] = probe_data['contour']
        elif 'model_3d' in probe_data and 'outline' in probe_data['model_3d']:
            geometry['contour'] = probe_data['model_3d']['outline']
        else:
            # Generate bounding box from electrodes
            if 'electrodes' in probe_data and probe_data['electrodes']:
                geometry['contour'] = self._generate_bounding_contour(
                    probe_data['electrodes']
                )
        
        # Add probe shape type
        if 'shanks' in probe_data and len(probe_data['shanks']) > 1:
            geometry['shape_type'] = 'multi_shank'
        else:
            geometry['shape_type'] = 'single_shank'
        
        # Add dimensions
        if 'dimensions' in probe_data:
            geometry['dimensions'] = probe_data['dimensions']
        
        return geometry
    
    def _format_3d_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format 3D model data for Pinpoint.
        
        Args:
            model_data: 3D model data
            
        Returns:
            Formatted 3D model reference
        """
        formatted = {
            'format': model_data.get('format', 'stl'),
            'source_file': model_data.get('filename', ''),
        }
        
        # Include simplified mesh if available
        if 'simplified' in model_data:
            formatted['mesh'] = {
                'vertices': model_data['simplified']['vertices'],
                'faces': model_data['simplified']['faces'],
            }
        else:
            # Include full mesh if not too large
            if len(model_data.get('vertices', [])) < 10000:
                formatted['mesh'] = {
                    'vertices': model_data['vertices'],
                    'faces': model_data['faces'],
                }
            else:
                # Just include reference and bounds
                formatted['mesh'] = {
                    'vertex_count': model_data.get('vertex_count', 0),
                    'face_count': model_data.get('face_count', 0),
                    'bounds': model_data.get('bounds', {}),
                }
        
        # Add alignment information
        if 'alignment' in model_data:
            formatted['alignment'] = model_data['alignment']
        
        return formatted
    
    def _format_shanks(self, shanks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format multi-shank information.
        
        Args:
            shanks: List of shank definitions
            
        Returns:
            Formatted shank list
        """
        formatted_shanks = []
        
        for shank in shanks:
            formatted = {
                'id': shank['id'],
                'electrode_count': shank.get('electrode_count', 0),
            }
            
            # Add bounds if available
            if 'bounds' in shank:
                formatted['bounds'] = shank['bounds']
            
            # Add spacing information
            if 'electrode_pitch' in shank:
                formatted['electrode_pitch'] = shank['electrode_pitch']
            
            formatted_shanks.append(formatted)
        
        return formatted_shanks
    
    def _format_visualization(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format visualization parameters for Pinpoint.
        
        Args:
            probe_data: Source probe data
            
        Returns:
            Visualization settings
        """
        viz = {
            'default_view': 'side',  # 'side', 'top', or '3d'
            'electrode_size': 10,  # Default size in pixels
            'show_channels': True,
            'show_labels': False,
            'color_scheme': 'default',
        }
        
        # Determine best default view based on probe type
        if 'shanks' in probe_data and len(probe_data.get('shanks', [])) > 1:
            viz['default_view'] = 'top'  # Better for multi-shank
        elif 'model_3d' in probe_data:
            viz['default_view'] = '3d'
        
        # Add color mapping for channels if available
        if 'channel_mapping' in probe_data:
            viz['channel_colors'] = self._generate_channel_colors(
                probe_data['channel_mapping']
            )
        
        return viz
    
    def _calculate_dimensions(self, electrodes: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate probe dimensions from electrode positions.
        
        Args:
            electrodes: List of electrodes
            
        Returns:
            Dimensions dictionary
        """
        if not electrodes:
            return {'width': 0, 'height': 0, 'depth': 0}
        
        x_coords = [e.get('x', 0) for e in electrodes]
        y_coords = [e.get('y', 0) for e in electrodes]
        z_coords = [e.get('z', 0) for e in electrodes]
        
        return {
            'width': float(max(x_coords) - min(x_coords)) if x_coords else 0,
            'height': float(max(y_coords) - min(y_coords)) if y_coords else 0,
            'depth': float(max(z_coords) - min(z_coords)) if z_coords else 0,
        }
    
    def _generate_bounding_contour(
        self,
        electrodes: List[Dict[str, Any]]
    ) -> List[List[float]]:
        """
        Generate a bounding contour from electrode positions.
        
        Args:
            electrodes: List of electrodes
            
        Returns:
            Contour points
        """
        if not electrodes:
            return []
        
        # Get 2D positions (x, y)
        points = np.array([[e.get('x', 0), e.get('y', 0)] for e in electrodes])
        
        # Calculate convex hull
        from scipy.spatial import ConvexHull
        
        try:
            hull = ConvexHull(points)
            contour = points[hull.vertices].tolist()
        except:
            # Fallback to bounding box
            min_pt = points.min(axis=0)
            max_pt = points.max(axis=0)
            contour = [
                [float(min_pt[0]), float(min_pt[1])],
                [float(max_pt[0]), float(min_pt[1])],
                [float(max_pt[0]), float(max_pt[1])],
                [float(min_pt[0]), float(max_pt[1])],
            ]
        
        return contour
    
    def _generate_channel_colors(self, channel_mapping: List[int]) -> Dict[int, str]:
        """
        Generate color mapping for channels.
        
        Args:
            channel_mapping: Channel indices
            
        Returns:
            Dictionary mapping channel to color hex
        """
        import matplotlib.cm as cm
        import matplotlib.colors as mcolors
        
        n_channels = len(set(channel_mapping))
        colormap = cm.get_cmap('viridis')
        
        colors = {}
        for i, channel in enumerate(set(channel_mapping)):
            color_rgb = colormap(i / n_channels)[:3]
            color_hex = mcolors.rgb2hex(color_rgb)
            colors[channel] = color_hex
        
        return colors

    def _generate_metadata(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate metadata.json content for Pinpoint format.

        Args:
            probe_data: Source probe data

        Returns:
            Metadata dictionary with Pinpoint-spec fields
        """
        # Get probe name from various possible sources
        name = probe_data.get('name', 'Unknown Probe')

        metadata = {
            'name': name,
            'type': 1001,  # Placeholder - can be made configurable later
            'producer': probe_data.get('manufacturer', ''),
            'sites': len(probe_data.get('electrodes', [])),
            'shanks': self._count_shanks(probe_data),
            'references': probe_data.get('references', ''),
            'spec': probe_data.get('spec_url', ''),
        }

        return metadata

    def _generate_site_map(
        self,
        electrodes: List[Dict[str, Any]],
        probe_name: str = ''
    ) -> List[Dict[str, Any]]:
        """
        Generate site_map.csv row data from electrodes.

        Columns: index, x, y, z, w, h, d, default, layer1, layer2

        For 2D probes (ndim=2), the z coordinate represents the shank thickness,
        which is looked up from the probe database.

        Args:
            electrodes: List of electrode dictionaries
            probe_name: Probe model name for database lookup

        Returns:
            List of dictionaries for CSV rows
        """
        rows = []

        # Look up shank thickness for this probe model (for 2D probes)
        shank_thickness_z = None
        if probe_name:
            shank_thickness = self.probe_db.get_shank_thickness(probe_name)
            if shank_thickness is not None:
                shank_thickness_z = float(shank_thickness)
                self.logger.info(
                    f"Using shank thickness as z coordinate: {shank_thickness_z} μm "
                    f"(probe: {probe_name})"
                )

        for electrode in electrodes:
            # Get position from electrode dict
            if 'position' in electrode:
                # Nested position format
                pos = electrode['position']
                x = pos.get('x', 0)
                y = pos.get('y', 0)
                z = pos.get('z', 0)
            else:
                # Flat format
                x = electrode.get('x', 0)
                y = electrode.get('y', 0)
                z = electrode.get('z', 0)

            # Override z with shank thickness if available and z is 0
            # (for 2D probes, z should represent physical shank thickness)
            if shank_thickness_z is not None and z == 0:
                z = shank_thickness_z

            # Calculate width, height, depth from shape
            shape = electrode.get('shape', 'circle')
            shape_params = electrode.get('shape_params', {})

            if shape == 'circle':
                radius = shape_params.get('radius', 10)
                w = h = radius * 2
            elif shape == 'square':
                width = shape_params.get('width', 20)
                w = h = width
            else:
                # Default to circle with 10um radius
                w = h = 20

            d = 0  # 2D electrodes (depth = 0)

            row = {
                'index': electrode.get('id', len(rows)),
                'x': float(x),
                'y': float(y),
                'z': float(z),
                'w': float(w),
                'h': float(h),
                'd': float(d),
                'default': 1,  # Visible by default
                'layer1': 1,   # In layer 1 by default
                'layer2': 0,   # Not in layer 2
            }
            rows.append(row)

        return rows

    def _generate_obj_model(self, model_3d: Dict[str, Any]) -> str:
        """
        Generate Wavefront OBJ file content from 3D model data.

        OBJ format:
        - Vertices: v x y z
        - Faces: f v1 v2 v3 (1-based indexing)

        Args:
            model_3d: 3D model data with 'vertices' and 'faces'

        Returns:
            OBJ file content as string
        """
        lines = []

        # Add header comment
        lines.append("# Probe 3D model")
        lines.append("# Generated by pinpoint_converter")
        lines.append("")

        # Write vertices (scaled)
        vertices = model_3d.get('vertices', [])
        for vertex in vertices:
            if len(vertex) >= 3:
                x, y, z = vertex[0] / self.obj_scale_factor, vertex[1] / self.obj_scale_factor, vertex[2] / self.obj_scale_factor
                lines.append(f"v {x} {y} {z}")

        lines.append("")

        # Write faces (add 1 to indices for 1-based indexing)
        faces = model_3d.get('faces', [])
        for face in faces:
            if len(face) >= 3:
                indices = ' '.join(str(int(idx) + 1) for idx in face)
                lines.append(f"f {indices}")

        return '\n'.join(lines) + '\n'

    def _sanitize_name(self, name: str) -> str:
        """
        Remove invalid filesystem characters from probe name.

        Sanitizes: < > : " / \\ | ? *

        Args:
            name: Original probe name

        Returns:
            Sanitized name safe for use as folder name
        """
        # Remove invalid filesystem characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name).strip()

        # Log if name was changed
        if sanitized != name:
            self.logger.warning(f"Sanitized probe name: '{name}' → '{sanitized}'")

        return sanitized

    def _count_shanks(self, probe_data: Dict[str, Any]) -> int:
        """
        Count number of shanks in probe.

        Args:
            probe_data: Probe data

        Returns:
            Number of shanks
        """
        if 'shanks' in probe_data:
            return len(probe_data['shanks'])

        # Count unique shank_ids in electrodes
        shank_ids = set()
        for electrode in probe_data.get('electrodes', []):
            if 'shank_id' in electrode:
                shank_ids.add(electrode['shank_id'])

        return len(shank_ids) if shank_ids else 1

    def _has_geometry(self, model_3d: Dict[str, Any]) -> bool:
        """
        Check if 3D model has valid geometry data.

        Args:
            model_3d: 3D model data

        Returns:
            True if model has vertices and faces
        """
        if not model_3d:
            return False

        vertices = model_3d.get('vertices', [])
        faces = model_3d.get('faces', [])

        return len(vertices) > 0 and len(faces) > 0

    def _generate_obj_from_contour(
        self,
        contour: List[List[float]],
        shank_thickness: Optional[float] = None
    ) -> str:
        """
        Generate Wavefront OBJ file from 2D probe contour by extrusion.

        Creates a 3D mesh by:
        1. Using contour points as the base (z=0)
        2. Extruding to create top face (z=shank_thickness)
        3. Creating side faces connecting base and top

        Args:
            contour: List of [x, y] points defining probe outline
            shank_thickness: Thickness to extrude (micrometers), default 15

        Returns:
            OBJ file content as string
        """
        if not contour or len(contour) < 3:
            self.logger.warning("Contour has insufficient points for 3D model generation")
            return ""

        # Default shank thickness if not provided
        if shank_thickness is None:
            shank_thickness = 15.0
            self.logger.info(f"Using default shank thickness: {shank_thickness} μm")
        else:
            self.logger.info(f"Generating 3D model from contour (thickness: {shank_thickness} μm)")

        lines = []
        lines.append("# Probe 3D model")
        lines.append("# Generated from probe contour by extrusion")
        lines.append(f"# Shank thickness: {shank_thickness} μm")
        lines.append("")

        n_points = len(contour)

        # Generate vertices (scaled down by 100x)
        # Bottom face vertices (z = 0)
        for point in contour:
            x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
            lines.append(f"v {x} {y} 0.0")

        # Top face vertices (z = shank_thickness)
        for point in contour:
            x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
            z_scaled = shank_thickness / self.obj_scale_factor
            lines.append(f"v {x} {y} {z_scaled}")

        lines.append("")

        # Generate faces
        # Bottom face (vertices 1 to n_points, wound counter-clockwise when viewed from below)
        # Use triangle fan from first vertex
        for i in range(1, n_points - 1):
            lines.append(f"f 1 {i + 1} {i + 2}")

        # Top face (vertices n_points+1 to 2*n_points, wound counter-clockwise when viewed from above)
        base_idx = n_points
        for i in range(1, n_points - 1):
            lines.append(f"f {base_idx + 1} {base_idx + i + 2} {base_idx + i + 1}")

        # Side faces (quads connecting bottom and top, split into triangles)
        for i in range(n_points):
            next_i = (i + 1) % n_points

            # Bottom vertex indices (1-based)
            v1 = i + 1
            v2 = next_i + 1

            # Top vertex indices (1-based)
            v3 = v1 + n_points
            v4 = v2 + n_points

            # Create two triangles for the quad
            # Triangle 1: v1, v2, v3
            lines.append(f"f {v1} {v2} {v3}")
            # Triangle 2: v2, v4, v3
            lines.append(f"f {v2} {v4} {v3}")

        return '\n'.join(lines) + '\n'

    def _generate_merged_obj_from_contours(
        self,
        contours_data: List[Dict[str, Any]],
        shank_thickness: Optional[float] = None
    ) -> str:
        """
        Generate merged Wavefront OBJ file from multiple probe contours.

        For probe groups with multiple shanks (e.g., ASSY-325D-H7 with 2 shanks),
        this combines all contours into a single unified 3D model.

        Args:
            contours_data: List of dicts with 'contour' and 'probe_index'
            shank_thickness: Thickness to extrude (micrometers), default 15

        Returns:
            OBJ file content as string with merged geometry
        """
        if not contours_data:
            self.logger.warning("No contours provided for merged model generation")
            return ""

        # Default shank thickness if not provided
        if shank_thickness is None:
            shank_thickness = 15.0
            self.logger.info(f"Using default shank thickness: {shank_thickness} μm")
        else:
            self.logger.info(f"Generating merged 3D model from {len(contours_data)} contours (thickness: {shank_thickness} μm)")

        lines = []
        lines.append("# Probe 3D model (merged from multiple shanks)")
        lines.append(f"# Number of shanks: {len(contours_data)}")
        lines.append(f"# Shank thickness: {shank_thickness} μm")
        lines.append("")

        vertex_offset = 0  # Track vertex indices across contours
        all_vertices = []
        all_faces = []

        for i, contour_data in enumerate(contours_data):
            contour = contour_data['contour']
            n_points = len(contour)

            if n_points < 3:
                self.logger.warning(f"Contour {i} has insufficient points, skipping")
                continue

            # For 3D contours with [x, y, z] format:
            # - Extract x, z for the contour shape (probe face in x-z plane)
            # - y represents offset between shanks (e.g., y=0 and y=30)
            # - Extrusion is in the y direction (shank thickness)

            # Detect if contour is 2D [x, z] or 3D [x, y, z]
            first_point = contour[0]
            is_3d_contour = len(first_point) == 3

            # Bottom face vertices (scaled)
            for point in contour:
                if is_3d_contour:
                    x, y, z = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor, point[2] / self.obj_scale_factor
                    all_vertices.append(f"v {x} {y} {z}")
                else:
                    x, z = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                    all_vertices.append(f"v {x} 0.0 {z}")

            # Top face vertices (extruded in y direction by shank_thickness, scaled)
            for point in contour:
                if is_3d_contour:
                    x, y, z = point[0] / self.obj_scale_factor, (point[1] + shank_thickness) / self.obj_scale_factor, point[2] / self.obj_scale_factor
                    all_vertices.append(f"v {x} {y} {z}")
                else:
                    x, z = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                    y_scaled = shank_thickness / self.obj_scale_factor
                    all_vertices.append(f"v {x} {y_scaled} {z}")

            # Generate faces for this contour
            base_idx = vertex_offset + 1  # OBJ indices are 1-based

            # Bottom face (triangle fan)
            for j in range(1, n_points - 1):
                all_faces.append(f"f {base_idx} {base_idx + j} {base_idx + j + 1}")

            # Top face (triangle fan)
            top_base = base_idx + n_points
            for j in range(1, n_points - 1):
                all_faces.append(f"f {top_base} {top_base + j + 1} {top_base + j}")

            # Side faces (connecting bottom and top)
            for j in range(n_points):
                next_j = (j + 1) % n_points

                v1 = base_idx + j
                v2 = base_idx + next_j
                v3 = v1 + n_points
                v4 = v2 + n_points

                # Two triangles per quad
                all_faces.append(f"f {v1} {v2} {v3}")
                all_faces.append(f"f {v2} {v4} {v3}")

            vertex_offset += n_points * 2  # Each contour adds bottom + top vertices

        # Combine all vertices and faces
        lines.extend(all_vertices)
        lines.append("")
        lines.extend(all_faces)

        return '\n'.join(lines) + '\n'

    def _get_unique_shank_ids(self, electrodes: List[Dict[str, Any]]) -> List[int]:
        """
        Get unique shank IDs from electrode list.

        Args:
            electrodes: List of electrode dictionaries

        Returns:
            Sorted list of unique shank IDs
        """
        shank_ids = set()
        for electrode in electrodes:
            if 'shank_id' in electrode:
                shank_ids.add(electrode['shank_id'])

        return sorted(list(shank_ids))

    def _generate_multi_shank_obj_from_contour(
        self,
        contour: List[List[float]],
        electrodes: List[Dict[str, Any]],
        shank_ids: List[int],
        shank_thickness: Optional[float] = None
    ) -> str:
        """
        Generate separate shank geometries by splitting a multi-shank contour.

        For probes like ASSY-276-H7, the probe_planar_contour traces around
        all shanks in a single path. This method splits the contour into
        separate shanks based on electrode positions.

        Args:
            contour: Single contour tracing around all shanks
            electrodes: List of electrode dictionaries with positions and shank_ids
            shank_ids: List of unique shank IDs
            shank_thickness: Thickness to extrude (micrometers), default 15

        Returns:
            OBJ file content with separate shank geometries
        """
        if not contour or not electrodes or not shank_ids:
            self.logger.warning("Missing contour, electrodes, or shank IDs for multi-shank split")
            return ""

        # Default shank thickness if not provided
        if shank_thickness is None:
            shank_thickness = 15.0
            self.logger.info(f"Using default shank thickness: {shank_thickness} μm")
        else:
            self.logger.info(f"Splitting contour into {len(shank_ids)} separate shanks (thickness: {shank_thickness} μm)")

        # Calculate electrode centroids for each shank
        shank_centers = {}
        for shank_id in shank_ids:
            shank_electrodes = [e for e in electrodes if e.get('shank_id') == shank_id]
            if shank_electrodes:
                x_coords = [e.get('x', 0) for e in shank_electrodes]
                shank_centers[shank_id] = sum(x_coords) / len(x_coords)

        # Assign contour points to shanks based on x-coordinate proximity
        shank_contours = {shank_id: [] for shank_id in shank_ids}

        for point in contour:
            x, y = point[0], point[1]
            # Find closest shank by x-coordinate
            closest_shank = min(shank_ids, key=lambda sid: abs(x - shank_centers.get(sid, 0)))
            shank_contours[closest_shank].append([x, y])

        # Generate OBJ file with separate shanks
        lines = []
        lines.append("# Probe 3D model (split from multi-shank contour)")
        lines.append(f"# Number of shanks: {len(shank_ids)}")
        lines.append(f"# Shank thickness: {shank_thickness} μm")
        lines.append("")

        vertex_offset = 0
        all_vertices = []
        all_faces = []

        for shank_id in shank_ids:
            shank_contour = shank_contours[shank_id]

            if len(shank_contour) < 3:
                self.logger.warning(f"Insufficient contour points for shank {shank_id}, skipping")
                continue

            n_points = len(shank_contour)

            # Bottom face vertices (z = 0, scaled)
            for point in shank_contour:
                x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                all_vertices.append(f"v {x} {y} 0.0")

            # Top face vertices (z = shank_thickness, scaled)
            for point in shank_contour:
                x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                z_scaled = shank_thickness / self.obj_scale_factor
                all_vertices.append(f"v {x} {y} {z_scaled}")

            # Generate faces for this shank
            base_idx = vertex_offset + 1  # OBJ indices are 1-based

            # Bottom face (triangle fan)
            for j in range(1, n_points - 1):
                all_faces.append(f"f {base_idx} {base_idx + j} {base_idx + j + 1}")

            # Top face (triangle fan, reversed winding)
            top_base = base_idx + n_points
            for j in range(1, n_points - 1):
                all_faces.append(f"f {top_base} {top_base + j + 1} {top_base + j}")

            # Side faces (connecting bottom and top)
            for j in range(n_points):
                next_j = (j + 1) % n_points

                v1 = base_idx + j
                v2 = base_idx + next_j
                v3 = v1 + n_points
                v4 = v2 + n_points

                # Two triangles per quad
                all_faces.append(f"f {v1} {v2} {v3}")
                all_faces.append(f"f {v2} {v4} {v3}")

            vertex_offset += n_points * 2

        # Combine all vertices and faces
        lines.extend(all_vertices)
        lines.append("")
        lines.extend(all_faces)

        return '\n'.join(lines) + '\n'

    def _generate_multi_shank_obj_from_electrodes(
        self,
        electrodes: List[Dict[str, Any]],
        shank_ids: List[int],
        shank_thickness: Optional[float] = None
    ) -> str:
        """
        Generate separate shank geometries from electrode positions.

        For multi-shank probes (e.g., ASSY-276-H7), generates individual
        shank shapes based on electrode positions rather than using the
        outer contour which connects all shanks.

        Args:
            electrodes: List of electrode dictionaries with positions
            shank_ids: List of unique shank IDs
            shank_thickness: Thickness to extrude (micrometers), default 15

        Returns:
            OBJ file content with separate shank geometries
        """
        if not electrodes or not shank_ids:
            self.logger.warning("No electrodes or shank IDs for multi-shank geometry")
            return ""

        # Default shank thickness if not provided
        if shank_thickness is None:
            shank_thickness = 15.0
            self.logger.info(f"Using default shank thickness: {shank_thickness} μm")
        else:
            self.logger.info(f"Generating multi-shank 3D model from {len(shank_ids)} shanks (thickness: {shank_thickness} μm)")

        lines = []
        lines.append("# Probe 3D model (separate shanks from electrode positions)")
        lines.append(f"# Number of shanks: {len(shank_ids)}")
        lines.append(f"# Shank thickness: {shank_thickness} μm")
        lines.append("")

        vertex_offset = 0
        all_vertices = []
        all_faces = []

        for shank_id in shank_ids:
            # Get electrodes for this shank
            shank_electrodes = [e for e in electrodes if e.get('shank_id') == shank_id]

            if not shank_electrodes:
                self.logger.warning(f"No electrodes found for shank {shank_id}, skipping")
                continue

            # Extract electrode positions
            positions = []
            for e in shank_electrodes:
                x = e.get('x', 0)
                y = e.get('y', 0)
                positions.append([float(x), float(y)])

            # Generate shank outline from electrode positions
            shank_contour = self._generate_shank_outline(positions)

            if len(shank_contour) < 3:
                self.logger.warning(f"Insufficient points for shank {shank_id} outline, skipping")
                continue

            n_points = len(shank_contour)

            # Bottom face vertices (z = 0, scaled)
            for point in shank_contour:
                x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                all_vertices.append(f"v {x} {y} 0.0")

            # Top face vertices (z = shank_thickness, scaled)
            for point in shank_contour:
                x, y = point[0] / self.obj_scale_factor, point[1] / self.obj_scale_factor
                z_scaled = shank_thickness / self.obj_scale_factor
                all_vertices.append(f"v {x} {y} {z_scaled}")

            # Generate faces for this shank
            base_idx = vertex_offset + 1  # OBJ indices are 1-based

            # Bottom face (triangle fan)
            for j in range(1, n_points - 1):
                all_faces.append(f"f {base_idx} {base_idx + j} {base_idx + j + 1}")

            # Top face (triangle fan, reversed winding)
            top_base = base_idx + n_points
            for j in range(1, n_points - 1):
                all_faces.append(f"f {top_base} {top_base + j + 1} {top_base + j}")

            # Side faces (connecting bottom and top)
            for j in range(n_points):
                next_j = (j + 1) % n_points

                v1 = base_idx + j
                v2 = base_idx + next_j
                v3 = v1 + n_points
                v4 = v2 + n_points

                # Two triangles per quad
                all_faces.append(f"f {v1} {v2} {v3}")
                all_faces.append(f"f {v2} {v4} {v3}")

            vertex_offset += n_points * 2

        # Combine all vertices and faces
        lines.extend(all_vertices)
        lines.append("")
        lines.extend(all_faces)

        return '\n'.join(lines) + '\n'

    def _generate_shank_outline(self, electrode_positions: List[List[float]], padding: float = 30.0) -> List[List[float]]:
        """
        Generate a shank outline around electrode positions.

        Creates a simplified probe shank shape by:
        1. Finding the convex hull of electrode positions
        2. Adding padding around the hull
        3. Creating a tapered tip at the bottom

        Args:
            electrode_positions: List of [x, y] electrode positions
            padding: Padding around electrodes in micrometers (default 30)

        Returns:
            List of [x, y] points defining the shank outline
        """
        if not electrode_positions:
            return []

        try:
            from scipy.spatial import ConvexHull
            import numpy as np

            # Convert to numpy array
            points = np.array(electrode_positions)

            if len(points) < 3:
                # Not enough points for convex hull, create simple box
                return self._generate_simple_box_outline(points, padding)

            # Calculate convex hull
            hull = ConvexHull(points)
            hull_points = points[hull.vertices]

            # Find min/max y to identify tip and top
            min_y = np.min(hull_points[:, 1])
            max_y = np.max(hull_points[:, 1])
            mean_x = np.mean(hull_points[:, 0])

            # Separate points into left, right, bottom (tip), and top
            tip_points = hull_points[hull_points[:, 1] < min_y + 100]  # Bottom 100μm
            top_points = hull_points[hull_points[:, 1] > max_y - 100]  # Top 100μm
            left_points = hull_points[hull_points[:, 0] < mean_x]
            right_points = hull_points[hull_points[:, 0] >= mean_x]

            # Build shank outline with taper
            outline = []

            # Top left corner
            if len(top_points) > 0 and len(left_points) > 0:
                top_left = left_points[np.argmax(left_points[:, 1])]
                outline.append([top_left[0] - padding, top_left[1] + padding])

            # Left side (top to bottom)
            left_sorted = left_points[np.argsort(left_points[:, 1])[::-1]]  # Sort by y descending
            for point in left_sorted:
                if point[1] > min_y + 50:  # Above tip
                    outline.append([point[0] - padding, point[1]])

            # Tip (tapered point)
            if len(tip_points) > 0:
                tip_x = np.mean(tip_points[:, 0])
                outline.append([tip_x, min_y - 80])  # Sharp tip

            # Right side (bottom to top)
            right_sorted = right_points[np.argsort(right_points[:, 1])]  # Sort by y ascending
            for point in right_sorted:
                if point[1] > min_y + 50:  # Above tip
                    outline.append([point[0] + padding, point[1]])

            # Top right corner
            if len(top_points) > 0 and len(right_points) > 0:
                top_right = right_points[np.argmax(right_points[:, 1])]
                outline.append([top_right[0] + padding, top_right[1] + padding])

            return outline

        except ImportError:
            self.logger.warning("scipy not available, using simple box outline")
            return self._generate_simple_box_outline(np.array(electrode_positions), padding)
        except Exception as e:
            self.logger.warning(f"Error generating convex hull: {e}, using simple box outline")
            return self._generate_simple_box_outline(np.array(electrode_positions), padding)

    def _generate_simple_box_outline(self, points, padding: float = 30.0) -> List[List[float]]:
        """
        Generate a simple rectangular outline with tapered tip.

        Args:
            points: Numpy array or list of [x, y] positions
            padding: Padding in micrometers

        Returns:
            List of [x, y] points defining rectangular outline with tip
        """
        import numpy as np

        points = np.array(points)
        min_x = np.min(points[:, 0])
        max_x = np.max(points[:, 0])
        min_y = np.min(points[:, 1])
        max_y = np.max(points[:, 1])
        mean_x = (min_x + max_x) / 2

        # Create rectangle with tapered tip
        outline = [
            [min_x - padding, max_y + padding],  # Top left
            [min_x - padding, min_y + 50],       # Left side above tip
            [mean_x, min_y - 80],                # Tip point
            [max_x + padding, min_y + 50],       # Right side above tip
            [max_x + padding, max_y + padding],  # Top right
        ]

        return outline

    def validate_output(self, pinpoint_data: Dict[str, Any]) -> bool:
        """
        Validate Pinpoint format output.
        
        Args:
            pinpoint_data: Formatted data
            
        Returns:
            True if valid
        """
        required_fields = ['format_version', 'probe', 'electrodes']
        
        for field in required_fields:
            if field not in pinpoint_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Check electrodes have positions
        for electrode in pinpoint_data['electrodes']:
            if 'position' not in electrode:
                self.logger.error(f"Electrode {electrode.get('id')} missing position")
                return False
        
        return True
