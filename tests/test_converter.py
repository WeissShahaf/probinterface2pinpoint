#!/usr/bin/env python
"""
Test script for probe converter
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from converter import ProbeConverter
from utils.logger import setup_logger

def main():
    """Run test conversion."""
    # Set up logger
    logger = setup_logger('test_converter', level='DEBUG')
    logger.info("Starting probe converter test")
    
    # Initialize converter
    converter = ProbeConverter()
    
    # Define paths
    data_dir = Path(__file__).parent.parent / 'data' / 'examples'
    output_dir = Path(__file__).parent.parent / 'data' / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test conversion
    try:
        # Convert single probe
        logger.info("Converting single probe...")
        result = converter.convert_probe(
            spikeinterface_file=str(data_dir / 'neuropixels_example.json'),
            electrode_csv=str(data_dir / 'electrodes_example.csv'),
            output_file=str(output_dir / 'neuropixels_pinpoint.json')
        )
        
        logger.info(f"Conversion successful! Output has {len(result['electrodes'])} electrodes")
        
        # Validate output
        logger.info("Validating output...")
        is_valid = converter.validate_output(str(output_dir / 'neuropixels_pinpoint.json'))
        
        if is_valid:
            logger.info("✅ Output validation passed!")
        else:
            logger.error("❌ Output validation failed!")
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("CONVERSION SUMMARY")
        logger.info("="*50)
        logger.info(f"Probe: {result['probe']['name']}")
        logger.info(f"Manufacturer: {result['probe']['manufacturer']}")
        logger.info(f"Electrodes: {result['probe']['electrode_count']}")
        logger.info(f"Coordinate System: {result['probe']['coordinate_system']}")
        logger.info(f"Output File: {output_dir / 'neuropixels_pinpoint.json'}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
