# Usage Guide

## Command Line Interface

### Basic Commands

#### Convert Single Probe
```bash
# Basic conversion - creates output_folder/probe_name/ with metadata.json, site_map.csv, model.obj
python src/cli.py convert -i input.json -o output_folder

# With electrode CSV mapping
python src/cli.py convert -i probe.json -e electrodes.csv -o output_folder

# With 3D model
python src/cli.py convert -i probe.json -s model.stl -o output_folder

# Full conversion with all inputs
python src/cli.py convert \
    -i probe.json \
    -e electrodes.csv \
    -s model.stl \
    -o output_folder
```

#### Batch Conversion
```bash
# Convert all JSON files in directory - creates multiple probe folders
python src/cli.py batch -i input_dir -o output_dir

# With custom pattern
python src/cli.py batch -i input_dir -o output_dir -p "*_probe.json"
```

#### Validate Output
```bash
# Validate probe folder
python src/cli.py validate output_folder/probe_name
```

### Command Options

```
Global Options:
  -v, --verbose         Enable verbose debug output
  -q, --quiet          Suppress all output except errors
  --log-file FILE      Save logs to file
  --config FILE        Use custom configuration file

Convert Options:
  -i, --input FILE     Input SpikeInterface JSON file (required)
  -e, --electrodes CSV Optional electrode mapping CSV
  -s, --stl FILE       Optional STL 3D model file
  -o, --output DIR     Output directory - creates probe_name/ folder (required)
  --no-validate        Skip output validation

Batch Options:
  -i, --input-dir DIR  Input directory (required)
  -o, --output-dir DIR Output directory (required)
  -p, --pattern GLOB   File pattern (default: *.json)
```

## Python API

### Basic Usage

```python
from converter import ProbeConverter

# Create converter instance
converter = ProbeConverter()

# Simple conversion - creates output_folder/probe_name/ folder
result = converter.convert_probe(
    spikeinterface_file="probe.json",
    output_file="output_folder"
)

# Access results
print(f"Probe: {result['probe_name']}")
print(f"Sites: {result['metadata']['sites']}")
```

### Advanced Usage

```python
# With all options
converter = ProbeConverter(config_path="custom_config.yaml")

result = converter.convert_probe(
    spikeinterface_file="probe.json",
    electrode_csv="electrodes.csv",
    stl_file="model.stl",
    output_file="output_folder",
    validate=True
)

# Access conversion results
print(f"Probe name: {result['probe_name']}")
print(f"Probe: {result['metadata']['name']}")
print(f"Sites: {result['metadata']['sites']}")
print(f"Shanks: {result['metadata']['shanks']}")
print(f"Producer: {result['metadata']['producer']}")

# Check if 3D model was generated
if result.get('model'):
    print("3D model included: model.obj")
```

### Batch Processing

```python
# Convert multiple files
converted = converter.batch_convert(
    input_dir="data/input",
    output_dir="data/output",
    pattern="*.json"
)

for file in converted:
    print(f"Converted: {file}")
```

### Custom Processing

```python
# Parse individual components
from parsers import SpikeInterfaceParser, CSVParser

# Load probe data
parser = SpikeInterfaceParser()
probe_data = parser.parse("probe.json")

# Load electrode mapping
csv_parser = CSVParser()
electrode_df = csv_parser.parse("electrodes.csv")

# Process with custom logic
from transformers import CoordinateTransformer

transformer = CoordinateTransformer()
transformed = transformer.transform_electrodes(
    probe_data['electrodes'],
    source_units='um',
    source_origin='tip'
)
```

## Examples

### Cambridge Neurotech H7 Probe

```python
# Convert H7 probe with full pipeline
converter = ProbeConverter()

result = converter.convert_probe(
    spikeinterface_file="data/input/cambridgeneurotech_h7.json",
    electrode_csv="data/input/cambridgeneurotech_h7_electrodes.csv",
    output_file="data/output/h7_pinpoint.json"
)

# Result contains 48 electrodes in 6x8 grid
```

### Neuropixels Probe

```python
# Convert Neuropixels 1.0
result = converter.convert_probe(
    spikeinterface_file="neuropixels_1.0.json",
    output_file="np1_pinpoint.json"
)
```

### Custom Configuration

```python
# Create custom config
config = Config()
config.set('conversion.coordinate_system.units', 'millimeters')
config.set('validation.strict_mode', True)

# Use with converter
converter = ProbeConverter()
converter.config = config
```

## Configuration

### Using config.yaml

```yaml
conversion:
  coordinate_system:
    units: micrometers  # um, mm, nm
    origin: tip         # tip, center, top
    axes: RAS          # RAS, XYZ
  auto_align: true

validation:
  strict_mode: false
  check_bounds: true
```

### Environment Variables

```bash
export PROBE_CONVERTER_UNITS=micrometers
export PROBE_CONVERTER_ORIGIN=center
export PROBE_CONVERTER_LOG_LEVEL=DEBUG

python src/cli.py convert -i input.json -o output.json
```

## Output Format

### Pinpoint JSON Structure

```json
{
  "format_version": "1.0",
  "timestamp": "2024-01-15T10:30:00",
  "probe": {
    "name": "ASSY-276-H7",
    "manufacturer": "Cambridge Neurotech",
    "electrode_count": 48,
    "dimensions": {
      "width": 225.0,
      "height": 100.0,
      "depth": 0.0
    },
    "coordinate_system": {
      "units": "micrometers",
      "origin": "tip",
      "axes": "RAS"
    }
  },
  "electrodes": [
    {
      "id": 0,
      "position": {"x": -7.5, "y": 100.0, "z": 0.0},
      "channel": 0,
      "shape": "circle",
      "shape_params": {"radius": 10}
    }
  ],
  "geometry": {
    "contour": [[-27.5, -10], [237.5, -10], ...]
  }
}
```

## Error Handling

### Common Errors and Solutions

#### Missing Input File
```python
try:
    result = converter.convert_probe("missing.json", "output.json")
except FileNotFoundError:
    print("Input file not found")
```

#### Invalid Format
```python
from validators import ProbeValidator

validator = ProbeValidator()
result = validator.validate(probe_data)
if not result.is_valid:
    print(f"Errors: {result.errors}")
```

#### Coordinate Issues
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check coordinate transformations
converter = ProbeConverter()
# Converter will log transformation details
```

## Tips and Best Practices

1. **Always validate input data** before conversion
2. **Use virtual environments** to avoid dependency conflicts
3. **Enable logging** for debugging complex conversions
4. **Check coordinate units** - most common source of errors
5. **Test with small datasets** before batch processing
6. **Back up original data** before batch conversions
7. **Review configuration** for project-specific settings

## Extending Functionality

### Add Custom Probe Type

```python
class CustomProbeParser:
    def parse(self, filepath):
        # Custom parsing logic
        return probe_data

# Register with converter
converter.custom_parser = CustomProbeParser()
```

### Custom Validation Rules

```python
def custom_validation(probe_data):
    # Custom validation logic
    return is_valid

converter.add_validator(custom_validation)
```
