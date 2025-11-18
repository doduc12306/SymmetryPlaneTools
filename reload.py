"""
Reload helper for SymmetryPlaneFromPoints, including its logic submodules.
Run this in Slicer's Python Interactor after editing code.
"""
import importlib, sys
import slicer, slicer.util

# List of all modules/submodules to reload (in dependency order)
modules_to_reload = [
    'SymmetryPlaneFromPoints.logic.utils',
    'SymmetryPlaneFromPoints.logic.plane',
    'SymmetryPlaneFromPoints.logic.mandible',
    'SymmetryPlaneFromPoints.logic.gonion',
    'SymmetryPlaneFromPoints.logic.sheet',
    'SymmetryPlaneFromPoints.logic.split',
    'SymmetryPlaneFromPoints.logic.guide',
    'SymmetryPlaneFromPoints.logic.export',
    'SymmetryPlaneFromPoints.logic',
    'SymmetryPlaneFromPointsLogic',
]

# Reload each submodule if already loaded
for mod_name in modules_to_reload:
    if mod_name in sys.modules:
        try:
            importlib.reload(sys.modules[mod_name])
            print(f"  ✓ Reloaded: {mod_name}")
        except Exception as e:
            print(f"  ⚠ Could not reload {mod_name}: {e}")

# Reload the main scripted module
slicer.util.reloadScriptedModule('SymmetryPlaneFromPoints')

print("\n✓ Full reload complete: SymmetryPlaneFromPoints + all logic submodules")
print("→ Go to: Modules → Utilities → Symmetry Plane From Points")
