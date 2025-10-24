# Probe Converter

Convert silicone probe data from SpikeInterface/probeinterface_library format to VirtualBrainLab Pinpoint format.

## Features

- 🔄 Convert probe geometry and electrode configurations between formats
- 📊 Support for Cambridge Neurotech, Neuropixels, and other probe types
- 🗂️ Process CSV electrode mappings and STL 3D models
- ⚙️ Automatic coordinate system transformations
- ✅ Comprehensive validation and error handling
- 🚀 Batch processing capabilities
- 📁 Command-line interface and Python API

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/probinterface2pinpoint.git
cd probinterface2pinpoint

# Install dependencies
pip install -r requirements.txt
```

## Command Line Usage

### Convert Single Probe

```bash
python src/cli.py convert -i <input.json> -o <output_folder>
```

**Required Inputs:**
- `-i, --input`: SpikeInterface JSON file (required)
- `-o, --output`: Output directory where probe folder will be created (required)

**Optional Inputs:**
- `-e, --electrodes`: CSV file with electrode mapping (optional)
- `-s, --stl`: STL file with 3D model (optional)
- `--no-validate`: Skip validation (optional)
- `--config`: Path to custom configuration file (optional)
- `-v, --verbose`: Enable verbose logging (optional)
- `-q, --quiet`: Suppress output except errors (optional)
- `--log-file`: Write logs to file (optional)

**Output Structure:**
```
output_folder/
└── probe_name/
    ├── metadata.json      # Probe metadata (name, type, producer, sites, shanks, references, spec)
    ├── site_map.csv       # Electrode positions and visibility layers
    └── model.obj          # 3D model (if STL input provided or geometry available)
```

**Example:**
```bash
# Basic conversion (SpikeInterface JSON only)
python src/cli.py convert -i data/input/ASSY-276-H7.json -o data/output

# With all optional inputs
python src/cli.py convert \
  -i data/input/ASSY-276-H7.json \
  -e data/input/electrodes.csv \
  -s data/input/model.stl \
  -o data/output \
  -v
```

### Batch Convert Multiple Probes

```bash
python src/cli.py batch -i <input_dir> -o <output_dir>
```

**Required Inputs:**
- `-i, --input-dir`: Directory containing SpikeInterface JSON files (required)
- `-o, --output-dir`: Output directory (required)

**Optional Inputs:**
- `-p, --pattern`: File pattern to match (default: `*.json`)
- `--config`: Path to custom configuration file (optional)
- `-v, --verbose`: Enable verbose logging (optional)

**Input Directory Structure:**
```
input_dir/
├── spikeinterface/
│   ├── probe1.json
│   └── probe2.json
├── csv/              # Optional - matched by filename
│   └── probe1.csv
└── stl/              # Optional - matched by filename
    └── probe1.stl
```

**Output Structure:**
```
output_dir/
├── probe1/
│   ├── metadata.json
│   ├── site_map.csv
│   └── model.obj
└── probe2/
    ├── metadata.json
    └── site_map.csv
```

**Example:**
```bash
python src/cli.py batch -i data/input -o data/output -v
```

### Validate Converted Probe

```bash
python src/cli.py validate <probe_folder>
```

**Required Inputs:**
- `path`: Path to probe folder or metadata.json file (required)

**Example:**
```bash
python src/cli.py validate data/output/ASSY-276-H7
```

## Quick Start

```bash
# Convert Cambridge Neurotech H7 probe
python src/cli.py convert -i data/input/cambridgeneurotech/ASSY-276-H7.json -o data/output

# Batch convert all Cambridge Neurotech probes
python src/cli.py batch -i data/input/cambridgeneurotech -o data/output

# Validate output
python src/cli.py validate data/output/ASSY-276-H7

# Run tests
python tests/test_cambridge_h7.py
```

## Output Format Details

The converter creates a **VirtualBrainLab Pinpoint multi-file format** in a folder structure:

### metadata.json
Contains probe metadata in JSON format:
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

### site_map.csv
Electrode coordinates and visibility layers:
```csv
index,x,y,z,w,h,d,default,layer1,layer2
0,-7.5,100.0,0.0,20.0,20.0,0.0,1,1,0
1,22.5,100.0,0.0,20.0,20.0,0.0,1,1,0
...
```

**Columns:**
- `index` - Electrode ID (0-indexed)
- `x,y,z` - Position in micrometers, relative to probe tip
- `w,h,d` - Width, height, depth (electrode dimensions)
- `default` - Default visibility (1=visible, 0=hidden)
- `layer1,layer2,...` - Selection layer visibility

### model.obj (Optional)
Wavefront OBJ 3D model with probe tip at origin (0,0,0). Generated when:
- STL file is provided as input, OR
- ProbeInterface data includes `probe_planar_contour` geometry

## Python API

```python
from pathlib import Path
from converter import ProbeConverter

# Initialize converter
converter = ProbeConverter()

# Convert single probe
result = converter.convert_probe(
    spikeinterface_file="data/input/ASSY-276-H7.json",
    electrode_csv="data/input/electrodes.csv",  # Optional
    stl_file="data/input/model.stl",            # Optional
    output_file="data/output",
    validate=True
)

# Access results
print(f"Probe: {result['probe_name']}")
print(f"Sites: {result['metadata']['sites']}")
print(f"Shanks: {result['metadata']['shanks']}")

# Batch convert
converted = converter.batch_convert(
    input_dir="data/input",
    output_dir="data/output",
    pattern="*.json"
)
print(f"Converted {len(converted)} probes")

# Validate output
is_valid = converter.validate_output("data/output/ASSY-276-H7")
```

## Input Format

The converter accepts **SpikeInterface/probeinterface format** JSON files:

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
      "device_channel_indices": [0, 1, 2, ...]
    }
  ]
}
```

**References:**
- [ProbeInterface Documentation](https://probeinterface.readthedocs.io/)
- [Probe Library](https://github.com/SpikeInterface/probeinterface_library/)
- [VirtualBrainLab Pinpoint Format](https://github.com/VirtualBrainLab/probe-library/)

## Tested Probes

- **Cambridge Neurotech ASSY-276-H7** - 48 channels, 6×8 electrode grid ✅
- **Cambridge Neurotech ASSY-77-H7** - 16 channels ✅
- **Neuropixels 1.0** - High-density silicon probe ✅
- **Neuropixels 2.0** - Ultra-high density probe ✅
- Custom probe configurations via JSON ✅

## Documentation

- [Installation Guide](installation.md) - Setup instructions
- [Usage Guide](usage.md) - Detailed usage examples
- [File Structure](file_structure_tree.md) - Project organization
- [Full Documentation](DOCUMENTATION.md) - Comprehensive reference
- [CLAUDE.md](CLAUDE.md) - Developer guide for Claude Code

## License

MIT License
