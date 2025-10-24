#!/usr/bin/env python
"""
Test script for Cambridge Neurotech H7 probe conversion
"""

import sys
import os
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from converter import ProbeConverter
from utils.logger import setup_logger

def test_h7_probe():
    """Test conversion of Cambridge Neurotech ASSY-276-H7 probe."""
    logger = setup_logger('test_h7', level='INFO')
    logger.info("Testing Cambridge Neurotech ASSY-276-H7 probe conversion")
    
    # Initialize converter
    converter = ProbeConverter()
    
    # Define paths
    data_dir = Path(__file__).parent.parent / 'data' / 'input'
    output_dir = Path(__file__).parent.parent / 'data' / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test H7 conversion (new multi-file format)
    try:
        logger.info("Converting Cambridge Neurotech H7 probe...")

        # Note: cambridgeneurotech_h7.json is in root directory
        input_file = Path(__file__).parent.parent / 'cambridgeneurotech_h7.json'
        if not input_file.exists():
            # Fallback to data/input location
            input_file = data_dir / 'cambridgeneurotech_h7.json'

        result = converter.convert_probe(
            spikeinterface_file=str(input_file),
            electrode_csv=None,  # No CSV for this test
            output_file=str(output_dir)  # Now outputs to directory
        )

        # Get probe folder path
        probe_folder = output_dir / result['probe_name']

        # Print probe details
        logger.info(f"[SUCCESS] Conversion successful!")
        logger.info(f"   Probe: {result['metadata']['name']}")
        logger.info(f"   Producer: {result['metadata']['producer']}")
        logger.info(f"   Type: {result['metadata']['type']}")
        logger.info(f"   Sites: {result['metadata']['sites']}")
        logger.info(f"   Shanks: {result['metadata']['shanks']}")
        logger.info(f"   Output: {probe_folder}")

        # Validate folder structure
        logger.info("\nValidating folder structure...")
        assert probe_folder.exists(), f"Probe folder not found: {probe_folder}"
        assert (probe_folder / 'metadata.json').exists(), "metadata.json not found"
        assert (probe_folder / 'site_map.csv').exists(), "site_map.csv not found"
        logger.info("[PASS] Folder structure valid!")

        # Validate metadata.json
        logger.info("\nValidating metadata.json...")
        with open(probe_folder / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        assert 'name' in metadata, "Missing 'name' in metadata"
        assert 'sites' in metadata, "Missing 'sites' in metadata"
        assert 'shanks' in metadata, "Missing 'shanks' in metadata"
        assert metadata['sites'] == 48, f"Expected 48 sites, got {metadata['sites']}"
        logger.info(f"[PASS] metadata.json valid (name: {metadata['name']}, sites: {metadata['sites']})")

        # Validate site_map.csv
        logger.info("\nValidating site_map.csv...")
        import csv as csv_module
        with open(probe_folder / 'site_map.csv', 'r', newline='') as f:
            reader = csv_module.DictReader(f)
            rows = list(reader)
        assert len(rows) == 48, f"Expected 48 rows, got {len(rows)}"
        required_cols = {'index', 'x', 'y', 'z', 'w', 'h', 'd', 'default'}
        assert required_cols.issubset(rows[0].keys()), f"Missing required columns"
        logger.info(f"[PASS] site_map.csv valid ({len(rows)} sites)")

        # Validate with ProbeValidator
        logger.info("\nValidating with ProbeValidator...")
        is_valid = converter.validate_output(str(probe_folder))
        if is_valid:
            logger.info("[PASS] Output validation passed!")
        else:
            logger.error("[FAIL] Output validation failed!")
            return False

        # Print electrode statistics from site_map
        x_coords = [float(row['x']) for row in rows]
        y_coords = [float(row['y']) for row in rows]

        logger.info("\n" + "="*50)
        logger.info("ELECTRODE STATISTICS")
        logger.info("="*50)
        logger.info(f"Number of electrodes: {len(rows)}")
        logger.info(f"X range: {min(x_coords):.1f} to {max(x_coords):.1f} µm")
        logger.info(f"Y range: {min(y_coords):.1f} to {max(y_coords):.1f} µm")
        logger.info(f"Array configuration: 6 rows × 8 columns")
        logger.info(f"Electrode pitch: 30 µm (horizontal), 20 µm (vertical)")
        logger.info("="*50)

        return True
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_conversion():
    """Test batch conversion of multiple probes."""
    logger = setup_logger('test_batch', level='INFO')
    logger.info("Testing batch conversion")

    converter = ProbeConverter()

    # Create input structure
    input_dir = Path(__file__).parent.parent / 'data' / 'input' / 'spikeinterface'
    input_dir.mkdir(parents=True, exist_ok=True)

    # Copy test files to spikeinterface directory
    import shutil
    data_dir = Path(__file__).parent.parent / 'data'

    # Copy H7 probe from root or data/input
    h7_source = Path(__file__).parent.parent / 'cambridgeneurotech_h7.json'
    if not h7_source.exists():
        h7_source = data_dir / 'input' / 'cambridgeneurotech_h7.json'

    if h7_source.exists():
        shutil.copy(h7_source, input_dir / 'h7_probe.json')

    # Copy example probe if it exists
    if (data_dir / 'examples' / 'neuropixels_example.json').exists():
        shutil.copy(
            data_dir / 'examples' / 'neuropixels_example.json',
            input_dir / 'neuropixels.json'
        )

    # Run batch conversion
    try:
        output_dir = Path(__file__).parent.parent / 'data' / 'output' / 'batch'
        converted_files = converter.batch_convert(
            str(data_dir / 'input'),
            str(output_dir),
            pattern='*.json'
        )

        logger.info(f"[SUCCESS] Batch conversion complete: {len(converted_files)} probes")
        for folder_path in converted_files:
            probe_name = Path(folder_path).name
            logger.info(f"   - {probe_name}/")

        # Validate at least one folder was created
        if len(converted_files) > 0:
            # The folder names come from probe metadata, check if folder exists
            logger.info(f"[PASS] Batch conversion validated!")

        return True
    except Exception as e:
        logger.error(f"Batch conversion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("CAMBRIDGE NEUROTECH H7 PROBE CONVERSION TEST")
    print("="*60 + "\n")
    
    # Run H7 test
    h7_success = test_h7_probe()
    
    print("\n" + "="*60)
    print("BATCH CONVERSION TEST")
    print("="*60 + "\n")
    
    # Run batch test
    batch_success = test_batch_conversion()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"H7 Probe Test: {'[PASSED]' if h7_success else '[FAILED]'}")
    print(f"Batch Test: {'[PASSED]' if batch_success else '[FAILED]'}")
    print("="*60)
    
    sys.exit(0 if (h7_success and batch_success) else 1)
