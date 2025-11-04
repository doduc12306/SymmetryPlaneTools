"""
Reload helper for SymmetryPlaneFromPoints, including its logic module.
Run this in Slicer's Python Interactor after editing code.
"""
import importlib, sys
import slicer, slicer.util

# Reload logic module explicitly to avoid Python module caching
mod_name = 'SymmetryPlaneFromPointsLogic'
if mod_name in sys.modules:
	importlib.reload(sys.modules[mod_name])
else:
	__import__(mod_name)

# Reload the scripted module itself
slicer.util.reloadScriptedModule('SymmetryPlaneFromPoints')

print("✓ Reloaded: SymmetryPlaneFromPointsLogic, SymmetryPlaneFromPoints")
print("→ Go to: Modules → Utilities → Symmetry Plane From Points")
