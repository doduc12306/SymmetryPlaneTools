import os
import unittest
import vtk
import qt
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging

#
# SymmetryPlaneFromPoints
#

class SymmetryPlaneFromPoints(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

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

#
# SymmetryPlaneFromPointsWidget
#

class SymmetryPlaneFromPointsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SymmetryPlaneFromPoints.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = SymmetryPlaneFromPointsLogic()

        # Connections
        
        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Connect text changed signals to update button state
        self.ui.point1LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point2LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point3LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        self.ui.point4LineEdit.connect('textChanged(QString)', self.onPointLabelsChanged)
        
        # Connect UI elements
        self.ui.createPlaneButton.connect('clicked(bool)', self.onCreatePlaneButton)

        # Initial update
        self.updateButtonStates()

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if inputParameterNode:
            self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI.
        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        # Initial GUI update
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True

        # Update node selectors and sliders
        if self._parameterNode.GetNodeReference("InputFiducials"):
            self.ui.fiducialSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputFiducials"))

        # Update buttons states
        self.updateButtonStates()

        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

        # Store point labels
        self._parameterNode.SetParameter("Point1Label", self.ui.point1LineEdit.text)
        self._parameterNode.SetParameter("Point2Label", self.ui.point2LineEdit.text)
        self._parameterNode.SetParameter("Point3Label", self.ui.point3LineEdit.text)
        self._parameterNode.SetParameter("Point4Label", self.ui.point4LineEdit.text)

        self._parameterNode.EndModify(wasModified)

    def onPointLabelsChanged(self, text):
        """
        Called when any point label text changes.
        """
        self.updateParameterNodeFromGUI()
        self.updateButtonStates()

    def updateButtonStates(self):
        """
        Update the enabled/disabled state of the create plane button.
        """
        # Get labels
        label1 = self.ui.point1LineEdit.text.strip()
        label2 = self.ui.point2LineEdit.text.strip()
        label3 = self.ui.point3LineEdit.text.strip()
        label4 = self.ui.point4LineEdit.text.strip()
        
        # Count non-empty labels
        labels = [label1, label2, label3, label4]
        numPoints = sum(1 for l in labels if l)
        
        # Update status label
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
        """
        Run processing when user clicks "Create Plane" button.
        """
        # Get labels from line edits
        label1 = self.ui.point1LineEdit.text.strip()
        label2 = self.ui.point2LineEdit.text.strip()
        label3 = self.ui.point3LineEdit.text.strip()
        label4 = self.ui.point4LineEdit.text.strip()
        
        # Collect non-empty labels
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
            # Find points by labels
            points = []
            for label in labels:
                try:
                    point = self.logic.findPointByLabel(label)
                    points.append(point)
                    print(f"✓ Found point '{label}': {point}")
                except ValueError as e:
                    slicer.util.errorDisplay(str(e))
                    return
            
            # Create a temporary fiducial node with all points
            tempFiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "TempSymmetryPoints")
            for i, point in enumerate(points):
                tempFiducialNode.AddControlPoint(point)
                tempFiducialNode.SetNthControlPointLabel(i, labels[i])
            
            # Compute using a single "Compute results" message
            with slicer.util.tryWithErrorDisplay("Failed to create symmetry plane.", waitCursor=True):
                planeModel = self.logic.createSymmetryPlane(tempFiducialNode)
                
                # Remove temporary node
                slicer.mrmlScene.RemoveNode(tempFiducialNode)
                
                if planeModel:
                    # Display success message
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
        """
        Clear all entered labels.
        """
        self.ui.point1LineEdit.text = ""
        self.ui.point2LineEdit.text = ""
        self.ui.point3LineEdit.text = ""
        self.ui.point4LineEdit.text = ""
        
        print("All point labels cleared.")
        self.updateButtonStates()

#
# SymmetryPlaneFromPointsLogic
#

class SymmetryPlaneFromPointsLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module. The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
        
        # Import the actual logic implementation
        from SymmetryPlaneFromPointsLogic import SymmetryPlaneLogic
        self.planeLogic = SymmetryPlaneLogic()

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        if not parameterNode.GetParameter("PlaneSize"):
            parameterNode.SetParameter("PlaneSize", "100.0")
        if not parameterNode.GetParameter("PlaneOpacity"):
            parameterNode.SetParameter("PlaneOpacity", "0.4")
    
    def findPointByLabel(self, label):
        """
        Find a fiducial point by its label (case-insensitive).
        Searches all MarkupsFiducial nodes and MarkupsPoint nodes in the scene.
        
        Args:
            label: str - The label of the point to find
            
        Returns:
            numpy array - [x, y, z] coordinates in world (RAS) space
            
        Raises:
            ValueError: If point with the label is not found
        """
        import numpy as np
        
        label = label.strip().lower()
        
        # Search in Markups Fiducial nodes (multiple points per node)
        for fid in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            n = fid.GetNumberOfControlPoints()
            for i in range(n):
                thisLabel = fid.GetNthControlPointLabel(i)
                if thisLabel.strip().lower() == label:
                    p = [0.0, 0.0, 0.0]
                    fid.GetNthControlPointPositionWorld(i, p)
                    return np.array(p, dtype=float)
        
        # Search in Markups Point nodes (one point per node - use node name as label)
        for pnode in slicer.util.getNodesByClass('vtkMRMLMarkupsPointNode'):
            if pnode.GetName().strip().lower() == label and pnode.GetNumberOfControlPoints() > 0:
                p = [0.0, 0.0, 0.0]
                pnode.GetNthControlPointPositionWorld(0, p)
                return np.array(p, dtype=float)
        
        raise ValueError(f"Point with label '{label}' not found. Please check that the point exists in your Markups.")

    def createSymmetryPlane(self, fiducialNode):
        """
        Create a symmetry plane from fiducial points.
        
        Args:
            fiducialNode: vtkMRMLMarkupsFiducialNode with 3 or 4 points
            
        Returns:
            vtkMRMLModelNode: The created plane model
        """
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

#
# SymmetryPlaneFromPointsTest
#

class SymmetryPlaneFromPointsTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_SymmetryPlaneFromPoints_3Points()
        self.test_SymmetryPlaneFromPoints_4Points()

    def test_SymmetryPlaneFromPoints_3Points(self):
        """ Test creating a plane from 3 points
        """
        self.delayDisplay("Starting test: 3 points plane")

        # Create a fiducial node with 3 points
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.AddControlPoint([0.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([10.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([0.0, 10.0, 0.0])

        # Create the plane
        logic = SymmetryPlaneFromPointsLogic()
        planeModel = logic.createSymmetryPlane(fiducialNode)

        # Verify the plane was created
        self.assertIsNotNone(planeModel)
        self.assertEqual(planeModel.GetName(), "SymmetryPlane")

        self.delayDisplay('Test passed: 3 points plane created successfully')

    def test_SymmetryPlaneFromPoints_4Points(self):
        """ Test creating a best-fit plane from 4 points
        """
        self.delayDisplay("Starting test: 4 points best-fit plane")

        # Create a fiducial node with 4 points (roughly planar)
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.AddControlPoint([0.0, 0.0, 0.0])
        fiducialNode.AddControlPoint([10.0, 0.0, 0.1])
        fiducialNode.AddControlPoint([0.0, 10.0, -0.1])
        fiducialNode.AddControlPoint([10.0, 10.0, 0.0])

        # Create the plane
        logic = SymmetryPlaneFromPointsLogic()
        planeModel = logic.createSymmetryPlane(fiducialNode)

        # Verify the plane was created
        self.assertIsNotNone(planeModel)
        self.assertEqual(planeModel.GetName(), "SymmetryPlane")

        self.delayDisplay('Test passed: 4 points best-fit plane created successfully')
