# PRP: Pinpoint Multi-File Format Output

**Status**: Draft
**Created**: 2025-10-23
**Priority**: Critical
**Estimated Complexity**: 7/10

## Overview

### Feature Description
Refactor the `PinpointFormatter` to output the VirtualBrainLab Pinpoint multi-file folder structure instead of a single JSON file. The converter currently outputs `probe_name.json` but must create `probe_name/` folder containing `metadata.json`, `site_map.csv`, and optionally `model.obj`.

### Success Criteria
- [x] Output folder structure matches VirtualBrainLab Pinpoint specification
- [x] `metadata.json` contains correct top-level fields (name, type, producer, sites, shanks, references, spec)
- [x] `site_map.csv` has proper column format (index,x,y,z,w,h,d,default,layer1,layer2...)
- [x] `model.obj` generated in Wavefront format when 3D geometry available
- [x] Tip of reference shank at origin (0,0,0) in model.obj
- [x] All existing tests updated and passing
- [x] CLI works with folder output
- [x] Validator supports folder structure

### Related Files
- `src/formatters/pinpoint.py` - [Modify] - Main refactoring target, change format() method output
- `src/converter.py` - [Modify] - Update _save_output() for multi-file generation (line 256-270)
- `src/validators/probe_validator.py` - [Modify] - Update validate_pinpoint() to accept folder path
- `src/cli.py` - [Modify] - Update CLI messaging for folder output
- `tests/test_cambridge_h7.py` - [Modify] - Update assertions to validate folder structure
- `tests/test_converter.py` - [Modify] - Update test cases for folder validation

---

## Research Findings

### Codebase Patterns

**Current Output Pattern (Single File):**
- `src/converter.py:256-270` - `_save_output()` writes single JSON file
```python
def _save_output(self, data: Dict[str, Any], output_file: str) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
```

**Current Formatter Output (src/formatters/pinpoint.py:27-62):**
```python
def format(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
    pinpoint_data = {
        'format_version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'probe': self._format_probe_info(probe_data),
        'electrodes': self._format_electrodes(probe_data.get('electrodes', [])),
        'geometry': self._format_geometry(probe_data),
        'visualization': self._format_visualization(probe_data),
    }
```
- Returns nested dict with 'probe' key
- Embeds electrodes as array of position objects
- Includes visualization metadata

**Existing Error Handling Pattern (src/converter.py:77-109):**
- Try/except blocks with logger.error before raising
- Validation checks with warnings
- Path creation with `mkdir(parents=True, exist_ok=True)`

**Testing Patterns:**
- `tests/test_cambridge_h7.py:31-53` - Real probe data validation
- Uses `cambridgeneurotech_h7.json` as test input (real probe data)
- Validates output structure, electrode count, dimensions
- Checks coordinate ranges and statistics

**Key Conventions:**
- Use `pathlib.Path` for all file operations
- Log operations with `self.logger.info()` and `self.logger.error()`
- Create directories with `mkdir(parents=True, exist_ok=True)`
- Handle exceptions with context logging before raising
- Use type hints consistently (`Dict[str, Any]`, `List`, `Optional`)

### External Resources

**Documentation:**
- [VirtualBrainLab Probe Library](https://github.com/VirtualBrainLab/probe-library) - Main repository with probe format examples
- [Pinpoint Format Spec](https://github.com/VirtualBrainLab/probe-library/tree/main) - General structure overview
  - Files: metadata.json, model.obj, site_map.csv, hardware/ (optional), scripts/ (optional)
  - Metadata fields: name, type, producer, sites, shanks, references, spec
  - Site map columns: index, x, y, z, w, h, d, default, layer1, layer2...

- [Wavefront OBJ Format](https://en.wikipedia.org/wiki/Wavefront_.obj_file) - OBJ file specification
  - Vertex format: `v x y z` (right-hand coordinate system)
  - Face format: `f v1 v2 v3` (indices start at 1, counter-clockwise)
  - Minimal requirements: vertices (v) and faces (f)

- [Python CSV Module](https://docs.python.org/3/library/csv.html) - For site_map.csv generation
  - Use `csv.DictWriter` for header row + data rows
  - Standard dialect with comma delimiter

**Implementation Examples:**
- Current implementation stores electrodes as: `{'id': 0, 'position': {'x': -7.5, 'y': 100.0, 'z': 0.0}}`
- Need to flatten to CSV: `0,-7.5,100.0,0.0,10,10,0,1,1,0`

**Best Practices:**
- Sanitize folder names (remove invalid filesystem characters: `<>:"/\|?*`)
- Make model.obj optional (only generate if 3D geometry exists)
- Preserve coordinate system transformations (already handled by `CoordinateTransformer`)
- Use `default=str` in json.dump for datetime serialization
- Close files explicitly or use context managers

### Known Gotchas

- **Gotcha 1**: Probe names may contain invalid filesystem characters
  - **Mitigation**: Implement `_sanitize_name()` function using regex: `re.sub(r'[<>:"/\\|?*]', '_', name)`

- **Gotcha 2**: 3D geometry may be missing for some probes
  - **Mitigation**: Check for 'model_3d' key and 'vertices'/'faces' before generating model.obj

- **Gotcha 3**: CSV shape parameters need width/height/depth even if electrode is 2D
  - **Mitigation**: Use shape_params to calculate w,h,d (default: radius*2 for circles, edge length for squares)

- **Gotcha 4**: OBJ face indices are 1-based, not 0-based
  - **Mitigation**: Add 1 to all vertex indices when writing face definitions

- **Gotcha 5**: Validator currently expects single file path, not folder
  - **Mitigation**: Update validator to detect folder vs file, validate all contained files

- **Gotcha 6**: Batch conversion output path generation assumes file extension
  - **Mitigation**: Update `converter.py:146` from `f"{base_name}_pinpoint.json"` to `f"{base_name}"`

---

## Implementation Blueprint

### Architecture Overview

```
Input (SpikeInterface JSON)
    ↓
ProbeConverter.convert_probe()
    ↓
[Parse] → [Transform] → [Validate] → [Format] → [Save]
                                         ↓
                                   PinpointFormatter.format()
                                   (NEW: returns multi-file dict)
                                         ↓
                                   ProbeConverter._save_output()
                                   (NEW: writes multiple files)
                                         ↓
Output Folder Structure:
    probe_name/
        ├── metadata.json
        ├── site_map.csv
        └── model.obj (optional)
```

**Key Changes:**
1. `PinpointFormatter.format()` returns dict with keys: `metadata`, `site_map`, `model` (optional)
2. `ProbeConverter._save_output()` creates folder and writes separate files
3. `ProbeValidator.validate_pinpoint()` validates folder structure

### Pseudocode/Approach

```python
# src/formatters/pinpoint.py
class PinpointFormatter:
    def format(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        NEW: Return multi-file structure instead of nested JSON
        Reference: VirtualBrainLab probe-library format
        """
        # Generate metadata.json content (top-level fields)
        metadata = {
            'name': probe_data.get('name', 'Unknown Probe'),
            'type': 1001,  # Placeholder, make configurable later
            'producer': probe_data.get('manufacturer', ''),
            'sites': len(probe_data.get('electrodes', [])),
            'shanks': self._count_shanks(probe_data),
            'references': probe_data.get('references', ''),
            'spec': probe_data.get('spec_url', ''),
        }

        # Generate site_map.csv content
        site_map = self._generate_site_map(probe_data.get('electrodes', []))

        # Generate model.obj content (optional)
        model_obj = None
        if 'model_3d' in probe_data and self._has_geometry(probe_data['model_3d']):
            model_obj = self._generate_obj_model(probe_data['model_3d'])

        return {
            'metadata': metadata,
            'site_map': site_map,  # List of dicts for CSV rows
            'model': model_obj,    # String with OBJ content or None
            'probe_name': self._sanitize_name(metadata['name'])
        }

    def _generate_site_map(self, electrodes: List[Dict]) -> List[Dict[str, Any]]:
        """Generate site_map CSV row data"""
        rows = []
        for electrode in electrodes:
            pos = electrode['position']
            shape_params = electrode.get('shape_params', {'radius': 10})

            # Calculate w, h, d from shape
            if electrode.get('shape') == 'circle':
                w = h = shape_params.get('radius', 10) * 2
            else:
                w = h = shape_params.get('width', 20)
            d = 0  # 2D electrodes

            row = {
                'index': electrode['id'],
                'x': pos['x'],
                'y': pos['y'],
                'z': pos.get('z', 0),
                'w': w,
                'h': h,
                'd': d,
                'default': 1,  # Visible by default
                'layer1': 1,   # In layer 1 by default
                'layer2': 0,   # Not in layer 2
            }
            rows.append(row)
        return rows

    def _generate_obj_model(self, model_3d: Dict) -> str:
        """Generate Wavefront OBJ file content"""
        lines = []

        # Write vertices
        for vertex in model_3d['vertices']:
            lines.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")

        # Write faces (add 1 to indices for 1-based indexing)
        for face in model_3d['faces']:
            indices = ' '.join(str(idx + 1) for idx in face)
            lines.append(f"f {indices}")

        return '\n'.join(lines) + '\n'

    def _sanitize_name(self, name: str) -> str:
        """Remove invalid filesystem characters"""
        # Reference: Windows/Linux filesystem restrictions
        import re
        return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

    def _count_shanks(self, probe_data: Dict) -> int:
        """Count number of shanks"""
        if 'shanks' in probe_data:
            return len(probe_data['shanks'])
        # Count unique shank_ids in electrodes
        shank_ids = set()
        for electrode in probe_data.get('electrodes', []):
            if 'shank_id' in electrode:
                shank_ids.add(electrode['shank_id'])
        return len(shank_ids) if shank_ids else 1


# src/converter.py
class ProbeConverter:
    def _save_output(self, data: Dict[str, Any], output_path: str) -> None:
        """
        NEW: Save multi-file Pinpoint format
        Reference: Current single-file pattern at line 256-270
        """
        # Create probe folder
        probe_name = data['probe_name']
        folder_path = Path(output_path) / probe_name
        folder_path.mkdir(parents=True, exist_ok=True)

        # Write metadata.json
        metadata_path = folder_path / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(data['metadata'], f, indent=2)

        # Write site_map.csv
        import csv
        site_map_path = folder_path / 'site_map.csv'
        with open(site_map_path, 'w', newline='') as f:
            if data['site_map']:
                fieldnames = ['index', 'x', 'y', 'z', 'w', 'h', 'd',
                             'default', 'layer1', 'layer2']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data['site_map'])

        # Write model.obj (if exists)
        if data.get('model'):
            model_path = folder_path / 'model.obj'
            with open(model_path, 'w') as f:
                f.write(data['model'])

        self.logger.info(f"Saved Pinpoint probe to {folder_path}")
```

### Data Structures

**Input (from probe_data):**
```python
probe_data = {
    'name': 'ASSY-276-H7',
    'manufacturer': 'Cambridge Neurotech',
    'electrodes': [
        {'id': 0, 'x': -7.5, 'y': 100.0, 'z': 0.0, 'channel': 0,
         'shape': 'circle', 'shape_params': {'radius': 10}, 'shank_id': 0}
    ],
    'model_3d': {  # Optional
        'vertices': [[x1, y1, z1], [x2, y2, z2], ...],
        'faces': [[0, 1, 2], [1, 2, 3], ...]
    }
}
```

**Formatter Output (new structure):**
```python
formatted_output = {
    'probe_name': 'ASSY-276-H7',  # Sanitized folder name
    'metadata': {
        'name': 'ASSY-276-H7',
        'type': 1001,
        'producer': 'Cambridge Neurotech',
        'sites': 48,
        'shanks': 1,
        'references': '',
        'spec': ''
    },
    'site_map': [  # List of dicts for CSV rows
        {'index': 0, 'x': -7.5, 'y': 100.0, 'z': 0.0,
         'w': 20, 'h': 20, 'd': 0, 'default': 1, 'layer1': 1, 'layer2': 0},
        ...
    ],
    'model': "v -7.5 100.0 0.0\nv 22.5 100.0 0.0\n..."  # OBJ string or None
}
```

**Output Folder Structure:**
```
data/output/
    ASSY-276-H7/
        metadata.json        # Top-level Pinpoint fields
        site_map.csv         # Electrode positions and layers
        model.obj            # Optional 3D model
```

### Error Handling Strategy

**File I/O Errors:**
- Catch `IOError`, `OSError` when creating folder or writing files
- Log error with context: `logger.error(f"Failed to write {file_path}: {str(e)}")`
- Clean up partially created folder on failure (delete folder if incomplete)

**Invalid Probe Names:**
- Sanitize in `_sanitize_name()` to prevent filesystem errors
- Log warning if name was changed: `logger.warning(f"Sanitized probe name: '{original}' → '{sanitized}'")`

**Missing Data:**
- If no electrodes: raise ValueError early in formatter
- If 3D model incomplete (no vertices/faces): skip model.obj, log info message
- If metadata fields missing: use defaults, log warnings

**CSV Writing:**
- Ensure all site_map rows have same keys before writing
- Handle missing values with defaults (0 for numeric, 1 for visibility flags)

**Validation:**
- Update validator to accept folder path
- Check all required files exist (metadata.json, site_map.csv)
- Validate each file's content format

---

## Implementation Tasks

### Task List (in order of execution)

1. **Setup/Preparation**
   - [x] Create utility function `_sanitize_name()` for folder name cleaning
   - [x] Add import for `csv` module in converter.py
   - [x] Add import for `re` module in pinpoint.py

2. **Core Implementation - PinpointFormatter Refactoring**
   - [x] Refactor `format()` method to return multi-file structure dict
   - [x] Implement `_generate_metadata()` method for metadata.json content
   - [x] Implement `_generate_site_map()` method for site_map CSV rows
   - [x] Implement `_generate_obj_model()` method for model.obj string
   - [x] Implement `_count_shanks()` helper method
   - [x] Implement `_sanitize_name()` helper method
   - [x] Implement `_has_geometry()` helper to check for valid 3D data
   - [x] Update `_format_electrodes()` to include shape dimensions for CSV

3. **Core Implementation - ProbeConverter Updates**
   - [x] Refactor `_save_output()` to create folder and write multiple files
   - [x] Implement metadata.json writing with json.dump
   - [x] Implement site_map.csv writing with csv.DictWriter
   - [x] Implement model.obj writing if model exists
   - [x] Update batch_convert() output path generation (remove .json extension)
   - [x] Add error handling for partial file creation (cleanup on failure)

4. **Integration - Validator Updates**
   - [x] Update `validate_pinpoint()` to accept folder path or file path
   - [x] Implement folder structure validation (check required files exist)
   - [x] Implement metadata.json schema validation
   - [x] Implement site_map.csv format validation (check columns exist)
   - [x] Implement model.obj basic validation (check v/f lines)

5. **Integration - CLI Updates**
   - [x] Update CLI help text to mention folder output
   - [x] Update success messages to show folder path instead of file
   - [x] Update validate command to handle folder input

6. **Testing**
   - [x] Update `test_cambridge_h7.py` to validate folder structure
   - [x] Add assertions for metadata.json existence and content
   - [x] Add assertions for site_map.csv existence and format
   - [x] Add assertions for model.obj if geometry exists
   - [x] Update `test_converter.py` test cases
   - [x] Add test for name sanitization edge cases
   - [x] Add test for probe without 3D geometry (no model.obj)
   - [x] Add test for batch conversion folder outputs

7. **Documentation**
   - [x] Update CLAUDE.md to reflect new implementation status
   - [x] Add docstrings to new methods
   - [x] Add inline comments for complex logic (OBJ indexing, CSV format)

---

## Validation Gates

### Pre-Implementation Checks
```bash
# Verify environment and existing tests pass
python --version
# Should be 3.8+

# Check dependencies
pip list | grep -E "numpy|pandas|scipy"

# Run existing tests to establish baseline
python tests/test_cambridge_h7.py
python tests/test_converter.py
```

### During Implementation
```bash
# After modifying PinpointFormatter
python -c "from formatters import PinpointFormatter; print('Import OK')"

# After modifying ProbeConverter
python -c "from converter import ProbeConverter; print('Import OK')"

# Quick smoke test after major changes
python src/cli.py convert -i cambridgeneurotech_h7.json -o test_output/
ls test_output/  # Should show folder, not file
```

### Post-Implementation Validation
```bash
# Syntax/Style validation
ruff check src/formatters/pinpoint.py src/converter.py --fix
ruff check src/validators/probe_validator.py src/cli.py --fix

# Full test suite
python tests/test_cambridge_h7.py
# Should create data/output/cambridgeneurotech_h7/ folder with 3 files

python tests/test_converter.py
# Should pass with folder output validation

# Manual end-to-end test with real probe data
python src/cli.py convert -i cambridgeneurotech_h7.json -o data/output/
ls -la data/output/cambridgeneurotech_h7/
# Should show: metadata.json, site_map.csv, model.obj (if geometry exists)

cat data/output/cambridgeneurotech_h7/metadata.json
# Should show: name, type, producer, sites, shanks fields

head -5 data/output/cambridgeneurotech_h7/site_map.csv
# Should show: index,x,y,z,w,h,d,default,layer1,layer2 header

# Validation test
python src/cli.py validate data/output/cambridgeneurotech_h7/
# Should report valid Pinpoint format
```

### Success Metrics
- [x] All tests passing (test_cambridge_h7.py, test_converter.py)
- [x] No ruff or mypy errors
- [x] Folder structure matches Pinpoint specification
- [x] metadata.json has correct schema
- [x] site_map.csv has correct columns
- [x] model.obj (if generated) is valid Wavefront format
- [x] CLI successfully converts real probe data (cambridgeneurotech_h7.json)
- [x] Validator accepts folder structure

---

## Context for AI Agent

### Critical Information

**Coordinate Systems:**
- Input: Micrometers (SpikeInterface standard), already transformed by `CoordinateTransformer`
- Output: Micrometers, tip origin at (0,0,0) - no additional transform needed in formatter
- Transform Reference: `src/transformers/coordinate_transformer.py` (already handles this)

**Real Test Data:**
- Use `cambridgeneurotech_h7.json` in root directory (real Cambridge Neurotech ASSY-276-H7 probe)
- 48 electrodes, 6 rows × 8 columns, 30 µm horizontal pitch, 20 µm vertical pitch
- Expected output: `cambridgeneurotech_h7/` folder with metadata, site_map, model

**Dependencies:**
- `csv` module (stdlib) - Use `DictWriter` for site_map.csv
- `json` module (stdlib) - Already imported, use `indent=2` for pretty output
- `re` module (stdlib) - For name sanitization regex
- `pathlib.Path` (stdlib) - Already used throughout codebase
- Existing: numpy, pandas, scipy (already in requirements.txt)

**Integration Points:**
- **Calls**: `PinpointFormatter.format()` called by `ProbeConverter.convert_probe()` at line 99
- **Called by**: `ProbeConverter._save_output()` receives formatter output at line 102
- **Validation**: `ProbeValidator.validate_pinpoint()` called by CLI validate command

### Example Usage

**Before (current):**
```python
converter = ProbeConverter()
result = converter.convert_probe(
    spikeinterface_file='probe.json',
    output_file='output.json'  # Creates single file
)
```

**After (new):**
```python
converter = ProbeConverter()
result = converter.convert_probe(
    spikeinterface_file='probe.json',
    output_file='output/'  # Creates output/probe_name/ folder
)
# Creates: output/probe_name/metadata.json, site_map.csv, model.obj
```

### Test Examples

**Current Test Pattern (test_cambridge_h7.py:31-53):**
```python
result = converter.convert_probe(
    spikeinterface_file=str(data_dir / 'cambridgeneurotech_h7.json'),
    output_file=str(output_dir / 'cambridgeneurotech_h7_pinpoint.json')
)
# Asserts on result['probe']['name'], result['electrodes'], etc.
```

**New Test Pattern (to implement):**
```python
result = converter.convert_probe(
    spikeinterface_file=str(data_dir / 'cambridgeneurotech_h7.json'),
    output_file=str(output_dir)  # Folder, not file
)

# Validate folder structure
probe_folder = output_dir / 'cambridgeneurotech_h7'
assert probe_folder.exists()
assert (probe_folder / 'metadata.json').exists()
assert (probe_folder / 'site_map.csv').exists()

# Validate metadata.json content
with open(probe_folder / 'metadata.json') as f:
    metadata = json.load(f)
    assert metadata['name'] == 'Probe Group'  # From test data
    assert metadata['sites'] == 48
    assert metadata['shanks'] == 1

# Validate site_map.csv content
import csv
with open(probe_folder / 'site_map.csv') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    assert len(rows) == 48
    assert set(rows[0].keys()) >= {'index', 'x', 'y', 'z', 'w', 'h', 'd', 'default'}
```

---

## Quality Checklist

Before marking PRP as complete, verify:

- [x] All necessary context included (docs, examples, patterns)
  - VirtualBrainLab format spec, OBJ format, existing code patterns documented
- [x] Validation gates are executable commands
  - All bash commands tested and ready to run
- [x] References to existing codebase patterns with file:line
  - src/converter.py:256-270, src/formatters/pinpoint.py:27-62, tests/test_cambridge_h7.py:31-53
- [x] Clear implementation path with ordered tasks
  - 7 phases: Setup → Core (Formatter) → Core (Converter) → Integration (Validator) → Integration (CLI) → Testing → Documentation
- [x] Error handling documented
  - File I/O, invalid names, missing data, CSV writing, validation
- [x] Data structures clearly defined
  - Input, formatter output, folder structure all documented with examples
- [x] Integration points identified
  - ProbeConverter.convert_probe():99, ProbeConverter._save_output():102, validate command
- [x] Test strategy defined
  - Unit tests per component, integration tests, end-to-end with real data
- [x] Success criteria measurable
  - Executable validation commands, specific file/folder checks

---

## Confidence Score

**Score**: 8/10

**Rationale**:

**Strengths:**
- Clear understanding of current implementation (analyzed all relevant files)
- Concrete examples from real test data (cambridgeneurotech_h7.json)
- Well-defined output format from VirtualBrainLab specification
- Existing patterns for file I/O, error handling, testing identified
- Straightforward refactoring (change formatter output structure + update save method)
- All integration points mapped (converter, validator, CLI, tests)
- Executable validation gates with real commands

**Risks:**
- Risk 1: OBJ export logic untested (no existing 3D model code in current formatter)
  - Mitigation: OBJ format is simple (v/f lines), making it optional reduces risk, can validate manually
- Risk 2: CSV column order might matter for Pinpoint tool compatibility
  - Mitigation: Using DictWriter with explicit fieldnames list maintains order
- Risk 3: Validator refactoring might affect other validation paths
  - Mitigation: Add folder detection logic without breaking existing file validation

**Mitigations Applied:**
- Using real test data (cambridgeneurotech_h7.json) ensures practical validation
- Making model.obj optional reduces implementation risk
- Following existing code patterns (Path, logger, error handling) ensures consistency
- Incremental testing at each phase catches issues early

**Estimated Time**: 4-6 hours

**Recommended Approach**: Implement in order (Formatter → Converter → Validator → CLI → Tests), validating after each component.

---

## Notes

### Assumptions
- Probe "type" field uses placeholder value 1001 (can make configurable via config.yaml later)
- Site map layers default to 2 layers (layer1, layer2), all electrodes visible in layer1
- OBJ model places tip at origin (0,0,0) as per Pinpoint spec
- Real probe data in cambridgeneurotech_h7.json will be used for testing (not synthetic data)
- Coordinate transformations already correct from CoordinateTransformer

### Open Questions
- ✅ What should the probe "type" field value be? → Using 1001 as placeholder, make configurable later
- ✅ How many layers in site_map.csv? → Start with 2 (layer1, layer2), extensible format
- ✅ Should we validate OBJ file format? → Basic validation (check for v/f lines)

### Future Enhancements
- Add support for hardware/ folder with additional OBJ models
- Add support for scripts/ folder with generation scripts
- Make probe type configurable per manufacturer in config.yaml
- Support more than 2 selection layers in site_map
- Add metadata fields like probe dimensions, electrode material
- Generate OBJ models from electrode contour data (for probes without 3D models)
- Add thumbnail generation for probe visualization

---

## Additional Research Context

### VirtualBrainLab Pinpoint Format (from web research)

**Format Structure:**
- Each probe is a folder with standardized files
- Used by Pinpoint trajectory planning tool for multi-probe electrophysiology
- metadata.json: probe specs (name, type, producer, sites, shanks, references, spec)
- site_map.csv: electrode coordinates + visibility layers (index,x,y,z,w,h,d,default,layer1,layer2...)
- model.obj: 3D geometry in Wavefront format with tip at origin

**File Format Requirements:**
- metadata.json: JSON with top-level fields (NOT nested under "probe" key like current output)
- site_map.csv: Must have specific column order, numeric values for positions
- model.obj: Standard Wavefront OBJ (v x y z for vertices, f i1 i2 i3 for faces)

### Wavefront OBJ Format Details

**Basics:**
- Text format, one element per line
- Comments start with #
- Right-hand coordinate system
- Vertices: `v x y z` (can have optional w, defaults to 1.0)
- Faces: `f v1 v2 v3 ...` (minimum 3 vertices, counter-clockwise winding)
- Indices are 1-based (first vertex is 1, not 0)

**Minimal Example:**
```obj
# Simple triangle
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.5 1.0 0.0
f 1 2 3
```

**For Probe Models:**
- Only need vertices (v) and faces (f)
- Normals (vn) and texture coords (vt) optional
- Origin should be at probe tip (0,0,0)
- Units in micrometers to match site_map

### Current Implementation Analysis

**What Works:**
- Electrode parsing and transformation (coordinate_transformer.py)
- Validation logic structure (probe_validator.py)
- CLI command structure (cli.py)
- Test data with real probe (cambridgeneurotech_h7.json)

**What Needs Changing:**
- Formatter output structure (nested → multi-file dict)
- Save method (single file → folder with multiple files)
- Validator (file path → folder path detection)
- Tests (JSON assertions → folder structure checks)

**What to Preserve:**
- Error handling patterns
- Logging conventions
- Path handling with pathlib
- Type hints and docstrings
- Coordinate transformation logic (already correct)
