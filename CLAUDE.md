# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **probe converter** tool that transforms neural probe data from SpikeInterface/probeinterface format to VirtualBrainLab Pinpoint format. The converter handles electrode positions, 3D geometry, coordinate transformations, and validation.

**Pinpoint definition**: A probe is a 3D object with one or more shanks, each of which have sites (electrodes) on them.

## ✅ Current Implementation Status

**The converter now outputs the VirtualBrainLab Pinpoint multi-file format.**

### Output Format (VirtualBrainLab Pinpoint)

The converter creates a probe folder with these files:

| File | Description | Status |
|------|-------------|--------|
| `metadata.json` | Probe metadata in JSON format (name, type, producer, sites, shanks, references, spec) | ✅ Implemented |
| `site_map.csv` | Electrode coordinates relative to tip and selection layers (columns: index, x, y, z, w, h, d, default, layer1, layer2...) | ✅ Implemented |
| `model.obj` | 3D model of probe shanks with tip of reference shank at origin | ✅ Implemented (when 3D geometry available) |
| `hardware/*.obj` | (Optional) 3D models of additional hardware, origin at tip of reference shank | 🔜 Future enhancement |
| `scripts/` | (Optional) Scripts used to generate probe 3D model or site_map for reproducibility | 🔜 Future enhancement |

**Reference**: https://github.com/VirtualBrainLab/probe-library/tree/main

### Example Output Structure

```
data/output/
└── Probe Group/
    ├── metadata.json        # Pinpoint metadata (name, type, producer, sites, shanks, references, spec)
    └── site_map.csv         # 48 sites with positions and visibility layers
```

**metadata.json** format:
```json
{
  "name": "Probe Group",
  "type": 1001,
  "producer": "Cambridge Neurotech",
  "sites": 48,
  "shanks": 1,
  "references": "",
  "spec": ""
}
```

**site_map.csv** format:
```csv
index,x,y,z,w,h,d,default,layer1,layer2
0,-7.5,100.0,0.0,20.0,20.0,0.0,1,1,0
1,22.5,100.0,0.0,20.0,20.0,0.0,1,1,0
...
```

### Implementation Details

- **PRP Document**: See `PRPs/pinpoint-multifile-format.md` for complete implementation specifications
- **Implemented**: 2025-10-23
- **Changes**: Refactored `PinpointFormatter` and `ProbeConverter._save_output()` to generate multi-file structure
- **Tests**: All tests passing with folder structure validation

## Input Format References

**ProbeInterface** (Input format):
- GitHub repo: https://github.com/SpikeInterface/probeinterface
- Documentation: https://probeinterface.readthedocs.io/
- Probe library: https://github.com/SpikeInterface/probeinterface_library/tree/main
- Examples: https://probeinterface.readthedocs.io/en/main/examples/ex_10_get_probe_from_library.html
- Format spec: https://probeinterface.readthedocs.io/en/main/format_spec.html


## Key Commands

### Running Conversions

```bash
# Convert single probe - outputs probe_name/ folder with metadata.json, site_map.csv, model.obj
python src/cli.py convert -i <input.json> -o <output_folder>

# With optional electrode CSV and 3D model
python src/cli.py convert -i probe.json -e electrodes.csv -s model.stl -o output_folder

# Batch conversion - creates multiple probe folders
python src/cli.py batch -i data/input -o data/output

# Validate output - validates folder structure
python src/cli.py validate "output_folder/probe_name"
```

### Testing

```bash
# Run specific test
python tests/test_cambridge_h7.py

# Run converter test
python tests/test_converter.py

# Tests use pytest (if installed)
pytest tests/
```

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Enable verbose logging for debugging
python src/cli.py convert -i input.json -o output.json -v

# Use custom config
python src/cli.py convert -i input.json -o output.json --config custom_config.yaml
```

## Architecture

### Data Flow Pipeline

The conversion follows a 5-stage pipeline orchestrated by `ProbeConverter`:

1. **Parse** ([src/parsers/](src/parsers/)) - Parse input files (SpikeInterface JSON, CSV electrode mappings, STL 3D models)
2. **Transform** ([src/transformers/](src/transformers/)) - Apply coordinate transformations and geometry processing
3. **Validate** ([src/validators/](src/validators/)) - Check data integrity and format compliance
4. **Format** ([src/formatters/](src/formatters/)) - Convert to Pinpoint multi-file format
5. **Save** - Create probe folder and write metadata.json, site_map.csv, and model.obj (if available)

### Core Components

**Converter** ([src/converter.py](src/converter.py))
- Main `ProbeConverter` class orchestrates the entire pipeline
- `convert_probe()` - single file conversion
- `batch_convert()` - directory processing
- Private methods `_parse_inputs()`, `_transform_data()`, `_save_output()` handle pipeline stages

**Parsers** ([src/parsers/](src/parsers/))
- `SpikeInterfaceParser` - Parses SpikeInterface JSON format, handles multiple probe formats (single probe, probe groups, probe lists)
- `CSVParser` - Parses electrode mapping CSVs
- `STLParser` - Loads and processes 3D mesh models
- Each parser returns standardized dictionaries with electrode positions and metadata

**Transformers** ([src/transformers/](src/transformers/))
- `CoordinateTransformer` - Transforms electrode coordinates between coordinate systems (units, origin, axes convention)
- `GeometryTransformer` - Processes 3D models, aligns with electrode positions

**Formatters** ([src/formatters/pinpoint.py](src/formatters/pinpoint.py))
- `PinpointFormatter` - Generates multi-file Pinpoint format structure
- `format()` returns dict with keys: `probe_name`, `metadata`, `site_map`, `model` (optional)
- `_generate_metadata()` creates metadata.json content (name, type, producer, sites, shanks, references, spec)
- `_generate_site_map()` creates site_map.csv rows with electrode positions and visibility layers
- `_generate_obj_model()` exports 3D geometry to Wavefront OBJ format (when available)
- `_sanitize_name()` removes invalid filesystem characters for folder names
- `_count_shanks()` determines number of shanks from probe data

**Validators** ([src/validators/probe_validator.py](src/validators/probe_validator.py))
- `ProbeValidator` - Validates data completeness and format compliance
- Returns validation results with errors/warnings

**Utilities**
- `Config` ([src/utils/config.py](src/utils/config.py)) - Configuration management from YAML
- `setup_logger` ([src/utils/logger.py](src/utils/logger.py)) - Logging setup

### Configuration

Settings in [config.yaml](config.yaml) control:
- **Coordinate system**: units (micrometers/millimeters), origin (tip/center/top), axes convention (RAS/XYZ)
- **Validation**: strict mode, bounds checking, warning limits
- **Processing**: mesh simplification, electrode matching tolerance
- **Output**: metadata inclusion, format version

## Code Patterns

### Adding Support for New Input Formats

1. Create new parser in `src/parsers/` inheriting pattern from `SpikeInterfaceParser`
2. Implement `parse(filepath)` method returning standardized dict with `electrodes` array
3. Register parser in `ProbeConverter.__init__()` and update `_parse_inputs()` to use it

### Electrode Data Structure

All parsers must return electrodes as list of dicts with:
```python
{
    'id': int,           # Required
    'x': float,          # Required - position in micrometers
    'y': float,          # Required
    'z': float,          # Optional (default 0)
    'channel': int,      # Optional - device channel
    'shape': str,        # Optional - 'circle', 'square'
    'shape_params': {},  # Optional - shape-specific parameters
    'shank_id': int,     # Optional - for multi-shank probes
}
```

### Coordinate System Conventions

- Input: typically micrometers (SpikeInterface standard)
- Output: configurable via `config.yaml` (default: micrometers, tip origin, RAS axes)
- Transform in `CoordinateTransformer` before formatting
- All coordinate metadata stored in output for traceability

### Error Handling

- All major operations wrapped in try/except blocks
- Errors logged with context before raising
- CLI exits with code 1 on errors
- Validation failures logged as warnings unless strict_mode enabled

## Format Specifications

### ProbeInterface Input Format (JSON)

```json
{
  "specification": "probeinterface",
  "version": "0.2.21",
  "probes": [
    {
      "ndim": 2,
      "si_units": "um",
      "annotations": {
        "name": "ASSY-276-H7",
        "manufacturer": "Cambridge Neurotech"
      },
      "contact_positions": [
        [-7.5, 100.0],
        [22.5, 100.0]
      ],
      "contact_shapes": "circle",
      "contact_shape_params": {"radius": 10},
      "probe_planar_contour": [[-27.5, -10.0], [237.5, -10.0], ...],
      "device_channel_indices": [0, 1, 2, ...]
    }
  ]
}
```

### Pinpoint Target Format

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
- Columns: index (electrode ID), x/y/z (position in μm), w/h/d (width/height/depth), default (visibility), layer1/layer2... (selection layers)

**model.obj**: Wavefront OBJ format with probe tip at origin (0,0,0)

## Important Notes

- The `src/` directory is added to Python path in CLI and test scripts using `sys.path.insert(0, str(Path(__file__).parent / 'src'))`
- Imports in `src/` modules use relative imports (e.g., `from parsers import ...`)
- Batch conversion expects directory structure: `input_dir/spikeinterface/*.json`, optional `input_dir/csv/*.csv` and `input_dir/stl/*.stl`
- 3D models are simplified if face count exceeds `max_mesh_faces` config setting (default 10,000)
- When both CSV and SpikeInterface data exist, CSV data is merged/overlaid onto SpikeInterface data in `_merge_electrode_data()`
