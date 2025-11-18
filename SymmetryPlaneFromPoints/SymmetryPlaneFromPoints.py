import os, unittest, vtk, qt, slicer, logging
import numpy as np
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget, ScriptedLoadableModuleLogic, ScriptedLoadableModuleTest
from slicer.util import VTKObservationMixin

class SymmetryPlaneFromPoints(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Symmetry Plane From Points"
        self.parent.categories = ["Utilities"]
        self.parent.dependencies = []
        self.parent.contributors = ["Do Nguyen Anh Duc"]
        self.parent.helpText = (
            "Create a symmetry plane from 3 or 4 fiducial points.\n"
            "- 3 points: exact plane\n- 4 points: best-fit PCA plane"
        )
        self.parent.acknowledgementText = "Module for symmetry plane analysis."

class SymmetryPlaneFromPointsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SymmetryPlaneFromPoints.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        uiWidget.setMRMLScene(slicer.mrmlScene)
        self.logic = SymmetryPlaneFromPointsLogic()
        # Observers
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        # Signals
        for le in (self.ui.point1LineEdit, self.ui.point2LineEdit, self.ui.point3LineEdit, self.ui.point4LineEdit):
            le.textChanged.connect(self.onPointLabelsChanged)
        self.ui.createPlaneButton.clicked.connect(self.onCreatePlaneButton)
        # Sheet controls
        self.ui.createSheetButton.clicked.connect(self.onCreateSheetButton)
        # Init
        self.updateButtonStates()
        self.initializeParameterNode()

    def cleanup(self):
        
        self.removeObservers()

    def enter(self):
        
        
        self.initializeParameterNode()

    def exit(self):
        
        
        self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    def onSceneStartClose(self, caller, event):
        
        
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event):
        
        
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self):
        

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode):

        if inputParameterNode:
            self.logic.setDefaultParameters(inputParameterNode)

        
        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        
        self._updatingGUIFromParameterNode = True

        
        if self._parameterNode.GetNodeReference("InputFiducials"):
            self.ui.fiducialSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputFiducials"))

        
        self.updateButtonStates()

        
        self._updatingGUIFromParameterNode = False

    def updateParameterNodeFromGUI(self, caller=None, event=None):

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = self._parameterNode.StartModify()

        
        self._parameterNode.SetParameter("Point1Label", self.ui.point1LineEdit.text)
        self._parameterNode.SetParameter("Point2Label", self.ui.point2LineEdit.text)
        self._parameterNode.SetParameter("Point3Label", self.ui.point3LineEdit.text)
        self._parameterNode.SetParameter("Point4Label", self.ui.point4LineEdit.text)

        self._parameterNode.EndModify(wasModified)

    def onPointLabelsChanged(self):
        self.updateParameterNodeFromGUI()
        self.updateButtonStates()

    def _collectLabelTexts(self):
        return [
            le.text.strip()
            for le in (
                self.ui.point1LineEdit,
                self.ui.point2LineEdit,
                self.ui.point3LineEdit,
                self.ui.point4LineEdit,
            )
        ]

    def _setStatusMessage(self, body, color):
        self.ui.statusLabel.text = (
            '<html><body><p><span style="font-size:9pt;">Status: '
            f'</span><span style="font-size:9pt; font-weight:600; color:{color};">{body}'
            '</span></p></body></html>'
        )

    def updateButtonStates(self):
        labels = self._collectLabelTexts()
        numPoints = sum(bool(lbl) for lbl in labels)
        if numPoints < 3:
            self._setStatusMessage(f"Need at least 3 point labels (currently {numPoints})", "#ff0000")
            self.ui.createPlaneButton.enabled = False
            self.ui.createPlaneButton.toolTip = f"Enter at least 3 point labels (currently {numPoints})"
            return
        if numPoints == 3:
            self._setStatusMessage("Ready - Exact plane (3 points)", "#00aa00")
            self.ui.createPlaneButton.toolTip = "Create exact plane through 3 points"
        else:
            self._setStatusMessage("Ready - Best-fit plane (4 points, PCA/SVD)", "#0000ff")
            self.ui.createPlaneButton.toolTip = "Create best-fit plane through 4 points using PCA/SVD"
        self.ui.createPlaneButton.enabled = True

    def onCreatePlaneButton(self):
        labels = [l for l in self._collectLabelTexts() if l]
        numPoints = len(labels)
        if numPoints < 3 or numPoints > 4:
            slicer.util.errorDisplay(f"Please enter 3 or 4 point labels (currently {numPoints}).")
            return
        try:
            planeNode = self.logic.createPlaneFromLabels(labels)
            if planeNode is None:
                slicer.util.errorDisplay("Plane creation returned None.")
                return
            msg = (f"✓ Exact plane: {', '.join(labels[:3])}" if numPoints==3 else f"✓ Best-fit plane: {', '.join(labels)}")
            slicer.util.showStatusMessage(msg,3000)
            logging.info(msg)
        except Exception as e:
            slicer.util.errorDisplay(str(e))
            logging.error(e)
    
    def onClearPointsButton(self):
        self.ui.point1LineEdit.text = ""
        self.ui.point2LineEdit.text = ""
        self.ui.point3LineEdit.text = ""
        self.ui.point4LineEdit.text = ""
        
        print("All point labels cleared.")
        self.updateButtonStates()

    def onCreateSheetButton(self):
        curveName = self.ui.curveNameLineEdit.text.strip() or 'MOL'
        yaw = self.ui.yawSpinBox.value
        lat = self.ui.latSpinBox.value
        med = self.ui.medSpinBox.value
        ext = self.ui.extendSpinBox.value
        try:
            sheet, mirror = self.logic.createCuttingSheet(curveName=curveName, yaw_deg=yaw, lat_mm=lat, med_mm=med, extend_mm=ext)
            msg = f"✓ Cutting sheet: {sheet.GetName()} + mirror {mirror.GetName()}"
            slicer.util.showStatusMessage(msg, 3000)
            logging.info(msg)
            self.ui.sheetStatusLabel.setText(f"<html><body><p><span style='color:#00aa00;font-size:8pt;'>Created: {sheet.GetName()} &amp; {mirror.GetName()}</span></p></body></html>")
        except Exception as e:
            slicer.util.errorDisplay(str(e))
            logging.error(e)
            self.ui.sheetStatusLabel.setText(f"<html><body><p><span style='color:#ff0000;font-size:8pt;'>Error: {str(e)}</span></p></body></html>")

class SymmetryPlaneFromPointsLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        # Directly import modular logic subcomponents (robust to package/non-package context)
        import os, sys
        here = os.path.dirname(os.path.abspath(__file__))
        logicDir = os.path.join(here, 'logic')
        if logicDir not in sys.path:
            sys.path.insert(0, logicDir)
        try:
            from SymmetryPlaneFromPoints.logic.plane import PlaneLogic  # type: ignore
            from SymmetryPlaneFromPoints.logic.gonion import GonionLogic  # type: ignore
            from SymmetryPlaneFromPoints.logic.sheet import SheetLogic  # type: ignore
        except Exception:
            from plane import PlaneLogic  # type: ignore
            from gonion import GonionLogic  # type: ignore
            from sheet import SheetLogic  # type: ignore
        self.planeLogic = PlaneLogic()
        self.gonionLogic = GonionLogic()
        self.sheetLogic = SheetLogic()

    def getParameterNode(self):
        node = slicer.mrmlScene.GetSingletonNode('SymmetryPlaneFromPointsParameters','vtkMRMLScriptedModuleNode')
        if node is None:
            node = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScriptedModuleNode')
            node.SetName('SymmetryPlaneFromPointsParameters')
            slicer.mrmlScene.AddNode(node)
        return node

    def setDefaultParameters(self, parameterNode):
        if not parameterNode.GetParameter("PlaneSize"):
            parameterNode.SetParameter("PlaneSize", "100.0")
        if not parameterNode.GetParameter("PlaneOpacity"):
            parameterNode.SetParameter("PlaneOpacity", "0.4")

    def _pointsFromFiducial(self, fiducialNode):
        pts = []
        temp = [0.0, 0.0, 0.0]
        for i in range(fiducialNode.GetNumberOfControlPoints()):
            fiducialNode.GetNthControlPointPositionWorld(i, temp)
            pts.append(temp[:])
        return pts

    def _createPlaneFromPointArrays(self, points):
        count = len(points)
        if count == 3:
            a, b, c = (np.array(pt, dtype=float) for pt in points)
            node = self.planeLogic.create_from_3_points(a, b, c, name='SymmetryPlane')
            if node:
                node.SetName('SymmetryPlane')  # enforce exact name for tests
            return node
        if count == 4:
            arr = [np.array(pt, dtype=float) for pt in points]
            node = self.planeLogic.create_best_fit(arr, name='SymmetryPlane')
            if node:
                node.SetName('SymmetryPlane')
            return node
        raise ValueError('Need 3 or 4 points')
    
    def findPointByLabel(self, label):
        label = label.strip().lower()
        
        # Search in MarkupsFiducialNode
        for fid in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            n = fid.GetNumberOfControlPoints()
            for i in range(n):
                thisLabel = fid.GetNthControlPointLabel(i)
                if thisLabel.strip().lower() == label:
                    p = [0.0, 0.0, 0.0]
                    fid.GetNthControlPointPositionWorld(i, p)
                    return np.array(p, dtype=float)
        
        # Search in MarkupsPointNode
        for pnode in slicer.util.getNodesByClass('vtkMRMLMarkupsPointNode'):
            if pnode.GetName().strip().lower() == label and pnode.GetNumberOfControlPoints() > 0:
                p = [0.0, 0.0, 0.0]
                pnode.GetNthControlPointPositionWorld(0, p)
                return np.array(p, dtype=float)
        
        raise ValueError(f"Point with label '{label}' not found. Please check that the point exists in your Markups.")

    def createSymmetryPlane(self, fiducialNode):
        if not fiducialNode:
            logging.error("Invalid fiducial node")
            return None
        
        numPoints = fiducialNode.GetNumberOfControlPoints()
        
        if numPoints == 3:
            return self.createPlaneFrom3Points(fiducialNode)
        elif numPoints == 4:
            return self.createPlaneFrom4Points(fiducialNode)
        else:
            logging.error(f"Invalid number of points: {numPoints}. Expected 3 or 4.")
            return None

    # New direct methods replacing external orchestrator dependency
    def createPlaneFrom3Points(self, fiducialNode):
        if fiducialNode.GetNumberOfControlPoints() != 3:
            logging.error('createPlaneFrom3Points requires exactly 3 points'); return None
        pts = self._pointsFromFiducial(fiducialNode)
        return self._createPlaneFromPointArrays(pts)

    def createPlaneFrom4Points(self, fiducialNode):
        if fiducialNode.GetNumberOfControlPoints() != 4:
            logging.error('createPlaneFrom4Points requires exactly 4 points'); return None
        pts = self._pointsFromFiducial(fiducialNode)
        return self._createPlaneFromPointArrays(pts)

    def createPlaneFromLabels(self, labels):
        points = [self.findPointByLabel(lb) for lb in labels]
        return self._createPlaneFromPointArrays(points)

    # Convenience: create and mirror a cutting sheet from a curve
    def createCuttingSheet(self, curveNode=None, curveName='MOL', yaw_deg=45.0, lat_mm=5.0, med_mm=15.0, extend_mm=10.0,
                           mirror_mode='model', mirror_yaw_sign=-1, planeName=None):
        """Build paired cutting sheets across MSP.
        mirror_mode:
          - 'model': build sheet on one side then reflect polydata (previous behavior).
          - 'curve': (default) mirror the curve points across MSP and rebuild sheet for better anatomical symmetry.
        Returns (sheetOriginal, sheetMirror).
        """
        if curveNode is None:
            try:
                curveNode = slicer.util.getNode(curveName)
            except slicer.util.MRMLNodeNotFoundException:
                raise RuntimeError(f"Curve node '{curveName}' not found")
        # --- Build primary sheet (Left side by convention) ---
        baseName = f"CuttingSheet_L_{curveName}"  # deterministic base name
        sheetNode, (O_msp, N_msp, msp_name) = self.sheetLogic.build_sheet(
            curveNode, yaw_deg=float(yaw_deg), lat_mm=float(lat_mm), med_mm=float(med_mm), extend_mm=float(extend_mm), baseName=baseName
        )
        sheetNode.SetName(baseName)  # enforce exact name
        def side_sign(poly):
            if not poly or poly.GetNumberOfPoints()==0:
                return 0.0
            # sample a few points for robust side sign (average projection)
            p=[0.0,0.0,0.0]; acc=0.0; cnt=min(20, poly.GetNumberOfPoints())
            step=max(1, poly.GetNumberOfPoints()//cnt)
            for i in range(0, poly.GetNumberOfPoints(), step):
                poly.GetPoint(i,p); acc += np.dot(np.array(p)-O_msp, N_msp)
                cnt -=1
                if cnt<=0: break
            return acc
        if mirror_mode == 'model':
            mirrorNode = self.sheetLogic.mirror_model(sheetNode, O_msp, N_msp)
            mirrorNode.SetName(f"CuttingSheet_R_{curveName}")
            # verify opposite side; if still same side, apply translation along normal
            try:
                s0 = side_sign(sheetNode.GetPolyData()); s1 = side_sign(mirrorNode.GetPolyData())
                if s0*s1 > 0:
                    # force shift across plane by projecting center
                    b=[0]*6; mirrorNode.GetPolyData().GetBounds(b)
                    c=np.array([(b[0]+b[1])/2,(b[2]+b[3])/2,(b[4]+b[5])/2])
                    dist=np.dot(c-O_msp, N_msp)
                    shift = -2.0*dist*N_msp
                    # build transform
                    M = vtk.vtkMatrix4x4();
                    for r in range(3):
                        for ccol in range(3): M.SetElement(r,ccol, 1.0 if r==ccol else 0.0)
                        M.SetElement(r,3, shift[r])
                    M.SetElement(3,0,0); M.SetElement(3,1,0); M.SetElement(3,2,0); M.SetElement(3,3,1)
                    try:
                        from SymmetryPlaneFromPoints.logic.utils import apply_and_harden  # type: ignore
                    except Exception:
                        from utils import apply_and_harden  # type: ignore
                    apply_and_harden(mirrorNode, M, 'Xform_ForceOppositeSide')
                    logging.info('Applied corrective translation to force mirror to opposite side.')
            except Exception as e:
                logging.warning(f"Mirror side correction skipped: {e}")
            logging.info(f"Cutting sheet (model mirror) created: {sheetNode.GetName()} & {mirrorNode.GetName()} MSP='{msp_name}'")
            # store references for console debugging
            self.lastSheetLeft = sheetNode
            self.lastSheetRight = mirrorNode
            return sheetNode, mirrorNode
        # curve-based mirroring
        pts = [curveNode.GetNthControlPointPositionWorld(i) for i in range(curveNode.GetNumberOfControlPoints())]
        pts_arr = np.array(pts, float)
        N = np.array(N_msp, float); N /= max(1e-9, np.linalg.norm(N))
        O = np.array(O_msp, float)
        # Reflect each point: p' = p - 2*((p - O)·N)N
        mirrored_pts = []
        for p in pts_arr:
            mirrored_pts.append(p - 2.0 * np.dot(p - O, N) * N)
        # Create (or reuse) mirrored curve node
        try:
            curveMirror = slicer.util.getNode(curveName + '_RmirrorCurve')
            if not isinstance(curveMirror, slicer.vtkMRMLMarkupsCurveNode): raise slicer.util.MRMLNodeNotFoundException()
        except slicer.util.MRMLNodeNotFoundException:
            curveMirror = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsCurveNode', curveName + '_RmirrorCurve')
        curveMirror.RemoveAllControlPoints()
        for p in mirrored_pts:
            curveMirror.AddControlPointWorld(p.tolist())
        # Build second sheet from mirrored curve (yaw sign may need flip to maintain outward direction)
        sheetMirror, _ = self.sheetLogic.build_sheet(
            curveMirror, yaw_deg=float(yaw_deg)*float(mirror_yaw_sign), lat_mm=float(lat_mm), med_mm=float(med_mm), extend_mm=float(extend_mm), baseName=f"CuttingSheet_R_{curveName}"
        )
        sheetMirror.SetName(f"CuttingSheet_R_{curveName}")
        # Validate that mirrored sheet lies on opposite side of MSP; if not, force reflection transform.
        try:
            # Compute centers (approx) via bounds
            b0 = [0]*6; b1=[0]*6
            if sheetNode.GetPolyData(): sheetNode.GetPolyData().GetBounds(b0)
            if sheetMirror.GetPolyData(): sheetMirror.GetPolyData().GetBounds(b1)
            c0 = np.array([(b0[0]+b0[1])/2.0,(b0[2]+b0[3])/2.0,(b0[4]+b0[5])/2.0])
            c1 = np.array([(b1[0]+b1[1])/2.0,(b1[2]+b1[3])/2.0,(b1[4]+b1[5])/2.0])
            s0 = np.dot(c0 - O, N)
            s1 = np.dot(c1 - O, N)
            if s0*s1 > 0:  # same side, fix by reflecting model
                try:
                    from SymmetryPlaneFromPoints.logic.utils import reflection_matrix, apply_and_harden  # type: ignore
                except Exception:
                    from utils import reflection_matrix, apply_and_harden  # type: ignore
                M = reflection_matrix(O, N)
                apply_and_harden(sheetMirror, M, 'Xform_SheetMirrorFix')
                logging.info('Applied reflection matrix to force curve-mirror sheet to opposite side.')
        except Exception as _mirrorSideErr:
            logging.warning(f"Mirror side validation skipped: {_mirrorSideErr}")
        logging.info(f"Cutting sheet (curve mirror) created: {sheetNode.GetName()} & {sheetMirror.GetName()} MSP='{msp_name}'")
        self.lastSheetLeft = sheetNode
        self.lastSheetRight = sheetMirror
        return sheetNode, sheetMirror



class SymmetryPlaneFromPointsTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SymmetryPlaneFromPoints_3Points()
        self.test_SymmetryPlaneFromPoints_4Points()

    def test_SymmetryPlaneFromPoints_3Points(self):
        self.delayDisplay("Starting test: 3 points plane")

        
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.AddControlPoint([0.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([10.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([0.0, 10.0, 0.0])

        
        logic = SymmetryPlaneFromPointsLogic()
        planeModel = logic.createSymmetryPlane(fiducialNode)

        
        self.assertIsNotNone(planeModel)
        self.assertEqual(planeModel.GetName(), "SymmetryPlane")

        self.delayDisplay('Test passed: 3 points plane created successfully')

    def test_SymmetryPlaneFromPoints_4Points(self):
        self.delayDisplay("Starting test: 4 points best-fit plane")

        
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.AddControlPoint([0.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([10.0, 0.0, 0.1])
        fiducialNode.AddControlPoint([0.0, 10.0, -0.1])
        fiducialNode.AddControlPoint([10.0, 10.0, 0.0])

        
        logic = SymmetryPlaneFromPointsLogic()
        planeModel = logic.createSymmetryPlane(fiducialNode)

        
        self.assertIsNotNone(planeModel)
        self.assertEqual(planeModel.GetName(), "SymmetryPlane")

        self.delayDisplay('Test passed: 4 points best-fit plane created successfully')
