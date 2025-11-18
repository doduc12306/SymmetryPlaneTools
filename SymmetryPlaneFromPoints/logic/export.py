import slicer, vtk, os, logging
try:
    from SymmetryPlaneFromPoints.logic.utils import ensure_normals  # type: ignore
except Exception:
    from utils import ensure_normals  # type: ignore

class ExportLogic:
    def __init__(self, targets=('bone_left','bone_right')):
        self.targets = targets

    def export_to_stl(self, directory=None):
        if directory is None:
            import qt
            directory = qt.QFileDialog.getExistingDirectory(slicer.util.mainWindow(), 'Select directory to save STL', qt.QDir.homePath())
            if not directory:
                logging.info('Export cancelled')
                return False
        for name in self.targets:
            try:
                node = slicer.util.getNode(name)
                poly = ensure_normals(node.GetPolyData())
                outPath = os.path.join(directory, f'{name}.stl')
                w = vtk.vtkSTLWriter(); w.SetFileName(outPath); w.SetInputData(poly)
                try: w.SetFileTypeToBinary()
                except: pass
                if w.Write()!=1: raise RuntimeError('Writer failed')
                logging.info(f"Exported {name} -> {outPath}")
            except Exception as e:
                logging.warning(f"Skip {name}: {e}")
        return True
