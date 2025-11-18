import numpy as np, slicer, vtk, math, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import unit, ensure_normals  # type: ignore
except Exception:
    from utils import unit, ensure_normals  # type: ignore

# Preferred MSP plane names (checked in order). Include the plane created by this module by default.
MSP_PREF_NAMES = ['SymmetryPlane','MSP_S_L2','MSP_CR_SNBa','MSP_SNMe','MSP']

class GonionLogic:
    def __init__(self, alpha_deg=127.0, ratio=2.0):
        self.alpha_deg = alpha_deg
        self.ratio = ratio
        self.dist_tol_mm = 0.35
        self.z_limit_mm = 6.0

    def find_point_any(self, syns):
        want={s.lower().replace(' ','').replace('_','') for s in syns}
        for node in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            for i in range(node.GetNumberOfControlPoints()):
                lb=node.GetNthControlPointLabel(i).lower().replace(' ','').replace('_','')
                if lb in want:
                    p=[0,0,0]; node.GetNthControlPointPositionWorld(i,p); return np.array(p,float)
        return None

    def get_msp_O_N(self):
        for name in MSP_PREF_NAMES:
            try:
                pl=slicer.util.getNode(name)
                O=[0,0,0]; N=[0,0,1]
                if hasattr(pl,'GetOriginWorld'): pl.GetOriginWorld(O)
                if hasattr(pl,'GetNormalWorld'): pl.GetNormalWorld(N)
                N=np.array(N,float); ln=np.linalg.norm(N)
                if ln<1e-9: continue
                return np.array(O,float), N/ln, name
            except slicer.util.MRMLNodeNotFoundException:
                pass
        for pl in slicer.util.getNodesByClass('vtkMRMLMarkupsPlaneNode'):
            if 'msp' in (pl.GetName() or '').lower():
                O=[0,0,0]; N=[0,0,1]
                if hasattr(pl,'GetOriginWorld'): pl.GetOriginWorld(O)
                if hasattr(pl,'GetNormalWorld'): pl.GetNormalWorld(N)
                N=np.array(N,float); ln=np.linalg.norm(N)
                if ln<1e-9: continue
                return np.array(O,float), N/ln, pl.GetName()
        raise RuntimeError('MSP plane not found')

    def pca_up(self, surface_pd, center, r_mm=25.0):
        kd=vtk.vtkPointLocator(); kd.SetDataSet(surface_pd); kd.BuildLocator()
        ids=vtk.vtkIdList(); kd.FindPointsWithinRadius(r_mm, center.tolist(), ids)
        if ids.GetNumberOfIds()<20: return np.array([0,0,1.0])
        pts=surface_pd.GetPoints(); A=np.empty((ids.GetNumberOfIds(),3),float)
        for k in range(ids.GetNumberOfIds()): A[k]=pts.GetPoint(ids.GetId(k))
        C=A.mean(axis=0); X=A-C; cov=np.cov(X.T); w,V=np.linalg.eigh(cov)
        iz=int(np.argsort(w)[-1]); vz=V[:,iz]/np.linalg.norm(V[:,iz])
        if np.dot(vz,np.array([0,0,1.0]))<0: vz=-vz
        return vz

    def pick_goN_outer(self, Me, Co, mand_pd, O_msp, N_msp, side_label='R', Go_hint=None):
        Y = float(np.linalg.norm(Co - Me))
        denom = 1.0 + self.ratio*self.ratio - 2.0*self.ratio*math.cos(math.radians(self.alpha_deg))
        if denom<=1e-12: raise RuntimeError(f'[{side_label}] denominator invalid (alpha?)')
        d = Y / math.sqrt(denom)
        L = self.ratio * d
        u = unit(Me - Co)
        a = (d*d - L*L + Y*Y) / (2.0*Y)
        P0 = Co + a*u
        plane=vtk.vtkPlane(); plane.SetOrigin(*P0.tolist()); plane.SetNormal(*u.tolist())
        cutter=vtk.vtkCutter(); cutter.SetInputData(mand_pd); cutter.SetCutFunction(plane); cutter.Update()
        stripper=vtk.vtkStripper(); stripper.SetInputConnection(cutter.GetOutputPort()); stripper.Update()
        curvePD = stripper.GetOutput(); Pts = curvePD.GetPoints()
        if not Pts or Pts.GetNumberOfPoints()==0:
            raise RuntimeError(f'[{side_label}] cutting plane does not intersect mandible')
        curveP = np.array([Pts.GetPoint(i) for i in range(Pts.GetNumberOfPoints())])
        dCo = np.linalg.norm(curveP - Co, axis=1)
        dMe = np.linalg.norm(curveP - Me, axis=1)
        err = np.maximum(np.abs(dCo - d), np.abs(dMe - L))
        mask = err <= self.dist_tol_mm
        if not np.any(mask):
            mask = np.zeros_like(err,dtype=bool); mask[np.argmin(err)]=True
        cand = curveP[mask]; errc = err[mask]
        s_val = (cand - O_msp) @ N_msp
        side_sign = +1.0 if side_label.upper().startswith('R') else -1.0
        mask_side = (s_val*side_sign) > 0
        if np.any(mask_side):
            cand=cand[mask_side]; errc=errc[mask_side]; s_val=s_val[mask_side]
        if Go_hint is not None:
            vz_up = self.pca_up(mand_pd, Go_hint)
            rise = np.maximum(0.0,(cand-Go_hint)@vz_up)
        else:
            cen = cand.mean(axis=0); vz_up = self.pca_up(mand_pd, cen)
            rise = np.maximum(0.0,(cand-cen)@vz_up)
        score = 5.0*np.abs(s_val) - 1.0*np.maximum(0.0, rise - self.z_limit_mm) - 1.5*errc
        return cand[int(np.argmax(score))]

    def set_fiducial(self, name, pt, label=None):
        try:
            n=slicer.util.getNode(name)
            if not isinstance(n, slicer.vtkMRMLMarkupsFiducialNode): raise slicer.util.MRMLNodeNotFoundException()
        except slicer.util.MRMLNodeNotFoundException:
            n=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', name); n.CreateDefaultDisplayNodes()
        n.RemoveAllControlPoints(); n.AddControlPointWorld(pt.tolist())
        if label: n.SetNthControlPointLabel(0,label)
        return n

    def set_angle(self, name, A, B, C):
        try:
            ang=slicer.util.getNode(name)
            if not isinstance(ang, slicer.vtkMRMLMarkupsAngleNode): raise slicer.util.MRMLNodeNotFoundException()
        except slicer.util.MRMLNodeNotFoundException:
            ang=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsAngleNode', name); ang.CreateDefaultDisplayNodes()
        ang.RemoveAllControlPoints(); ang.AddControlPointWorld(A.tolist()); ang.AddControlPointWorld(B.tolist()); ang.AddControlPointWorld(C.tolist())
        return ang
