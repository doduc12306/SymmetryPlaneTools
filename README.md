# SymmetryPlaneTools

Create a symmetry plane (Markups Plane) from 3–4 fiducial points in 3D Slicer, plus helpers to generate mirrored cutting sheets across the mid‑sagittal plane (MSP).

# Cutting sheets:
- Provide a Markups Curve name and parameters, then Create Cutting Sheet to generate left/right sheets mirrored across MSP.

## Install from source
- Download zip form github and extract it
- Edit → Application Settings → Modules → Additional module paths → Add
- Select: `.../SymmetryPlaneTools/SymmetryPlaneFromPoints`
- Restart Slicer

## Usage
- Modules → Utilities → Symmetry Plane From Points
- Enter labels of existing fiducials (e.g., S, N, Ba, Me)
- Click Create Plane to generate a Markups Plane (default size 300×500 mm)
