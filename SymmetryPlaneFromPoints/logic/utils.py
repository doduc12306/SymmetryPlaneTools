import slicer, vtk, numpy as np, math, os
import logging

# Shared utility helpers

def harden(node):
    if node and node.GetTransformNodeID():
        slicer.vtkSlicerTransformLogic().hardenTransform(node)


def ensure_unique_name(base):
    name = base
    i = 1
    while slicer.mrmlScene.GetFirstNodeByName(name) is not None:
        i += 1
        name = f"{base}_{i}"
    return name


def tri_clean(pd):
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    cln = vtk.vtkCleanPolyData(); cln.SetInputConnection(tri.GetOutputPort()); cln.Update()
    out = vtk.vtkPolyData(); out.DeepCopy(cln.GetOutput()); return out


def ensure_normals(pd):
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    clean = vtk.vtkCleanPolyData(); clean.SetInputConnection(tri.GetOutputPort()); clean.Update()
    nrm = vtk.vtkPolyDataNormals(); nrm.SetInputConnection(clean.GetOutputPort())
    nrm.AutoOrientNormalsOn(); nrm.ConsistencyOn(); nrm.SplittingOff(); nrm.Update()
    out = vtk.vtkPolyData(); out.DeepCopy(nrm.GetOutput()); return out


def surface_area(pd):
    if not pd or pd.GetNumberOfPoints()==0: return 0.0
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    mp  = vtk.vtkMassProperties(); mp.SetInputConnection(tri.GetOutputPort()); mp.Update()
    return mp.GetSurfaceArea()


def unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def upsert_model(name, pd, color=(0.8,0.8,0.8), opacity=1.0):
    try: node = slicer.util.getNode(name)
    except slicer.util.MRMLNodeNotFoundException:
        node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode', name)
    node.CreateDefaultDisplayNodes(); node.SetAndObservePolyData(pd)
    d = node.GetDisplayNode()
    if d:
        d.SetColor(*color); d.SetOpacity(opacity); d.SetVisibility(1)
        try: d.SetBackfaceCulling(0)
        except: pass
    return node


def find_point_by_label(label):
    lbl = label.strip().lower()
    for fid in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
        for i in range(fid.GetNumberOfControlPoints()):
            if fid.GetNthControlPointLabel(i).strip().lower() == lbl:
                p=[0,0,0]; fid.GetNthControlPointPositionWorld(i,p)
                return np.array(p,float)
    for pnode in slicer.util.getNodesByClass('vtkMRMLMarkupsPointNode'):
        if pnode.GetName().strip().lower()==lbl and pnode.GetNumberOfControlPoints()>0:
            p=[0,0,0]; pnode.GetNthControlPointPositionWorld(0,p)
            return np.array(p,float)
    raise ValueError(f"Point label '{label}' not found")


def reflection_matrix(origin, normal):
    normal = unit(np.asarray(normal,float))
    n = normal.reshape(3,1)
    R = np.eye(3) - 2.0*(n @ n.T)
    t = 2.0*normal*float(np.dot(normal, origin))
    M = vtk.vtkMatrix4x4()
    for r in range(3):
        for c in range(3): M.SetElement(r,c,float(R[r,c]))
        M.SetElement(r,3,float(t[r]))
    M.SetElement(3,0,0); M.SetElement(3,1,0); M.SetElement(3,2,0); M.SetElement(3,3,1)
    return M


def apply_and_harden(node, mat4x4, xformName='Xform_Temp'):
    try: x = slicer.util.getNode(xformName)
    except slicer.util.MRMLNodeNotFoundException:
        x = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', xformName)
    x.SetMatrixTransformToParent(mat4x4)
    node.SetAndObserveTransformNodeID(x.GetID())
    slicer.vtkSlicerTransformLogic().hardenTransform(node)
    return x
