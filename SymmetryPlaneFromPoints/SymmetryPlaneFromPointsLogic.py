"""Minimal backward-compatible orchestrator for modular logic classes.

This file intentionally keeps only thin wrappers; detailed implementations live in
separate modules under `logic/` for easier maintenance.
"""

import logging, os, sys, numpy as np, slicer

# Robust import of logic submodules whether this file is imported as a top-level module
# (the usual Slicer pattern) or as part of a package. We try absolute first, then
# fall back to adding the local 'logic' folder to sys.path.
try:
    from SymmetryPlaneFromPoints.logic.plane import PlaneLogic  # type: ignore
    from SymmetryPlaneFromPoints.logic.gonion import GonionLogic  # type: ignore
    from SymmetryPlaneFromPoints.logic.sheet import SheetLogic  # type: ignore
    from SymmetryPlaneFromPoints.logic.split import SplitLogic  # type: ignore
    from SymmetryPlaneFromPoints.logic.guide import GuideLogic  # type: ignore
    from SymmetryPlaneFromPoints.logic.export import ExportLogic  # type: ignore
except Exception:
    _here = os.path.dirname(os.path.abspath(__file__))
    _logic = os.path.join(_here, 'logic')
    if _logic not in sys.path:
        sys.path.insert(0, _logic)
    from plane import PlaneLogic  # type: ignore
    from gonion import GonionLogic  # type: ignore
    from sheet import SheetLogic  # type: ignore
    from split import SplitLogic  # type: ignore
    from guide import GuideLogic  # type: ignore
    from export import ExportLogic  # type: ignore


class SymmetryPlaneLogic:
    def __init__(self):
        self.planeLogic = PlaneLogic()
        self.gonionLogic = GonionLogic()
        self.sheetLogic = SheetLogic()
        self.splitLogic = SplitLogic()
        self.guideLogic = GuideLogic()
        self.exportLogic = ExportLogic()

    # Plane creation wrappers
    def createPlaneFrom3Points(self, fiducialNode):
        if fiducialNode.GetNumberOfControlPoints() != 3:
            logging.error('createPlaneFrom3Points requires exactly 3 points'); return None
        pts=[]; tmp=[0,0,0]
        for i in range(3): fiducialNode.GetNthControlPointPositionWorld(i,tmp); pts.append(np.array(tmp,float))
        planeNode = self.planeLogic.create_from_3_points(*pts, name='SymmetryPlane')
        return planeNode

    def createPlaneFrom4Points(self, fiducialNode):
        if fiducialNode.GetNumberOfControlPoints() != 4:
            logging.error('createPlaneFrom4Points requires exactly 4 points'); return None
        pts=[]; tmp=[0,0,0]
        for i in range(4): fiducialNode.GetNthControlPointPositionWorld(i,tmp); pts.append(np.array(tmp,float))
        planeNode = self.planeLogic.create_best_fit(pts, name='SymmetryPlane')
        return planeNode

    # Unified label-based creation (used by widget)
    def createPlaneFromLabels(self, labels):
        """Create plane from a list of 3 or 4 fiducial labels.
        Returns created plane node or None.
        """
        pts=[]
        for lb in labels:
            pt = self.find_point_by_label(lb)
            if pt is None:
                raise ValueError(f"Label '{lb}' not found in any Markups fiducial")
            pts.append(pt)
        tmpNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','TmpPlanePts')
        for i,p in enumerate(pts):
            tmpNode.AddControlPoint(p.tolist())
            tmpNode.SetNthControlPointLabel(i, labels[i])
        try:
            if len(pts)==3:
                plane = self.createPlaneFrom3Points(tmpNode)
            elif len(pts)==4:
                plane = self.createPlaneFrom4Points(tmpNode)
            else:
                raise ValueError('Need 3 or 4 labels')
            return plane
        finally:
            slicer.mrmlScene.RemoveNode(tmpNode)

    def find_point_by_label(self, label):
        want = label.strip().lower()
        p=[0,0,0]
        for fid in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            for i in range(fid.GetNumberOfControlPoints()):
                lb = fid.GetNthControlPointLabel(i).strip().lower()
                if lb==want:
                    fid.GetNthControlPointPositionWorld(i,p)
                    return np.array(p,float)
        return None

    # Reference plane helper (expects S,N,Me,Ba points already placed)
    def create_reference_planes(self):
        try:
            S = self.gonionLogic.find_point_any({'s'})
            N = self.gonionLogic.find_point_any({'n'})
            Me = self.gonionLogic.find_point_any({'me','menton'})
            Ba = self.gonionLogic.find_point_any({'ba'})
            if any(p is None for p in (S,N,Me,Ba)):
                raise RuntimeError('Missing one of required points: S,N,Me,Ba')
            origin_cr, normal_cr = (S+N+Ba)/3.0, np.cross(N-S, Ba-S); ln=np.linalg.norm(normal_cr); normal_cr/=ln
            origin_snme, normal_snme = (S+N+Me)/3.0, np.cross(N-S, Me-S); ln=np.linalg.norm(normal_snme); normal_snme/=ln
            self.planeLogic._create_markups_plane = self.planeLogic._create_markups_plane  # for clarity
            self.planeLogic._create_markups_plane(origin_cr, normal_cr, 'MSP_CR_SNBa')
            self.planeLogic._create_markups_plane(origin_snme, normal_snme, 'MSP_SNMe')
            slicer.util.showStatusMessage('✓ Created MSP planes',3000); return True
        except Exception as e:
            logging.error(e); slicer.util.errorDisplay(str(e)); return False

    # Gonion points wrapper
    def find_gonion_points(self):
        return self.gonionLogic.get_msp_O_N() and True  # placeholder to keep API; detailed use via gonionLogic

    # Cutting sheet
    def create_and_mirror_sheet(self, yaw_deg=45.0, lat_mm=5.0, med_mm=15.0, ext_mm=10.0):
        try:
            curve = slicer.util.getNode('MOL')
            sheet,_ = self.sheetLogic.build_sheet(curve, yaw_deg=yaw_deg, lat_mm=lat_mm, med_mm=med_mm, extend_mm=ext_mm)
            O,N,_ = self.sheetLogic.get_msp(); self.sheetLogic.mirror_model(sheet, O, N)
            slicer.util.showStatusMessage('Cutting sheet created & mirrored',3000); return True
        except Exception as e:
            logging.error(e); slicer.util.errorDisplay(str(e)); return False

    # Mandible split
    def split_mandible(self, leftSheetName='Sheet_MOL_yaw_45_out5p_in15'):
        try:
            rightSheet = leftSheetName + '_Rmirror'
            self.splitLogic.perform_split(leftSheetName, rightSheet)
            slicer.util.showStatusMessage('Mandible split',3000); return True
        except Exception as e:
            logging.error(e); slicer.util.errorDisplay(str(e)); return False

    # Guides
    def create_guides(self, sheetA='Sheet_MOL_yaw_45_out5p_in15', sheetB=None):
        try:
            if sheetB is None: sheetB = sheetA + '_Rmirror'
            self.guideLogic.create_guides(sheetA, sheetB)
            slicer.util.showStatusMessage('Guides created',3000); return True
        except Exception as e:
            logging.error(e); slicer.util.errorDisplay(str(e)); return False

    # Export STL
    def export_bone_pieces_to_stl(self):
        return self.exportLogic.export_to_stl()
