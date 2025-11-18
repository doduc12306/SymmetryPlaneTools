import numpy as np, slicer, vtk, math, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_normals, unit, ensure_unique_name  # type: ignore
except Exception:
    from utils import ensure_normals, unit, ensure_unique_name  # type: ignore
try:
    from SymmetryPlaneFromPoints.logic.gonion import MSP_PREF_NAMES  # type: ignore
except Exception:
    from gonion import MSP_PREF_NAMES  # type: ignore

class SheetLogic:
    def __init__(self, samples=420):
        self.samples = samples

    def resample_cardinal(self, P, samples=None):
        if samples is None: samples = self.samples
        xs=vtk.vtkCardinalSpline(); ys=vtk.vtkCardinalSpline(); zs=vtk.vtkCardinalSpline()
        N=len(P)
        for i,(x,y,z) in enumerate(P): xs.AddPoint(i,x); ys.AddPoint(i,y); zs.AddPoint(i,z)
        M=max(samples,N); out=np.zeros((M,3),float)
        for j in range(M):
            t=j*(N-1)/float(max(M-1,1)); out[j]=[xs.Evaluate(t),ys.Evaluate(t),zs.Evaluate(t)]
        return out

    def tangents(self, P):
        T=np.zeros_like(P)
        for i in range(len(P)):
            if i==0: v=P[1]-P[0]
            elif i==len(P)-1: v=P[-1]-P[-2]
            else: v=P[i+1]-P[i-1]
            T[i]=unit(v)
        return T

    def extend_polyline(self, P, ext_mm=10.0):
        T=self.tangents(P)
        head=P[0]-T[0]*ext_mm; tail=P[-1]+T[-1]*ext_mm
        return np.vstack([head,P,tail])

    def bishop_frame_outward(self, P, O_msp, N_msp, up_axis=np.array([0,0,1.0],float)):
        T=self.tangents(P)
        U=np.zeros_like(T); V=np.zeros_like(T)
        for i in range(len(P)):
            d_side=np.sign(np.dot(P[i]-O_msp,N_msp)); L=d_side*N_msp
            U_lat=L - T[i]*np.dot(L,T[i])
            if np.linalg.norm(U_lat)<1e-8: U_lat=np.cross(up_axis,T[i])
            U[i]=unit(U_lat); V[i]=unit(np.cross(T[i],U[i]))
            if np.dot(V[i],up_axis)<0: V[i]=-V[i]
        return U,V,T

    def get_msp(self):
        for name in MSP_PREF_NAMES:
            try:
                pl=slicer.util.getNode(name)
                o=[0,0,0]; n=[0,0,1]
                if hasattr(pl,'GetOriginWorld'): pl.GetOriginWorld(o)
                if hasattr(pl,'GetNormalWorld'): pl.GetNormalWorld(n)
                n=np.array(n,float); ln=np.linalg.norm(n)
                if ln>1e-8: return np.array(o,float), n/ln, pl.GetName()
            except slicer.util.MRMLNodeNotFoundException:
                pass
        for pl in slicer.util.getNodesByClass('vtkMRMLMarkupsPlaneNode'):
            if 'msp' in (pl.GetName() or '').lower():
                o=[0,0,0]; n=[0,0,1]
                if hasattr(pl,'GetOriginWorld'): pl.GetOriginWorld(o)
                if hasattr(pl,'GetNormalWorld'): pl.GetNormalWorld(n)
                n=np.array(n,float); ln=np.linalg.norm(n)
                if ln>1e-8: return np.array(o,float), n/ln, pl.GetName()
        return np.array([0,0,0],float), np.array([1,0,0],float), 'MSP_fallback_X'

    def build_sheet(self, curveNode, yaw_deg=45.0, lat_mm=5.0, med_mm=15.0, extend_mm=10.0, baseName='Sheet_MOL'):
        if curveNode.GetNumberOfControlPoints()<2:
            raise RuntimeError('Curve requires >=2 points')
        P0=np.array([curveNode.GetNthControlPointPositionWorld(i) for i in range(curveNode.GetNumberOfControlPoints())])
        P=self.resample_cardinal(P0,self.samples)
        P=self.extend_polyline(P,extend_mm)
        O_msp,N_msp,msp_name=self.get_msp()
        U_lat,V_up,T=self.bishop_frame_outward(P,O_msp,N_msp)
        yaw=math.radians(yaw_deg); Uo=np.cos(yaw)*U_lat + np.sin(yaw)*V_up
        name=f"{baseName}_yaw_{yaw_deg}_out{lat_mm}p_in{med_mm}".replace('.','p')
        m=self._build_sheet_asym(P,Uo,lat_mm,med_mm,name)
        logging.info(f"Built sheet {name} yaw={yaw_deg} lat={lat_mm} med={med_mm} extend={extend_mm} samples={self.samples}")
        return m, (O_msp,N_msp,msp_name)

    def _build_sheet_asym(self, P,Uo,lat_mm,med_mm,name,color=(1.0,0.85,0.0),op=0.95):
        N=len(P); pts=vtk.vtkPoints(); polys=vtk.vtkCellArray()
        for p in (P+Uo*lat_mm): pts.InsertNextPoint(*p.tolist())
        for p in (P-Uo*med_mm): pts.InsertNextPoint(*p.tolist())
        def tri(a,b,c):
            t=vtk.vtkTriangle(); t.GetPointIds().SetId(0,a); t.GetPointIds().SetId(1,b); t.GetPointIds().SetId(2,c); polys.InsertNextCell(t)
        for i in range(N-1): tri(i,i+N,i+1+N); tri(i,i+1+N,i+1)
        pd=vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(polys); pd=ensure_normals(pd)
        try: slicer.mrmlScene.RemoveNode(slicer.util.getNode(name))
        except: pass
        m=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode',name)
        m.CreateDefaultDisplayNodes(); m.SetAndObservePolyData(pd)
        d=m.GetDisplayNode();
        if d: d.SetOpacity(op); d.SetVisibility(1); d.SetBackfaceCulling(0)
        return m

    def mirror_model(self, srcNode, origin, normal):
        poly=srcNode.GetPolyData();
        if not poly or poly.GetNumberOfPoints()==0: raise RuntimeError('Source model empty')
        newPoly=vtk.vtkPolyData(); newPoly.DeepCopy(poly)
        dstName=ensure_unique_name(srcNode.GetName() + '_Rmirror')
        dst=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode',dstName)
        dst.CreateDefaultDisplayNodes(); dst.SetAndObservePolyData(newPoly)
        try:
            from SymmetryPlaneFromPoints.logic.utils import reflection_matrix, apply_and_harden  # type: ignore
        except Exception:
            from utils import reflection_matrix, apply_and_harden  # type: ignore
        M=reflection_matrix(origin, normal)
        apply_and_harden(dst,M,'Xform_Mirror_MSP')
        d=dst.GetDisplayNode();
        if d: d.SetVisibility(True); d.SetBackfaceCulling(0)
        logging.info(f"Mirrored {srcNode.GetName()} -> {dstName}")
        return dst
