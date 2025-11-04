import os
import unittest
import vtk
import qt
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging


class SymmetryPlaneFromPoints(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Symmetry Plane From Points"
        self.parent.categories = ["Utilities"]
        self.parent.dependencies = []
        self.parent.contributors = ["Do Nguyen Anh Duc"]
        self.parent.helpText = """
        This module creates a symmetry plane from 3 or 4 fiducial points.
        - 3 points: Creates an exact plane through all 3 points
        - 4 points: Creates a best-fit plane using PCA/SVD
        """
        self.parent.acknowledgementText = """
        This module was developed for symmetry plane analysis in 3D Slicer.
        """


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

        
        
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        
        self.ui.point1LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point2LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point3LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point4LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        
        
        self.ui.createPlaneButton.connect('clicked(bool)', self.onCreatePlaneButton)

        
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

    def onPointLabelsChanged(self, text):
        self.updateParameterNodeFromGUI()
        self.updateButtonStates()

    def updateButtonStates(self):
        
        label1 = self.ui.point1LineEdit.text.strip()
        label2 = self.ui.point2LineEdit.text.strip()
        label3 = self.ui.point3LineEdit.text.strip()
        label4 = self.ui.point4LineEdit.text.strip()
        
        
        labels = [label1, label2, label3, label4]
        numPoints = sum(1 for l in labels if l)
        
        
        if numPoints < 3:
            self.ui.statusLabel.text = f'<html><body><p><span style="font-size:9pt;">Status: </span><span style="font-size:9pt; font-weight:600; color:#ff0000;">Need at least 3 point labels (currently {numPoints})</span></p></body></html>'
            self.ui.createPlaneButton.enabled = False
            self.ui.createPlaneButton.toolTip = f"Enter at least 3 point labels (currently {numPoints})"
        elif numPoints == 3:
            self.ui.statusLabel.text = '<html><body><p><span style="font-size:9pt;">Status: </span><span style="font-size:9pt; font-weight:600; color:#00aa00;">Ready - Exact plane (3 points)</span></p></body></html>'
            self.ui.createPlaneButton.enabled = True
            self.ui.createPlaneButton.toolTip = "Create exact plane through 3 points"
        elif numPoints == 4:
            self.ui.statusLabel.text = '<html><body><p><span style="font-size:9pt;">Status: </span><span style="font-size:9pt; font-weight:600; color:#0000ff;">Ready - Best-fit plane (4 points, PCA/SVD)</span></p></body></html>'
            self.ui.createPlaneButton.enabled = True
            self.ui.createPlaneButton.toolTip = "Create best-fit plane through 4 points using PCA/SVD"

    def onCreatePlaneButton(self):
        
        label1 = self.ui.point1LineEdit.text.strip()
        label2 = self.ui.point2LineEdit.text.strip()
        label3 = self.ui.point3LineEdit.text.strip()
        label4 = self.ui.point4LineEdit.text.strip()
        
        
        labels = []
        if label1:
            labels.append(label1)
        if label2:
            labels.append(label2)
        if label3:
            labels.append(label3)
        if label4:
            labels.append(label4)
        
        numPoints = len(labels)
        
        if numPoints < 3 or numPoints > 4:
            slicer.util.errorDisplay(f"Please enter 3 or 4 point labels (currently {numPoints}).")
            return

        try:
            
            points = []
            for label in labels:
                try:
                    point = self.logic.findPointByLabel(label)
                    points.append(point)
                    print(f"✓ Found point '{label}': {point}")
                except ValueError as e:
                    slicer.util.errorDisplay(str(e))
                    return
            
            
            tempFiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TempSymmetryPoints")
            for i, point in enumerate(points):
                tempFiducialNode.AddControlPoint(point)
                tempFiducialNode.SetNthControlPointLabel(i, labels[i])
            
            
            with slicer.util.tryWithErrorDisplay("Failed to create symmetry plane.", waitCursor=True):
                planeModel = self.logic.createSymmetryPlane(tempFiducialNode)
                
                
                slicer.mrmlScene.RemoveNode(tempFiducialNode)
                
                if planeModel:
                    
                    if numPoints == 3:
                        message = f"✓ Successfully created exact plane through points: {', '.join(labels[:3])}"
                    else:
                        message = f"✓ Successfully created best-fit plane through points: {', '.join(labels)}"
                    
                    slicer.util.showStatusMessage(message, 3000)
                    print(message)
                    print(f"Plane model created: {planeModel.GetName()}")
                else:
                    slicer.mrmlScene.RemoveNode(tempFiducialNode)
                    slicer.util.errorDisplay("Failed to create plane model.")
                    
        except Exception as e:
            slicer.util.errorDisplay(f"Error creating plane: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def onClearPointsButton(self):
        self.ui.point1LineEdit.text = ""
        self.ui.point2LineEdit.text = ""
        self.ui.point3LineEdit.text = ""
        self.ui.point4LineEdit.text = ""
        
        print("All point labels cleared.")
        self.updateButtonStates()



class SymmetryPlaneFromPointsLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        
        
        from SymmetryPlaneFromPointsLogic import SymmetryPlaneLogic
        self.planeLogic = SymmetryPlaneLogic()

    def setDefaultParameters(self, parameterNode):
        if not parameterNode.GetParameter("PlaneSize"):
            parameterNode.SetParameter("PlaneSize", "100.0")
        if not parameterNode.GetParameter("PlaneOpacity"):
            parameterNode.SetParameter("PlaneOpacity", "0.4")
    
    def findPointByLabel(self, label):
        import numpy as np
        
        label = label.strip().lower()
        
        
        for fid in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            n = fid.GetNumberOfControlPoints()
            for i in range(n):
                thisLabel = fid.GetNthControlPointLabel(i)
                if thisLabel.strip().lower() == label:
                    p = [0.0, 0.0, 0.0]
                    fid.GetNthControlPointPositionWorld(i, p)
                    return np.array(p, dtype=float)
        
        
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
            return self.planeLogic.createPlaneFrom3Points(fiducialNode)
        elif numPoints == 4:
            return self.planeLogic.createPlaneFrom4Points(fiducialNode)
        else:
            logging.error(f"Invalid number of points: {numPoints}. Expected 3 or 4.")
            return None



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
