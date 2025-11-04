import vtk
import slicer
import numpy as np
import logging

class SymmetryPlaneLogic:
    """
    Logic class for creating symmetry planes from fiducial points.
    """
    
    def __init__(self):
        # Kích thước mặt phẳng hình chữ nhật (mm)
        self.planeWidth = 200.0   # Chiều rộng (ngang) - 300mm
        self.planeHeight = 200.0  # Chiều dài (dọc) - 500mm
        self.planeColor = [0.3, 0.6, 1.0]  # Light blue color
        self.planeOpacity = 0.4
    
    def createPlaneFrom3Points(self, fiducialNode):
        """
        Create an exact plane passing through 3 points.
        The normal vector is calculated using cross product v1 × v2.
        
        Args:
            fiducialNode: vtkMRMLMarkupsFiducialNode with exactly 3 points
            
        Returns:
            vtkMRMLModelNode: The created plane model
        """
        if fiducialNode.GetNumberOfControlPoints() != 3:
            logging.error("createPlaneFrom3Points requires exactly 3 points")
            return None
        
        # Get the three points (WORLD/RAS coordinates for robustness)
        p0w = [0.0, 0.0, 0.0]
        p1w = [0.0, 0.0, 0.0]
        p2w = [0.0, 0.0, 0.0]
        fiducialNode.GetNthControlPointPositionWorld(0, p0w)
        fiducialNode.GetNthControlPointPositionWorld(1, p1w)
        fiducialNode.GetNthControlPointPositionWorld(2, p2w)
        p0 = np.array(p0w)
        p1 = np.array(p1w)
        p2 = np.array(p2w)
        
        # Calculate vectors
        v1 = p1 - p0
        v2 = p2 - p0
        
        # Calculate normal vector using cross product
        normal = np.cross(v1, v2)
        normal_length = np.linalg.norm(normal)
        
        if normal_length < 1e-6:
            logging.error("Points are collinear, cannot create a plane")
            return None
        
        # Normalize the normal vector
        normal = normal / normal_length
        
        # Calculate the center point (centroid of the 3 points)
        center = (p0 + p1 + p2) / 3.0
        
        # Print information to Python Interactor
        print("\n=== Symmetry Plane Created from 3 Points ===")
        print(f"Point 0: {p0}")
        print(f"Point 1: {p1}")
        print(f"Point 2: {p2}")
        print(f"Plane Center: {center}")
        print(f"Plane Normal: {normal}")
        print(f"Normal vector calculated using cross product v1 × v2")
        print("=" * 45 + "\n")
        
        # Create the plane model
        return self._createPlaneModel(center, normal, "SymmetryPlane")
    
    def createPlaneFrom4Points(self, fiducialNode):
        """
        Create a best-fit plane through 4 points using PCA/SVD.
        
        Args:
            fiducialNode: vtkMRMLMarkupsFiducialNode with exactly 4 points
            
        Returns:
            vtkMRMLModelNode: The created plane model
        """
        if fiducialNode.GetNumberOfControlPoints() != 4:
            logging.error("createPlaneFrom4Points requires exactly 4 points")
            return None
        
        # Get all four points (WORLD/RAS coordinates)
        pts = []
        for i in range(4):
            pw = [0.0, 0.0, 0.0]
            fiducialNode.GetNthControlPointPositionWorld(i, pw)
            pts.append(pw)
        points = np.array(pts)
        
        # Calculate centroid
        center = np.mean(points, axis=0)
        
        # Center the points
        centered_points = points - center
        
        # Perform SVD (Principal Component Analysis)
        # The columns of U are the principal components
        # The last column corresponds to the smallest singular value
        # and represents the normal to the best-fit plane
        U, S, Vt = np.linalg.svd(centered_points.T)
        
        # The normal is the last column of U (corresponding to smallest singular value)
        normal = U[:, -1]
        
        # Ensure consistent orientation (pointing in positive Z direction if possible)
        if normal[2] < 0:
            normal = -normal
        
        # Calculate fitting error (sum of squared distances to plane)
        distances = np.abs(np.dot(centered_points, normal))
        fitting_error = np.sum(distances**2)
        rms_error = np.sqrt(np.mean(distances**2))
        
        # Print information to Python Interactor
        print("\n=== Symmetry Plane Created from 4 Points (PCA/SVD) ===")
        for i, p in enumerate(points):
            print(f"Point {i}: {p}")
        print(f"Plane Center (Centroid): {center}")
        print(f"Plane Normal: {normal}")
        print(f"Singular Values: {S}")
        print(f"RMS Fitting Error: {rms_error:.4f} mm")
        print(f"Individual distances to plane:")
        for i, d in enumerate(distances):
            print(f"  Point {i}: {d:.4f} mm")
        print("=" * 55 + "\n")
        
        # Create the plane model
        return self._createPlaneModel(center, normal, "SymmetryPlane")
    
    def _createPlaneModel(self, center, normal, modelName):
        """
        Create a Markups Plane node (theo code mẫu).
        
        Args:
            center: numpy array [x, y, z] - center point of the plane
            normal: numpy array [nx, ny, nz] - normal vector of the plane
            modelName: str - name for the plane node
            
        Returns:
            vtkMRMLMarkupsPlaneNode: The created plane node
        """
        # Ensure unique name
        name = modelName
        i = 1
        while slicer.mrmlScene.GetFirstNodeByName(name) is not None:
            i += 1
            name = f"{modelName}_{i}"
        
        print(f"\n=== Creating Markups Plane ===")
        print(f"Name: {name}")
        print(f"Origin (center): {center}")
        print(f"Normal: {normal}")
        print(f"Size: {self.planeWidth} x {self.planeHeight} mm")
        
        # Create Markups Plane Node
        planeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode', name)
        
        # Set origin and normal in WORLD coordinates
        planeNode.SetOriginWorld(center.tolist())
        planeNode.SetNormalWorld(normal.tolist())
        
        # Set size (absolute mode)
        try:
            planeNode.SetSizeMode(planeNode.SizeModeAbsolute)
            # Prefer API compatible with Slicer 5.x: SetSizeMm(w, h)
            planeNode.SetSizeMm(float(self.planeWidth), float(self.planeHeight))
            print(f"✓ Set size using SetSizeMm: {self.planeWidth} x {self.planeHeight} mm")
        except Exception as e:
            print(f"SetSizeMm failed: {e}, trying SetPlaneBounds...")
            # Fallback for older Slicer versions
            half_w = self.planeWidth * 0.5
            half_h = self.planeHeight * 0.5
            try:
                planeNode.SetPlaneBounds(-half_w, half_w, -half_h, half_h)
                print(f"✓ Set size using SetPlaneBounds: ±{half_w} x ±{half_h} mm")
            except Exception as e2:
                print(f"SetPlaneBounds also failed: {e2}")
        
        # Debug: report resulting size from node API
        try:
            # Some versions expose GetSizeMm, others GetPlaneBounds only
            sizeMm = [0.0, 0.0]
            if hasattr(planeNode, 'GetSizeMm'):
                sizeMm = list(planeNode.GetSizeMm())
                print(f"→ Reported size (GetSizeMm): {sizeMm}")
            else:
                bounds = [0.0, 0.0, 0.0, 0.0]
                planeNode.GetPlaneBounds(bounds)
                print(f"→ Reported bounds (GetPlaneBounds): x=({bounds[0]}, {bounds[1]}), y=({bounds[2]}, {bounds[3]})")
        except Exception as e:
            print(f"(debug) Could not query resulting size: {e}")

        # Set display properties
        disp = planeNode.GetDisplayNode()
        if disp:
            disp.SetOpacity(float(self.planeOpacity))
            disp.SetSelectedColor(*[float(c) for c in self.planeColor])
            disp.SetColor(*[float(c) for c in self.planeColor])
            # Prefer modern API: show on slice views
            if hasattr(disp, 'SetVisibility2D'):
                disp.SetVisibility2D(True)
            # Ensure 3D visibility as well
            if hasattr(disp, 'SetVisibility3D'):
                disp.SetVisibility3D(True)
            print(f"✓ Display: color={self.planeColor}, opacity={self.planeOpacity}")
        
        print("=" * 35 + "\n")
        
        return planeNode
