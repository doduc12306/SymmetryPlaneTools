# SymmetryPlaneTools

3D Slicer Extension để tạo mặt phẳng đối xứng từ điểm fiducial.

## Cài đặt

1. Mở 3D Slicer
2. **Edit** → **Application Settings** → **Modules**
3. Add path: `/path/to/SymmetryPlaneTools/SymmetryPlaneFromPoints`
4. Restart Slicer

## Sử dụng

### 1. Tạo test data (trong Python Interactor):
```python
exec(open('/path/to/demo.py').read())
```

### 2. Sử dụng module:
- **Modules** → **Utilities** → **Symmetry Plane From Points**
- Nhập labels: `S`, `N`, `Ba` (hoặc `Me`)
- Click **Create Plane**

### 3. Kết quả:
- Mặt phẳng hình chữ nhật **300×500 mm** (rộng×dài)
- Màu xanh nhạt, opacity 0.4
- 3 điểm: Exact plane | 4 điểm: Best-fit (PCA/SVD)

## Thay đổi kích thước

Edit `SymmetryPlaneFromPointsLogic.py`:
```python
self.planeWidth = 300.0   # Chiều rộng (mm)
self.planeHeight = 500.0  # Chiều dài (mm)
```

Sau đó reload:
```python
exec(open('/path/to/reload.py').read())
```
