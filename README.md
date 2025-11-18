# SymmetryPlaneTools

Create a symmetry plane (Markups Plane) from 3–4 fiducial points in 3D Slicer, plus helpers to generate mirrored cutting sheets across the mid‑sagittal plane (MSP).

## Install from source
- Edit → Application Settings → Modules → Additional module paths → Add
- Select: `.../SymmetryPlaneTools/SymmetryPlaneFromPoints`
- Restart Slicer

## Usage
- Modules → Utilities → Symmetry Plane From Points
- Enter labels of existing fiducials (e.g., S, N, Ba, Me)
- Click Create Plane to generate a Markups Plane (default size 300×500 mm)

Cutting sheets (optional):
- Provide a Markups Curve name (default `MOL`) and parameters, then Create Cutting Sheet to generate left/right sheets mirrored across MSP.

## Development workflow
Reload the module after code changes in Python Interactor:
```python
exec(open(r"<repo>/SymmetryPlaneTools/reload.py").read())
```
