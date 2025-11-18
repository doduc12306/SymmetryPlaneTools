# SymmetryPlaneTools

Create a symmetry plane (Markups Plane) from 3–4 fiducial points in 3D Slicer, plus helpers to generate mirrored cutting sheets across the mid‑sagittal plane (MSP).

## Install (recommended)

1) Download a packaged zip from Releases: https://github.com/doduc12306/SymmetryPlaneTools/releases
2) In 3D Slicer: Tools → Extension Wizard → Install from package → select the .zip → Restart

Install from source (no build required):
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

## Build & Package from source (optional)

Note: Packaging requires a Slicer install that provides `SlicerConfig.cmake` under `lib/cmake/Slicer-<major.minor>`. Some distributions (e.g., user profile installs) may not include it.

### Windows (PowerShell)
```powershell
# Create a dedicated build folder next to the sources
mkdir SymmetryPlaneTools-build
cd SymmetryPlaneTools-build

# Point Slicer_DIR to your Slicer cmake config path, e.g.:
# C:\Program Files\3D Slicer 5.10.0\lib\cmake\Slicer-5.10
cmake -G "Ninja" -DSlicer_DIR="C:/Path/To/Slicer/lib/cmake/Slicer-5.x" -DCMAKE_BUILD_TYPE=Release ../SymmetryPlaneTools

# Build and create the extension .zip
cmake --build . --config Release --target package
```

### macOS/Linux (zsh/bash)
```zsh
mkdir -p SymmetryPlaneTools-build
cd SymmetryPlaneTools-build
cmake -G Ninja -DSlicer_DIR="/path/to/Slicer/lib/cmake/Slicer-5.x" -DCMAKE_BUILD_TYPE=Release ../SymmetryPlaneTools
cmake --build . --config Release --target package
```

The produced .zip can be installed via Extension Wizard → Install from package.

## Release to GitHub (optional)
```zsh
# Tag and push
git tag -a v0.1.0 -m "SymmetryPlaneTools v0.1.0"
git push origin v0.1.0

# Optionally attach the built zip via GitHub CLI
# gh release create v0.1.0 SymmetryPlaneTools-build/<artifact>.zip -t "v0.1.0" -n "Initial release"
```
