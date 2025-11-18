import numpy as np, slicer, vtk, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_normals, tri_clean, surface_area, upsert_model  # type: ignore
except Exception:
    from utils import ensure_normals, tri_clean, surface_area, upsert_model  # type: ignore

class GuideLogic:
    def __init__(self, gap_mm=0.35, thick_mm=2.2, expand_mm=3.0, vox_mm=0.35, pad_mm=6.0):
        self.gap = gap_mm
        self.thick = thick_mm
        self.expand = expand_mm
        self.vox = vox_mm
        self.pad = pad_mm
        self.cut_strip = 0.5

    def _get_poly(self, name):
        node = slicer.util.getNode(name)
        pd = node.GetPolyData()
        if not pd or pd.GetNumberOfPoints()==0:
            raise RuntimeError(f'PolyData empty: {name}')
        return ensure_normals(pd)

    def _make_shell(self, bone_pd):
        imp = vtk.vtkImplicitPolyDataDistance(); imp.SetInput(bone_pd)
        b = list(bone_pd.GetBounds()); P = self.gap+self.thick+self.pad
        bounds = [b[0]-P,b[1]+P,b[2]-P,b[3]+P,b[4]-P,b[5]+P]
        dims = [max(2,int((bounds[1]-bounds[0])/self.vox)+1),
                max(2,int((bounds[3]-bounds[2])/self.vox)+1),
                max(2,int((bounds[5]-bounds[4])/self.vox)+1)]
        samp = vtk.vtkSampleFunction(); samp.SetImplicitFunction(imp); samp.SetModelBounds(bounds)
        samp.SetSampleDimensions(dims); samp.SetOutputScalarTypeToFloat(); samp.ComputeNormalsOff(); samp.Update()
        thr = vtk.vtkImageThreshold(); thr.SetInputConnection(samp.GetOutputPort())
        thr.ThresholdBetween(self.gap, self.gap+self.thick); thr.SetInValue(1); thr.SetOutValue(0); thr.SetOutputScalarTypeToUnsignedChar(); thr.Update()
        mc = vtk.vtkMarchingCubes(); mc.SetInputConnection(thr.GetOutputPort()); mc.SetValue(0,0.5); mc.Update()
        ws = vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(mc.GetOutput())
        ws.SetNumberOfIterations(30); ws.BoundarySmoothingOn(); ws.FeatureEdgeSmoothingOff(); ws.NonManifoldSmoothingOn(); ws.NormalizeCoordinatesOn(); ws.SetPassBand(0.03); ws.Update()
        return tri_clean(ws.GetOutput())

    def _compute_point_values(self, pd, imp):
        P=pd.GetPoints(); N=P.GetNumberOfPoints(); q=[0,0,0]
        vals=np.empty(N,float)
        for i in range(N): P.GetPoint(i,q); vals[i]=float(imp.EvaluateFunction(q))
        return vals

    def _clip_scalar(self, poly, scalars, thresh, keep_ge=True):
        pd = vtk.vtkPolyData(); pd.DeepCopy(poly)
        arr = vtk.vtkDoubleArray(); arr.SetName('sc'); arr.SetNumberOfComponents(1); arr.SetNumberOfTuples(pd.GetNumberOfPoints())
        for i,v in enumerate(scalars): arr.SetValue(i, v)
        pd.GetPointData().SetScalars(arr)
        clip = vtk.vtkClipPolyData(); clip.SetInputData(pd); clip.SetValue(float(thresh))
        if keep_ge: clip.InsideOutOff()
        else: clip.InsideOutOn()
        clip.GenerateClippedOutputOff(); clip.Update()
        return tri_clean(clip.GetOutput())

    def _keep_largest_region(self, pd):
        if not pd or pd.GetNumberOfPoints()==0: return pd
        conn=vtk.vtkConnectivityFilter(); conn.SetInputData(pd); conn.SetExtractionModeToLargestRegion(); conn.Update()
        out=vtk.vtkPolyData(); out.DeepCopy(conn.GetOutput()); return out

    def build_side(self, bone_name, plane_name, out_name, imp_sheetA, imp_sheetB):
        bone_pd=self._get_poly(bone_name)
        shell_pd=self._make_shell(bone_pd)
        plane_pd=self._get_poly(plane_name)
        imp_plane=vtk.vtkImplicitPolyDataDistance(); imp_plane.SetInput(plane_pd)
        s=self._compute_point_values(shell_pd, imp_plane)
        side_pos=self._clip_scalar(shell_pd, s, 0.0, keep_ge=True)
        side_neg=self._clip_scalar(shell_pd, s, 0.0, keep_ge=False)
        pos_is_outer=(surface_area(side_pos) >= surface_area(side_neg))
        half_ext=self._clip_scalar(shell_pd, s, -self.expand if pos_is_outer else +self.expand, keep_ge=pos_is_outer)
        half_ext=self._keep_largest_region(half_ext)
        if not half_ext or half_ext.GetNumberOfPoints()==0: raise RuntimeError(f'[{bone_name}] Guide empty after outer-half selection')
        dA=np.abs(self._compute_point_values(half_ext, imp_sheetA))
        dB=np.abs(self._compute_point_values(half_ext, imp_sheetB))
        dMin=np.minimum(dA,dB)
        guide=self._clip_scalar(half_ext, dMin, self.cut_strip, keep_ge=True)
        guide=self._keep_largest_region(guide)
        if not guide or guide.GetNumberOfPoints()==0: raise RuntimeError(f'[{bone_name}] Guide empty after sheet proximity subtraction')
        upsert_model(out_name, guide, (1.0,0.85,0.0), 0.95)
        logging.info(f"Built {out_name}: clearance={self.gap} thick={self.thick} area~{surface_area(guide):.1f}")
        return True

    def create_guides(self, sheetA_name, sheetB_name, left_bone='bone_left', right_bone='bone_right', planeL='CurvedPlane_Left', planeR='CurvedPlane_Right', outL='Guide_L_outerWhole', outR='Guide_R_outerWhole'):
        sheetA_pd=self._get_poly(sheetA_name)
        sheetB_pd=self._get_poly(sheetB_name)
        impA=vtk.vtkImplicitPolyDataDistance(); impA.SetInput(sheetA_pd)
        impB=vtk.vtkImplicitPolyDataDistance(); impB.SetInput(sheetB_pd)
        self.build_side(right_bone, planeR, outR, impA, impB)
        self.build_side(left_bone,  planeL, outL, impA, impB)
        return True
