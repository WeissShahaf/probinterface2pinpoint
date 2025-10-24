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

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Convert Cambridge Neurotech H7 probe
python src/cli.py convert -i data/input/cambridgeneurotech_h7.json -o output.json

# Run tests
python tests/test_cambridge_h7.py
```

## Documentation

- [Installation Guide](installation.md) - Setup instructions
- [Usage Guide](usage.md) - Detailed usage examples
- [File Structure](file_structure_tree.md) - Project organization
- [API Documentation](DOCUMENTATION.md) - Full documentation

## Supported Probes

### Tested with:
- **Cambridge Neurotech ASSY-276-H7** - 48 channels, 6×8 electrode grid
- **Neuropixels 1.0** - High-density silicon probe
- Custom probe configurations via JSON

## Example: Cambridge Neurotech H7

```python
from probe_converter import ProbeConverter

converter = ProbeConverter()
result = converter.convert_probe(
    spikeinterface_file="cambridgeneurotech_h7.json",
    electrode_csv="h7_electrodes.csv",
    output_file="h7_pinpoint.json"
)
print(f"Converted {result['probe']['electrode_count']} electrodes")
```

## Project Structure

```
probe_converter/
├── src/                # Source code
├── data/              # Data files
├── tests/             # Test scripts
├── docs/              # Documentation
└── config.yaml        # Configuration
```

## License

MIT License - See LICENSE file for details
