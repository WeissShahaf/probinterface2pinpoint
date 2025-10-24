# Feature: Pinpoint Multi-File Format Output

**Type**: Refactor | Enhancement
**Priority**: Critical
**Requester**: Project Requirements
**Date**: 2025-10-23

## Problem Statement

Currently, the `PinpointFormatter` outputs a **single JSON file** with embedded probe metadata, electrode arrays, and geometry data. However, the VirtualBrainLab Pinpoint format specification requires a **multi-file folder structure** with:
- `metadata.json` - Probe metadata
- `site_map.csv` - Electrode coordinates and selection layers
- `model.obj` - 3D model in Wavefront OBJ format (optional)
- `scripts/` - Generation scripts (optional)
- `hardware/` - Additional hardware models (optional)

**Current Output**: `output/probe_name.json`
**Required Output**: `output/probe_name/` folder with files above

## Proposed Solution

Refactor the `PinpointFormatter` class to:
1. Generate `metadata.json` with top-level Pinpoint fields (not nested under "probe" key)
2. Export electrode data to `site_map.csv` with proper column format
3. Export 3D geometry to `model.obj` in Wavefront format (if 3D data available)
4. Create proper folder structure instead of single file
5. Update `ProbeConverter._save_output()` to handle multi-file output

## Requirements

### Functional Requirements
- [ ] FR1: Create output folder named after probe (sanitized name)
- [ ] FR2: Generate `metadata.json` with fields: name, type, producer, sites, shanks, references, spec
- [ ] FR3: Generate `site_map.csv` with columns: index, x, y, z, w, h, d, default, layer1, layer2...
- [ ] FR4: Export `model.obj` if 3D geometry data exists
- [ ] FR5: Place tip of reference shank at origin (0,0,0) in model.obj
- [ ] FR6: Maintain backward compatibility with validation logic

### Non-Functional Requirements
- [ ] NFR1: Follow existing code patterns in codebase
- [ ] NFR2: Preserve all existing functionality (just change output format)
- [ ] NFR3: Update CLI to work with folder output instead of file
- [ ] NFR4: Update tests to validate folder structure

## User Stories

**As a** neuroscience researcher
**I want** the converter to output Pinpoint-format probe folders
**So that** I can directly import probes into VirtualBrainLab Pinpoint

**Acceptance Criteria:**
- Given a SpikeInterface probe JSON
- When I run `python src/cli.py convert -i input.json -o output_folder`
- Then I get `output_folder/probe_name/` with metadata.json, site_map.csv, and model.obj (if applicable)

## Input/Output Specification

### Input (unchanged)
```json
{
  "specification": "probeinterface",
  "probes": [{
    "ndim": 2,
    "si_units": "um",
    "annotations": {"name": "ASSY-276-H7", "manufacturer": "Cambridge Neurotech"},
    "contact_positions": [[x1, y1], [x2, y2], ...],
    "contact_shapes": "circle",
    "contact_shape_params": {"radius": 10},
    "device_channel_indices": [0, 1, 2, ...]
  }]
}
```

### Output (new folder structure)
```
output_folder/
  ASSY-276-H7/
    metadata.json
    site_map.csv
    model.obj (optional)
```

**metadata.json**:
```json
{
  "name": "ASSY-276-H7",
  "type": 1001,
  "producer": "Cambridge Neurotech",
  "sites": 48,
  "shanks": 1,
  "references": "https://doi.org/...",
  "spec": "https://www.cambridgeneurotech.com/..."
}
```

**site_map.csv**:
```csv
index,x,y,z,w,h,d,default,layer1,layer2
0,-7.5,100.0,0.0,10,10,0,1,1,0
1,22.5,100.0,0.0,10,10,0,1,1,0
```

**model.obj**: Wavefront OBJ format
```
v x1 y1 z1
v x2 y2 z2
...
f 1 2 3
f 2 3 4
...
```

## Examples

### Example 1: Basic Conversion (existing test probe)
```bash
# Command
python src/cli.py convert -i cambridgeneurotech_h7.json -o data/output

# Expected Output Structure
data/output/
  cambridgeneurotech_h7/
    metadata.json
    site_map.csv
    model.obj
```

### Example 2: Batch Conversion
```bash
# Command
python src/cli.py batch -i data/input -o data/output

# Expected Output
data/output/
  probe1/
    metadata.json
    site_map.csv
  probe2/
    metadata.json
    site_map.csv
```

## Similar Implementations

### Internal References
- `src/formatters/pinpoint.py` - Current PinpointFormatter (needs refactoring)
- `src/converter.py:ProbeConverter._save_output()` - Needs update for folder output
- `tests/test_cambridge_h7.py` - Test pattern to follow, update for folder validation

### External References
- [VirtualBrainLab Probe Library](https://github.com/VirtualBrainLab/probe-library/tree/main) - Reference format
- [Pinpoint Spec Example](https://github.com/VirtualBrainLab/probe-library/tree/main/Neuropixels/NP1.0) - Real probe folder
- [Wavefront OBJ Format](https://en.wikipedia.org/wiki/Wavefront_.obj_file) - OBJ file format spec
- [Python CSV module](https://docs.python.org/3/library/csv.html) - For site_map.csv generation

## Technical Considerations

### Dependencies
- `csv` module (stdlib) - For site_map.csv generation
- `pathlib.Path` (stdlib) - For folder creation
- Existing dependencies maintained

### Constraints
- Must maintain coordinate system transformations
- Must preserve metadata from input
- Must handle probes without 3D geometry (skip model.obj)
- Must sanitize probe names for folder names (remove invalid chars)

### Risks
- Risk 1: Breaking existing validation logic that expects single JSON file
  - Mitigation: Update validator to accept folder path
- Risk 2: Missing 3D geometry data for model.obj
  - Mitigation: Make model.obj optional, only generate if geometry exists
- Risk 3: Probe name contains invalid filesystem characters
  - Mitigation: Implement name sanitization function

## Testing Strategy

### Unit Tests
- Test metadata.json generation with correct schema
- Test site_map.csv generation with correct columns
- Test model.obj generation from geometry data
- Test folder creation and naming
- Test name sanitization for invalid characters

### Integration Tests
- Test full conversion pipeline with Cambridge H7 probe
- Test batch conversion creates multiple folders
- Test validation works with folder structure
- Test CLI commands with new folder output

### Edge Cases
- Probe with no 3D geometry (skip model.obj)
- Probe with special characters in name
- Probe with missing optional metadata fields
- Empty output folder (create if not exists)

## Success Metrics

How will we know this feature is successful?
- Output matches VirtualBrainLab Pinpoint format specification
- All existing tests updated and passing
- Can import generated probes into Pinpoint successfully
- Backward compatibility maintained (validation, CLI interface)

## Out of Scope

- `hardware/` folder generation (optional feature, future enhancement)
- `scripts/` folder generation (optional feature, future enhancement)
- Multi-shank probe support (implement basic version first)
- Advanced OBJ features (textures, materials) - basic vertex/face only

## Open Questions

- [x] What should the probe "type" field value be? (Default to 1001 as placeholder)
- [x] How to handle probes with multiple shanks? (Start with single-shank, extend later)
- [x] Should we validate generated OBJ files? (Basic validation for now)

## Notes

**From CLAUDE.md**:
> The `PinpointFormatter` ([src/formatters/pinpoint.py](src/formatters/pinpoint.py)) needs refactoring to:
> 1. Generate `metadata.json` with Pinpoint-spec fields (not nested probe object)
> 2. Generate `site_map.csv` from electrodes array
> 3. Export `model.obj` from 3D model data (if available)
> 4. Create output directory structure instead of single file
> 5. Update `ProbeConverter._save_output()` to handle multi-file output

**Critical Files to Modify**:
- `src/formatters/pinpoint.py:PinpointFormatter.format()` - Main refactor target
- `src/converter.py:ProbeConverter._save_output()` - Update for folder output
- `src/validators/probe_validator.py` - Update to validate folder structure
- `tests/test_cambridge_h7.py` - Update assertions for folder structure
- `tests/test_converter.py` - Update test cases

**Coordinate System**:
- Input: micrometers (SpikeInterface standard)
- Output: micrometers, tip origin at (0,0,0)
- Transform handled by `CoordinateTransformer` before formatting
