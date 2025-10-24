"""
Geometry transformation module for 3D models and probe shapes
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy.spatial import distance_matrix, procrustes
from scipy.optimize import minimize


class GeometryTransformer:
    """
    Handle geometric transformations for 3D models and probe shapes.
    
    Supports:
    - 3D model alignment with electrode positions
    - Mesh transformations (scaling, rotation, translation)
    - Probe outline extraction
    - Shape fitting and registration
    - Geometric validation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def transform_model(
        self,
        model_data: Dict[str, Any],
        electrodes: List[Dict[str, Any]],
        method: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Transform 3D model to align with electrode positions.
        
        Args:
            model_data: 3D model data dictionary
            electrodes: List of electrode positions
            method: Alignment method ('auto', 'icp', 'procrustes', 'manual')
            
        Returns:
            Transformed model data
        """
        if not electrodes:
            self.logger.warning("No electrodes provided for model alignment")
            return model_data
        
        self.logger.info(f"Transforming 3D model using {method} method")
        
        # Get electrode positions as array
        electrode_points = np.array([
            [e.get('x', 0), e.get('y', 0), e.get('z', 0)]
            for e in electrodes
        ])
        
        # Get model vertices
        vertices = np.array(model_data.get('vertices', []))
        
        if len(vertices) == 0:
            self.logger.error("No vertices in 3D model")
            return model_data
        
        # Choose alignment method
        if method == 'auto':
            # Automatically choose based on data characteristics
            if len(electrode_points) < 10:
                method = 'bounding_box'
            elif len(electrode_points) < 100:
                method = 'procrustes'
            else:
                method = 'icp'
        
        # Apply transformation
        if method == 'bounding_box':
            transformed_vertices = self._align_bounding_box(vertices, electrode_points)
        elif method == 'procrustes':
            transformed_vertices = self._align_procrustes(vertices, electrode_points)
        elif method == 'icp':
            transformed_vertices = self._align_icp(vertices, electrode_points)
        else:
            self.logger.warning(f"Unknown alignment method: {method}")
            transformed_vertices = vertices
        
        # Update model data
        model_data['vertices'] = transformed_vertices.tolist()
        
        # Update faces if vertex order changed
        if 'faces' in model_data:
            model_data['faces'] = self._validate_faces(
                model_data['faces'],
                len(transformed_vertices)
            )
        
        # Recalculate bounds
        model_data['bounds'] = {
            'min': transformed_vertices.min(axis=0).tolist(),
            'max': transformed_vertices.max(axis=0).tolist(),
        }
        
        # Add transformation metadata
        model_data['transformation'] = {
            'method': method,
            'electrode_count': len(electrode_points),
            'vertex_count': len(transformed_vertices),
        }
        
        return model_data
    
    def _align_bounding_box(
        self,
        vertices: np.ndarray,
        electrode_points: np.ndarray
    ) -> np.ndarray:
        """
        Align model using bounding box matching.
        
        Args:
            vertices: Model vertices
            electrode_points: Electrode positions
            
        Returns:
            Aligned vertices
        """
        # Calculate bounding boxes
        model_min = vertices.min(axis=0)
        model_max = vertices.max(axis=0)
        model_center = (model_min + model_max) / 2
        model_size = model_max - model_min
        
        electrode_min = electrode_points.min(axis=0)
        electrode_max = electrode_points.max(axis=0)
        electrode_center = (electrode_min + electrode_max) / 2
        electrode_size = electrode_max - electrode_min
        
        # Calculate scale factors
        scale_factors = np.where(
            model_size > 0,
            electrode_size / model_size,
            1.0
        )
        
        # Use uniform scaling (median of non-zero factors)
        valid_scales = scale_factors[scale_factors > 0]
        if len(valid_scales) > 0:
            uniform_scale = np.median(valid_scales)
        else:
            uniform_scale = 1.0
        
        # Apply transformation
        vertices_centered = vertices - model_center
        vertices_scaled = vertices_centered * uniform_scale
        vertices_aligned = vertices_scaled + electrode_center
        
        self.logger.info(f"Bounding box alignment: scale={uniform_scale:.3f}")
        
        return vertices_aligned
    
    def _align_procrustes(
        self,
        vertices: np.ndarray,
        electrode_points: np.ndarray,
        n_samples: int = 100
    ) -> np.ndarray:
        """
        Align model using Procrustes analysis.
        
        Args:
            vertices: Model vertices
            electrode_points: Electrode positions
            n_samples: Number of model points to sample
            
        Returns:
            Aligned vertices
        """
        # Sample points from model surface
        if len(vertices) > n_samples:
            # Random sampling
            sample_indices = np.random.choice(len(vertices), n_samples, replace=False)
            model_samples = vertices[sample_indices]
        else:
            model_samples = vertices
        
        # Find closest model points to electrodes
        distances = distance_matrix(electrode_points, model_samples)
        closest_indices = distances.argmin(axis=1)
        closest_points = model_samples[closest_indices]
        
        # Procrustes analysis
        _, transformed_points, disparity = procrustes(electrode_points, closest_points)
        
        # Calculate transformation matrix
        # Center both point sets
        electrode_centered = electrode_points - electrode_points.mean(axis=0)
        closest_centered = closest_points - closest_points.mean(axis=0)
        
        # Compute optimal rotation
        H = closest_centered.T @ electrode_centered
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # Ensure proper rotation (det(R) = 1)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        
        # Compute scale
        scale = np.trace(R @ H) / np.trace(closest_centered.T @ closest_centered)
        
        # Compute translation
        translation = electrode_points.mean(axis=0) - scale * R @ closest_points.mean(axis=0)
        
        # Apply transformation to all vertices
        vertices_transformed = scale * (vertices @ R.T) + translation
        
        self.logger.info(f"Procrustes alignment: scale={scale:.3f}, disparity={disparity:.3f}")
        
        return vertices_transformed
    
    def _align_icp(
        self,
        vertices: np.ndarray,
        electrode_points: np.ndarray,
        max_iterations: int = 50,
        tolerance: float = 1e-5
    ) -> np.ndarray:
        """
        Align model using Iterative Closest Point (ICP) algorithm.
        
        Args:
            vertices: Model vertices
            electrode_points: Electrode positions
            max_iterations: Maximum ICP iterations
            tolerance: Convergence tolerance
            
        Returns:
            Aligned vertices
        """
        # Initialize transformation
        R = np.eye(3)  # Rotation matrix
        t = np.zeros(3)  # Translation vector
        s = 1.0  # Scale factor
        
        vertices_transformed = vertices.copy()
        prev_error = float('inf')
        
        for iteration in range(max_iterations):
            # Find closest points
            distances = distance_matrix(electrode_points, vertices_transformed)
            closest_indices = distances.argmin(axis=1)
            closest_points = vertices_transformed[closest_indices]
            
            # Calculate error
            error = np.mean(distances.min(axis=1))
            
            # Check convergence
            if abs(prev_error - error) < tolerance:
                self.logger.info(f"ICP converged after {iteration} iterations")
                break
            prev_error = error
            
            # Calculate optimal transformation
            # Center both point sets
            electrode_centered = electrode_points - electrode_points.mean(axis=0)
            closest_centered = closest_points - closest_points.mean(axis=0)
            
            # Compute rotation
            H = closest_centered.T @ electrode_centered
            U, _, Vt = np.linalg.svd(H)
            R_iter = Vt.T @ U.T
            
            if np.linalg.det(R_iter) < 0:
                Vt[-1, :] *= -1
                R_iter = Vt.T @ U.T
            
            # Compute scale
            s_iter = np.trace(R_iter @ H) / np.trace(closest_centered.T @ closest_centered)
            
            # Compute translation
            t_iter = electrode_points.mean(axis=0) - s_iter * R_iter @ closest_points.mean(axis=0)
            
            # Apply transformation
            vertices_transformed = s_iter * (vertices_transformed @ R_iter.T) + t_iter
            
            # Accumulate transformation
            R = R_iter @ R
            t = s_iter * R_iter @ t + t_iter
            s = s_iter * s
        
        self.logger.info(f"ICP alignment: final error={error:.3f}, scale={s:.3f}")
        
        return vertices_transformed
    
    def extract_probe_outline(
        self,
        model_data: Dict[str, Any],
        projection: str = 'xy',
        simplify: bool = True
    ) -> List[List[float]]:
        """
        Extract 2D outline of probe from 3D model.
        
        Args:
            model_data: 3D model data
            projection: Projection plane ('xy', 'xz', 'yz')
            simplify: Whether to simplify the outline
            
        Returns:
            List of 2D points forming the outline
        """
        vertices = np.array(model_data.get('vertices', []))
        
        if len(vertices) == 0:
            return []
        
        # Project to 2D
        if projection == 'xy':
            points_2d = vertices[:, :2]
        elif projection == 'xz':
            points_2d = vertices[:, [0, 2]]
        elif projection == 'yz':
            points_2d = vertices[:, [1, 2]]
        else:
            raise ValueError(f"Invalid projection: {projection}")
        
        # Find convex hull
        from scipy.spatial import ConvexHull
        
        try:
            hull = ConvexHull(points_2d)
            outline = points_2d[hull.vertices]
        except:
            # Fallback to bounding box
            min_pt = points_2d.min(axis=0)
            max_pt = points_2d.max(axis=0)
            outline = np.array([
                [min_pt[0], min_pt[1]],
                [max_pt[0], min_pt[1]],
                [max_pt[0], max_pt[1]],
                [min_pt[0], max_pt[1]],
            ])
        
        # Simplify outline if requested
        if simplify and len(outline) > 20:
            outline = self._simplify_polygon(outline, tolerance=1.0)
        
        # Close the polygon
        outline = np.vstack([outline, outline[0]])
        
        return outline.tolist()
    
    def _simplify_polygon(
        self,
        points: np.ndarray,
        tolerance: float = 1.0
    ) -> np.ndarray:
        """
        Simplify polygon using Douglas-Peucker algorithm.
        
        Args:
            points: 2D points forming polygon
            tolerance: Simplification tolerance
            
        Returns:
            Simplified polygon points
        """
        from shapely.geometry import Polygon
        from shapely.geometry import LineString
        
        try:
            # Create polygon or line
            if len(points) > 2:
                poly = Polygon(points)
                simplified = poly.simplify(tolerance)
                return np.array(simplified.exterior.coords[:-1])
            else:
                return points
        except:
            # Fallback to no simplification
            return points
    
    def calculate_electrode_projection(
        self,
        electrodes: List[Dict[str, Any]],
        model_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Project electrodes onto 3D model surface.
        
        Args:
            electrodes: Electrode positions
            model_data: 3D model data
            
        Returns:
            Electrodes with surface projection data
        """
        if 'vertices' not in model_data or 'faces' not in model_data:
            return electrodes
        
        vertices = np.array(model_data['vertices'])
        faces = np.array(model_data['faces'])
        
        projected_electrodes = []
        
        for electrode in electrodes:
            point = np.array([
                electrode.get('x', 0),
                electrode.get('y', 0),
                electrode.get('z', 0)
            ])
            
            # Find closest point on surface
            closest_vertex_idx = np.argmin(np.linalg.norm(vertices - point, axis=1))
            closest_point = vertices[closest_vertex_idx]
            
            # Calculate projection distance
            distance = np.linalg.norm(point - closest_point)
            
            # Update electrode with projection info
            projected = electrode.copy()
            projected['surface_projection'] = {
                'x': float(closest_point[0]),
                'y': float(closest_point[1]),
                'z': float(closest_point[2]),
                'distance': float(distance),
                'vertex_index': int(closest_vertex_idx),
            }
            
            projected_electrodes.append(projected)
        
        return projected_electrodes
    
    def _validate_faces(
        self,
        faces: List[List[int]],
        n_vertices: int
    ) -> List[List[int]]:
        """
        Validate and fix face indices.
        
        Args:
            faces: Face index list
            n_vertices: Number of vertices
            
        Returns:
            Validated faces
        """
        validated_faces = []
        
        for face in faces:
            # Check if all indices are valid
            if all(0 <= idx < n_vertices for idx in face):
                validated_faces.append(face)
            else:
                self.logger.warning(f"Invalid face indices: {face}")
        
        return validated_faces
    
    def fit_parametric_model(
        self,
        electrodes: List[Dict[str, Any]],
        model_type: str = 'linear_array'
    ) -> Dict[str, Any]:
        """
        Fit a parametric model to electrode positions.
        
        Args:
            electrodes: Electrode positions
            model_type: Type of parametric model
            
        Returns:
            Fitted model parameters
        """
        if not electrodes:
            return {}
        
        points = np.array([
            [e.get('x', 0), e.get('y', 0), e.get('z', 0)]
            for e in electrodes
        ])
        
        if model_type == 'linear_array':
            # Fit a line to electrodes
            center = points.mean(axis=0)
            _, _, vh = np.linalg.svd(points - center)
            direction = vh[0]
            
            # Project points onto line
            projections = []
            for point in points:
                t = np.dot(point - center, direction)
                proj = center + t * direction
                projections.append(proj)
            
            projections = np.array(projections)
            
            # Calculate spacing
            distances = np.linalg.norm(np.diff(projections, axis=0), axis=1)
            spacing = np.median(distances) if len(distances) > 0 else 0
            
            model_params = {
                'type': 'linear_array',
                'center': center.tolist(),
                'direction': direction.tolist(),
                'spacing': float(spacing),
                'length': float(np.linalg.norm(projections[-1] - projections[0])),
                'fit_error': float(np.mean(np.linalg.norm(points - projections, axis=1))),
            }
            
        elif model_type == 'grid':
            # Fit a 2D grid to electrodes
            # (Simplified - assumes aligned grid)
            x_unique = np.unique(points[:, 0])
            y_unique = np.unique(points[:, 1])
            
            model_params = {
                'type': 'grid',
                'rows': len(y_unique),
                'columns': len(x_unique),
                'row_spacing': float(np.median(np.diff(y_unique))) if len(y_unique) > 1 else 0,
                'column_spacing': float(np.median(np.diff(x_unique))) if len(x_unique) > 1 else 0,
            }
        
        else:
            model_params = {'type': 'unknown'}
        
        return model_params
