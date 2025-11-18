import slicer, vtk
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_normals  # type: ignore
except Exception:
    from utils import ensure_normals  # type: ignore

MODEL_MAND_KEYS = (
    'mandible','mandible_aftercut','lower jaw','lowerjaw','jaw - mandible',
    'xhd','xương hàm dưới','ham duoi','bone_left','bone_right'
)
SEG_MAND_KEYS   = (
    'mandible','lower jaw','lowerjaw','xhd','xương hàm dưới','ham duoi',
    'mand','mandible_aftercut','aftercut','after cut','bone_left','bone_right'
)
SEG_EXCLUDE_KEYS = ('maxilla','upper','skull','teeth','canal','upper skull')

class MandibleData:
    def __init__(self):
        pass

    def _try_get_mandible_model_node(self):
        for m in slicer.util.getNodesByClass('vtkMRMLModelNode'):
            nm=(m.GetName() or '').lower()
            if any(k in nm for k in MODEL_MAND_KEYS):
                if m.GetTransformNodeID():
                    slicer.vtkSlicerTransformLogic().hardenTransform(m)
                pd=m.GetPolyData()
                if pd and pd.GetNumberOfPoints()>0:
                    return m
        return None

    def _ensure_closed_surface(self, segNode):
        try:
            segNode.CreateClosedSurfaceRepresentation(); return True
        except Exception:
            pass
        try:
            seg = segNode.GetSegmentation()
            closedName = slicer.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
            seg.CreateRepresentation(closedName); return True
        except Exception:
            return False

    def _segment_poly(self, segNode, segId):
        if self._ensure_closed_surface(segNode):
            poly = vtk.vtkPolyData()
            ok = segNode.GetClosedSurfaceRepresentation(segId, poly)
            if ok and poly and poly.GetNumberOfPoints()>0:
                return poly
        # fallback export
        before = set([n.GetID() for n in slicer.util.getNodesByClass('vtkMRMLModelNode')])
        ids = vtk.vtkStringArray(); ids.InsertNextValue(segId)
        slicer.modules.segmentations.logic().ExportSegmentsToModels(segNode, ids, None)
        after = {n.GetID(): n for n in slicer.util.getNodesByClass('vtkMRMLModelNode')}
        created = [after[i] for i in after if i not in before]
        if not created:
            return None
        mdl = created[0]
        if mdl.GetTransformNodeID():
            slicer.vtkSlicerTransformLogic().hardenTransform(mdl)
        return mdl.GetPolyData()

    def get_polydata_and_ensure_model(self):
        mdl = self._try_get_mandible_model_node()
        if mdl:
            return ensure_normals(mdl.GetPolyData())
        best_pd=None; best_score=-1.0
        segNodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        if not segNodes:
            raise RuntimeError('No segmentation with mandible found in scene')
        for segNode in segNodes:
            segs=segNode.GetSegmentation()
            for i in range(segs.GetNumberOfSegments()):
                segId=segs.GetNthSegmentID(i)
                nm=(segs.GetNthSegment(i).GetName() or '').lower()
                if any(ek in nm for ek in SEG_EXCLUDE_KEYS):
                    continue
                pd=self._segment_poly(segNode, segId)
                if not pd or pd.GetNumberOfPoints()==0:
                    continue
                tri=vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
                mp=vtk.vtkMassProperties(); mp.SetInputConnection(tri.GetOutputPort()); mp.Update()
                area=mp.GetSurfaceArea()
                if area<=0: continue
                name_bonus = 1.0 if any(k in nm for k in SEG_MAND_KEYS) else 0.0
                score = name_bonus*1e9 + area
                if score>best_score:
                    best_score=score; best_pd=pd
        if best_pd is None:
            raise RuntimeError('Could not derive mandible surface from segmentation')
        # create a model node for visibility
        mdl = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode', 'Mandible')
        mdl.SetAndObservePolyData(best_pd)
        disp = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelDisplayNode')
        slicer.mrmlScene.AddNode(disp)
        disp.SetBackfaceCulling(0); disp.SetOpacity(0.3)
        mdl.SetAndObserveDisplayNodeID(disp.GetID())
        return ensure_normals(best_pd)

    def get_model_node(self):
        m = self._try_get_mandible_model_node()
        if m: return m
        self.get_polydata_and_ensure_model()
        m = self._try_get_mandible_model_node()
        if not m: raise RuntimeError('Mandible model node not found after ensure')
        return m
