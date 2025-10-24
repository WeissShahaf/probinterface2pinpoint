# Project File Structure

```
probe_converter/
│
├── src/                              # Source code directory
│   ├── __init__.py                  # Main package initialization
│   ├── converter.py                 # Main ProbeConverter class
│   ├── cli.py                       # Command-line interface
│   │
│   ├── parsers/                     # Input format parsers
│   │   ├── __init__.py
│   │   ├── spikeinterface.py       # SpikeInterface JSON parser
│   │   ├── csv_parser.py           # CSV electrode mapping parser
│   │   └── stl_parser.py           # STL/3D model parser
│   │
│   ├── formatters/                  # Output format generators
│   │   ├── __init__.py
│   │   └── pinpoint.py             # Pinpoint format generator
│   │
│   ├── transformers/                # Coordinate/geometry transformers
│   │   ├── __init__.py
│   │   ├── coordinates.py          # Coordinate system transformations
│   │   └── geometry.py             # 3D geometry transformations
│   │
│   ├── validators/                  # Data validation modules
│   │   ├── __init__.py
│   │   └── probe_validator.py      # Probe data validator
│   │
│   └── utils/                       # Utility modules
│       ├── __init__.py
│       ├── config.py               # Configuration management
│       └── logger.py               # Logging utilities
│
├── data/                            # Data directory
│   ├── input/                      # Input data files
│   │   ├── cambridgeneurotech_h7.json        # Cambridge Neurotech H7 probe
│   │   ├── cambridgeneurotech_h7_electrodes.csv # H7 electrode mapping
│   │   └── spikeinterface/         # SpikeInterface format files
│   │
│   ├── output/                      # Converted output files
│   │   ├── cambridgeneurotech_h7_pinpoint.json
│   │   ├── neuropixels_pinpoint.json
│   │   └── batch/                  # Batch conversion outputs
│   │
│   └── examples/                    # Example data files
│       ├── neuropixels_example.json
│       └── electrodes_example.csv
│
├── tests/                           # Test scripts
│   ├── test_converter.py           # Basic converter test
│   └── test_cambridge_h7.py        # Cambridge Neurotech H7 test
│
├── docs/                            # Documentation
│   ├── api.md                      # API reference
│   ├── formats.md                  # Format specifications
│   └── examples.md                 # Usage examples
│
├── scripts/                         # Utility scripts
│   ├── download_examples.py        # Download example data
│   └── validate_output.py          # Validate conversions
│
├── config.yaml                      # Default configuration file
├── requirements.txt                 # Python dependencies
├── setup.py                        # Package setup file
├── README.md                       # Main documentation
├── installation.md                 # Installation guide
├── usage.md                        # Usage instructions
├── file_structure_tree.md          # This file
└── DOCUMENTATION.md                # Comprehensive documentation
```

## Directory Descriptions

### `/src`
Core application code organized into logical modules:
- Main converter orchestration
- Format-specific parsers and generators
- Coordinate and geometry transformations
- Data validation
- Utility functions

### `/data`
Data files organized by purpose:
- **input/**: Source probe data files
- **output/**: Converted Pinpoint format files
- **examples/**: Sample data for testing

### `/tests`
Test scripts for verification:
- Unit tests for individual components
- Integration tests for complete pipeline
- Specific probe type tests (e.g., Cambridge H7)

### `/docs`
Technical documentation:
- API reference
- Format specifications
- Usage examples and tutorials

## Key Files

### Core Application
- `converter.py` (650 lines) - Main conversion orchestration
- `cli.py` (200 lines) - Command-line interface
- `pinpoint.py` (450 lines) - Pinpoint format generator

### Parsers
- `spikeinterface.py` (350 lines) - SpikeInterface JSON parser
- `csv_parser.py` (400 lines) - CSV electrode parser
- `stl_parser.py` (550 lines) - 3D model parser

### Transformers
- `coordinates.py` (450 lines) - Coordinate transformations
- `geometry.py` (500 lines) - Geometric operations

### Configuration
- `config.yaml` - Default settings
- `requirements.txt` - Python dependencies

## File Naming Conventions

- **Python modules**: `lowercase_with_underscores.py`
- **Data files**: `{probe_name}_{type}.{ext}`
  - Example: `cambridgeneurotech_h7.json`
- **Output files**: `{input_name}_pinpoint.json`
- **Test files**: `test_{feature}.py`

## Total Project Size

- **Source code**: ~3,500 lines of Python
- **Test code**: ~500 lines
- **Documentation**: ~1,500 lines
- **Total files**: 35+
- **Supported formats**: 3 input, 1 output
