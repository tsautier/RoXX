# Build and Packaging Guide for RoXX

## 🔨 Building RoXX

### Prerequisites

```bash
# Install development dependencies
pip install -e ".[dev]"
```

---

## 📦 Packaging Options

### 1. Python Package (pip)

**Build wheel and source distribution**:

```bash
# Install build tools
pip install build

# Build package
python -m build

# This creates:
# - dist/roxx-1.0.0b0-py3-none-any.whl
# - dist/roxx-1.0.0b0.tar.gz
```

**Install locally**:

```bash
pip install dist/roxx-1.0.0b0-py3-none-any.whl
```

**Upload to PyPI** (when ready):

```bash
pip install twine
twine upload dist/*
```

---

### 2. Windows Executable (.exe)

**Using PyInstaller**:

```powershell
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller roxx.spec

# Output: dist/roxx.exe
```

**One-file executable** (alternative):

```powershell
pyinstaller --onefile --name roxx --icon roxx_logo.png roxx/__main__.py
```

**Test the executable**:

```powershell
.\dist\roxx.exe
```

---

### 3. Linux Package (.deb)

**Using stdeb**:

```bash
# Install stdeb
pip install stdeb

# Create Debian package
python setup.py --command-packages=stdeb.command bdist_deb

# Output: deb_dist/python3-roxx_1.0.0b0-1_all.deb
```

**Install**:

```bash
sudo dpkg -i deb_dist/python3-roxx_1.0.0b0-1_all.deb
```

---

### 4. Linux Package (.rpm)

**Using setup.py**:

```bash
# Create RPM
python setup.py bdist_rpm

# Output: dist/roxx-1.0.0b0-1.noarch.rpm
```

**Install**:

```bash
sudo rpm -i dist/roxx-1.0.0b0-1.noarch.rpm
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=roxx --cov-report=html

# Run specific test file
pytest tests/test_system.py

# Run with verbose output
pytest -v
```

### Test Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=roxx --cov-report=html

# Open in browser
# Windows: start htmlcov/index.html
# Linux: xdg-open htmlcov/index.html
```

---

## 📋 Pre-Release Checklist

- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black roxx/`)
- [ ] Linting clean (`ruff check roxx/`)
- [ ] Version updated in:
  - [ ] `pyproject.toml`
  - [ ] `roxx/__init__.py`
  - [ ] `README.md`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Logo and assets included

---

## 🚀 Release Process

### 1. Tag Release

```bash
git tag -a v1.0.0-beta -m "Release 1.0.0-beta"
git push origin v1.0.0-beta
```

### 2. Build All Packages

```bash
# Python package
python -m build

# Windows exe
pyinstaller roxx.spec

# Linux packages (on Linux)
python setup.py bdist_deb
python setup.py bdist_rpm
```

### 3. Create GitHub Release

1. Go to GitHub Releases
2. Create new release from tag `v1.0.0-beta`
3. Upload artifacts:
   - `dist/roxx-1.0.0b0-py3-none-any.whl`
   - `dist/roxx.exe` (Windows)
   - `deb_dist/python3-roxx_1.0.0b0-1_all.deb` (Debian)
   - `dist/roxx-1.0.0b0-1.noarch.rpm` (RPM)

---

## 📝 Distribution Channels

### PyPI (Python Package Index)

```bash
twine upload dist/*.whl dist/*.tar.gz
```

Users install with:
```bash
pip install roxx
```

### GitHub Releases

- Attach pre-built binaries
- Users download directly

### Docker (Future)

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install .
CMD ["roxx"]
```

---

## 🔧 Build Troubleshooting

### PyInstaller Issues

**Missing modules**:
- Add to `hiddenimports` in `roxx.spec`

**Missing data files**:
- Add to `datas` in `roxx.spec`

**Large exe size**:
- Use `--exclude-module` for unused packages
- Enable UPX compression

### Package Issues

**Import errors**:
- Check `MANIFEST.in` includes all necessary files
- Verify `package_data` in `setup.py`

**Version conflicts**:
- Update `requires-python` in `pyproject.toml`
- Pin dependency versions if needed

---

## 📊 Build Sizes (Approximate)

| Package Type | Size | Notes |
|--------------|------|-------|
| Python wheel | ~50 KB | Requires Python installed |
| Windows exe | ~30 MB | Standalone, includes Python |
| Linux deb | ~50 KB | Requires Python installed |
| Docker image | ~200 MB | Includes Python runtime |

---

## 🎯 Continuous Integration

### GitHub Actions (Example)

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - run: pip install -e ".[dev]"
    - run: pytest
```
