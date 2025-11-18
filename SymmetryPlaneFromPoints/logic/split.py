import slicer, vtk, numpy as np, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_normals, surface_area, upsert_model, harden  # type: ignore
except Exception:
    from utils import ensure_normals, surface_area, upsert_model, harden  # type: ignore

MODEL_KEYS = ('mandible','mandible_aftercut','lower jaw','lowerjaw','jaw - mandible','xhd','xương hàm dưới','ham duoi','bone_left','bone_right')

class SplitLogic:
    def __init__(self):
        pass

    def find_model_by_name_contains(self, key):
        k=key.lower()
        for m in slicer.util.getNodesByClass('vtkMRMLModelNode'):
            if k in (m.GetName() or '').lower(): return m
        return None

    def get_mandible_node(self):
        for m in slicer.util.getNodesByClass('vtkMRMLModelNode'):
            if any(k in (m.GetName() or '').lower() for k in MODEL_KEYS):
                harden(m)
                if m.GetPolyData() and m.GetPolyData().GetNumberOfPoints()>0:
                    return m
        raise RuntimeError('Mandible model not found')

    def split_by_sheet(self, inputPD, sheetPD):
        imp=vtk.vtkImplicitPolyDataDistance(); imp.SetInput(sheetPD)
        pd=vtk.vtkPolyData(); pd.DeepCopy(inputPD)
        sd=vtk.vtkDoubleArray(); sd.SetName('SignedDist'); sd.SetNumberOfTuples(pd.GetNumberOfPoints())
        p=[0,0,0]
        for i in range(pd.GetNumberOfPoints()): pd.GetPoint(i,p); sd.SetValue(i, imp.EvaluateFunction(p))
        pd.GetPointData().AddArray(sd); pd.GetPointData().SetScalars(sd)
        clipNeg=vtk.vtkClipPolyData(); clipNeg.SetInputData(pd); clipNeg.SetValue(0.0); clipNeg.InsideOutOff(); clipNeg.Update()
        clipPos=vtk.vtkClipPolyData(); clipPos.SetInputData(pd); clipPos.SetValue(0.0); clipPos.InsideOutOn(); clipPos.Update()
        partNeg=ensure_normals(clipNeg.GetOutput()); partPos=ensure_normals(clipPos.GetOutput())
        areaNeg=surface_area(partNeg); areaPos=surface_area(partPos)
        if areaNeg==0.0 and areaPos==0.0: raise RuntimeError('Sheet does not intersect bone')
        if areaNeg>0.0 and (areaNeg <= areaPos or areaPos==0.0): return partNeg, partPos
        else: return partPos, partNeg

    def perform_split(self, leftSheetName, rightSheetName, outLeft='bone_left', outRight='bone_right', outAfter='mandible_aftercut'):
        mandNode=self.get_mandible_node(); mandPD=ensure_normals(mandNode.GetPolyData())
        leftSheet=self.find_model_by_name_contains(leftSheetName)
        rightSheet=self.find_model_by_name_contains(rightSheetName)
        if not leftSheet or not rightSheet: raise RuntimeError('Cutting sheets not found')
        leftPD=ensure_normals(leftSheet.GetPolyData()); rightPD=ensure_normals(rightSheet.GetPolyData())
        boneL, rest=self.split_by_sheet(mandPD, leftPD)
        boneR, after=self.split_by_sheet(rest, rightPD)
        upsert_model(outLeft, boneL, (1.0,0.25,0.25),1.0)
        upsert_model(outRight, boneR,(0.25,0.45,1.0),1.0)
        upsert_model(outAfter, after,(0.85,0.95,1.0),1.0)
        logging.info(f"Split complete areas: L={surface_area(boneL):.2f} R={surface_area(boneR):.2f} After={surface_area(after):.2f}")
        return True
