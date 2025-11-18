import numpy as np, slicer, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_unique_name  # type: ignore
except Exception:
    from utils import ensure_unique_name  # type: ignore

class PlaneLogic:
    def __init__(self, width=200.0, height=200.0, color=(0.3,0.6,1.0), opacity=0.4):
        self.width = width
        self.height = height
        self.color = color
        self.opacity = opacity

    def create_from_3_points(self, p0, p1, p2, name='SymmetryPlane_3pt'):
        v1 = p1 - p0; v2 = p2 - p0
        normal = np.cross(v1, v2)
        ln = np.linalg.norm(normal)
        if ln < 1e-6:
            raise ValueError('Three points are collinear; cannot form plane')
        normal /= ln
        center = (p0 + p1 + p2)/3.0
        return self._create_markups_plane(center, normal, name)

    def create_best_fit(self, points, name='SymmetryPlane_4pt_PCA'):
        if len(points) != 4:
            raise ValueError('Need exactly 4 points for best-fit plane')
        pts = np.asarray(points,float)
        center = pts.mean(axis=0)
        X = pts - center
        U,S,Vt = np.linalg.svd(X.T)
        normal = U[:,-1]
        if normal[2] < 0: normal = -normal
        return self._create_markups_plane(center, normal, name)

    def _create_markups_plane(self, center, normal, baseName):
        name = ensure_unique_name(baseName)
        planeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode', name)
        planeNode.SetOriginWorld(center.tolist())
        planeNode.SetNormalWorld(normal.tolist())
        try:
            planeNode.SetSizeMode(planeNode.SizeModeAbsolute)
            planeNode.SetSizeMm(float(self.width), float(self.height))
        except Exception:
            half_w = self.width*0.5; half_h = self.height*0.5
            try: planeNode.SetPlaneBounds(-half_w, half_w, -half_h, half_h)
            except Exception: pass
        disp = planeNode.GetDisplayNode()
        if disp:
            disp.SetOpacity(float(self.opacity))
            disp.SetSelectedColor(*self.color)
            disp.SetColor(*self.color)
            if hasattr(disp,'SetVisibility2D'): disp.SetVisibility2D(True)
            if hasattr(disp,'SetVisibility3D'): disp.SetVisibility3D(True)
        logging.info(f"Created plane '{name}' center={center} normal={normal}")
        return planeNode
