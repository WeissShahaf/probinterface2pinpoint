"""
Parser for 3D model files (STL and Blender)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import trimesh
from pathlib import Path


class STLParser:
    """
    Parse 3D model files (STL format) for probe geometry.
    
    Handles:
    - STL binary and ASCII formats
    - Coordinate transformations
    - Mesh simplification
    - Bounding box calculations
    - Alignment with electrode coordinates
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, filepath: str) -> Dict[str, Any]:
        """
        Parse STL file and extract geometry information.
        
        Args:
            filepath: Path to STL file
            
        Returns:
            Dictionary containing 3D model data
        """
        self.logger.info(f"Parsing STL file: {filepath}")
        
        try:
            # Load mesh using trimesh
            mesh = trimesh.load(filepath, force='mesh')
            
            # Extract model data
            model_data = {
                'filename': Path(filepath).name,
                'format': 'stl',
                'vertices': mesh.vertices.tolist(),
                'faces': mesh.faces.tolist(),
                'normals': mesh.face_normals.tolist() if hasattr(mesh, 'face_normals') else [],
                'bounds': {
                    'min': mesh.bounds[0].tolist(),
                    'max': mesh.bounds[1].tolist(),
                },
                'center': mesh.center_mass.tolist(),
                'volume': float(mesh.volume) if mesh.is_watertight else None,
                'is_watertight': mesh.is_watertight,
                'vertex_count': len(mesh.vertices),
                'face_count': len(mesh.faces),
            }
            
            # Calculate additional properties
            model_data['dimensions'] = self._calculate_dimensions(mesh)
            model_data['coordinate_system'] = self._infer_coordinate_system(mesh)
            
            # Simplify mesh if too complex (for performance)
            if len(mesh.faces) > 10000:
                simplified = self._simplify_mesh(mesh, target_faces=5000)
                model_data['simplified'] = {
                    'vertices': simplified.vertices.tolist(),
                    'faces': simplified.faces.tolist(),
                    'face_count': len(simplified.faces),
                }
                self.logger.info(f"Simplified mesh from {len(mesh.faces)} to {len(simplified.faces)} faces")
            
            self.logger.info(f"Successfully parsed STL with {model_data['vertex_count']} vertices")
            return model_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse STL file: {str(e)}")
            raise
    
    def parse_blender(self, filepath: str) -> Dict[str, Any]:
        """
        Parse Blender file (.blend) - requires bpy module.
        
        Args:
            filepath: Path to .blend file
            
        Returns:
            Dictionary containing 3D model data
        """
        try:
            import bpy
        except ImportError:
            self.logger.error("Blender Python module (bpy) not installed")
            raise ImportError(
                "Blender file parsing requires the bpy module. "
                "Please install Blender as a Python module or convert to STL format."
            )
        
        self.logger.info(f"Parsing Blender file: {filepath}")
        
        try:
            # Clear existing scene
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # Load blend file
            bpy.ops.wm.open_mainfile(filepath=filepath)
            
            # Find mesh objects
            meshes = []
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    mesh_data = self._extract_blender_mesh(obj)
                    meshes.append(mesh_data)
            
            if not meshes:
                raise ValueError("No mesh objects found in Blender file")
            
            # Combine meshes if multiple
            if len(meshes) == 1:
                model_data = meshes[0]
            else:
                model_data = self._combine_meshes(meshes)
            
            model_data['format'] = 'blender'
            model_data['filename'] = Path(filepath).name
            
            return model_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse Blender file: {str(e)}")
            raise
    
    def _extract_blender_mesh(self, obj) -> Dict[str, Any]:
        """
        Extract mesh data from Blender object.
        
        Args:
            obj: Blender mesh object
            
        Returns:
            Dictionary with mesh data
        """
        import bpy
        
        # Get mesh data
        mesh = obj.data
        
        # Extract vertices
        vertices = np.array([v.co[:] for v in mesh.vertices])
        
        # Extract faces
        faces = []
        for poly in mesh.polygons:
            faces.append(poly.vertices[:])
        
        # Convert to trimesh for consistency
        tm = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        return {
            'name': obj.name,
            'vertices': vertices.tolist(),
            'faces': faces,
            'bounds': {
                'min': tm.bounds[0].tolist(),
                'max': tm.bounds[1].tolist(),
            },
            'center': tm.center_mass.tolist(),
        }
    
    def _calculate_dimensions(self, mesh: trimesh.Trimesh) -> Dict[str, float]:
        """
        Calculate probe dimensions from mesh.
        
        Args:
            mesh: Trimesh object
            
        Returns:
            Dictionary with dimensions
        """
        extents = mesh.extents  # [x, y, z] dimensions
        
        return {
            'width': float(extents[0]),
            'height': float(extents[1]),
            'depth': float(extents[2]),
            'diagonal': float(np.linalg.norm(extents)),
        }
    
    def _infer_coordinate_system(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Infer the coordinate system orientation from mesh.
        
        Args:
            mesh: Trimesh object
            
        Returns:
            Dictionary with coordinate system info
        """
        extents = mesh.extents
        
        # Assume longest dimension is the probe length (usually Y or Z)
        max_dim = np.argmax(extents)
        
        if max_dim == 0:
            primary_axis = 'x'
        elif max_dim == 1:
            primary_axis = 'y'
        else:
            primary_axis = 'z'
        
        return {
            'primary_axis': primary_axis,
            'units': 'unknown',  # Will be determined during alignment
            'orientation': 'standard',  # Can be updated during transformation
        }
    
    def _simplify_mesh(
        self,
        mesh: trimesh.Trimesh,
        target_faces: int = 5000
    ) -> trimesh.Trimesh:
        """
        Simplify mesh to reduce complexity.
        
        Args:
            mesh: Original mesh
            target_faces: Target number of faces
            
        Returns:
            Simplified mesh
        """
        simplified = mesh.simplify_quadric_decimation(
            face_count=target_faces
        )
        return simplified
    
    def align_with_electrodes(
        self,
        model_data: Dict[str, Any],
        electrode_positions: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Align 3D model with electrode positions.
        
        Args:
            model_data: Parsed 3D model data
            electrode_positions: List of electrode positions
            
        Returns:
            Aligned model data
        """
        if not electrode_positions:
            self.logger.warning("No electrode positions provided for alignment")
            return model_data
        
        # Convert electrode positions to numpy array
        electrode_coords = np.array([
            [e.get('x', 0), e.get('y', 0), e.get('z', 0)]
            for e in electrode_positions
        ])
        
        # Get model vertices
        vertices = np.array(model_data['vertices'])
        
        # Calculate scaling factor based on electrode spread
        electrode_range = electrode_coords.max(axis=0) - electrode_coords.min(axis=0)
        model_range = vertices.max(axis=0) - vertices.min(axis=0)
        
        # Avoid division by zero
        scale_factors = np.ones(3)
        for i in range(3):
            if model_range[i] > 0 and electrode_range[i] > 0:
                scale_factors[i] = electrode_range[i] / model_range[i]
        
        # Apply uniform scaling (use median of non-zero factors)
        non_zero_scales = scale_factors[scale_factors > 0]
        if len(non_zero_scales) > 0:
            uniform_scale = np.median(non_zero_scales)
            vertices *= uniform_scale
        
        # Center alignment
        electrode_center = electrode_coords.mean(axis=0)
        model_center = vertices.mean(axis=0)
        translation = electrode_center - model_center
        vertices += translation
        
        # Update model data
        model_data['vertices'] = vertices.tolist()
        model_data['alignment'] = {
            'scale_factor': float(uniform_scale) if 'uniform_scale' in locals() else 1.0,
            'translation': translation.tolist(),
            'electrode_center': electrode_center.tolist(),
        }
        
        # Recalculate bounds
        model_data['bounds'] = {
            'min': vertices.min(axis=0).tolist(),
            'max': vertices.max(axis=0).tolist(),
        }
        
        self.logger.info("Successfully aligned 3D model with electrode positions")
        return model_data
    
    def extract_probe_outline(
        self,
        model_data: Dict[str, Any],
        projection_plane: str = 'xy'
    ) -> List[List[float]]:
        """
        Extract 2D outline of probe from 3D model.
        
        Args:
            model_data: 3D model data
            projection_plane: Plane to project onto ('xy', 'xz', or 'yz')
            
        Returns:
            List of 2D points forming the outline
        """
        vertices = np.array(model_data['vertices'])
        
        # Project to specified plane
        if projection_plane == 'xy':
            points_2d = vertices[:, :2]
        elif projection_plane == 'xz':
            points_2d = vertices[:, [0, 2]]
        elif projection_plane == 'yz':
            points_2d = vertices[:, [1, 2]]
        else:
            raise ValueError(f"Invalid projection plane: {projection_plane}")
        
        # Find convex hull
        from scipy.spatial import ConvexHull
        
        try:
            hull = ConvexHull(points_2d)
            outline = points_2d[hull.vertices].tolist()
        except:
            # If convex hull fails, use bounding box
            min_pt = points_2d.min(axis=0)
            max_pt = points_2d.max(axis=0)
            outline = [
                [min_pt[0], min_pt[1]],
                [max_pt[0], min_pt[1]],
                [max_pt[0], max_pt[1]],
                [min_pt[0], max_pt[1]],
            ]
        
        return outline
    
    def _combine_meshes(self, meshes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine multiple meshes into a single model.
        
        Args:
            meshes: List of mesh dictionaries
            
        Returns:
            Combined mesh data
        """
        all_vertices = []
        all_faces = []
        vertex_offset = 0
        
        for mesh_data in meshes:
            vertices = mesh_data['vertices']
            faces = np.array(mesh_data['faces']) + vertex_offset
            
            all_vertices.extend(vertices)
            all_faces.extend(faces.tolist())
            vertex_offset += len(vertices)
        
        # Create combined trimesh
        combined = trimesh.Trimesh(
            vertices=all_vertices,
            faces=all_faces
        )
        
        return {
            'vertices': all_vertices,
            'faces': all_faces,
            'bounds': {
                'min': combined.bounds[0].tolist(),
                'max': combined.bounds[1].tolist(),
            },
            'center': combined.center_mass.tolist(),
            'combined_from': len(meshes),
        }
