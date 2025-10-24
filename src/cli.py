#!/usr/bin/env python
"""
Command-line interface for probe converter
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

# Add src to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))

from converter import ProbeConverter
from utils.logger import setup_logger


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    if args.quiet:
        log_level = 'ERROR'
    
    logger = setup_logger('probe_converter', level=log_level, log_file=args.log_file)
    
    # Handle commands
    if args.command == 'convert':
        convert_command(args, logger)
    elif args.command == 'batch':
        batch_command(args, logger)
    elif args.command == 'validate':
        validate_command(args, logger)
    else:
        parser.print_help()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='Convert silicone probe data from SpikeInterface to Pinpoint format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single probe (creates output_folder/probe_name/ with metadata.json, site_map.csv, model.obj)
  probe-convert convert -i probe.json -o output_folder

  # Convert with electrode CSV and STL model
  probe-convert convert -i probe.json -e electrodes.csv -s model.stl -o output_folder

  # Batch convert directory
  probe-convert batch -i input_dir -o output_dir

  # Validate converted probe folder
  probe-convert validate output_folder/probe_name
        """
    )
    
    # Global options
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress output except errors')
    parser.add_argument('--log-file', help='Log to file')
    parser.add_argument('--config', help='Path to configuration file')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert single probe')
    convert_parser.add_argument('-i', '--input', required=True, help='Input SpikeInterface JSON file')
    convert_parser.add_argument('-e', '--electrodes', help='Electrode CSV file (optional)')
    convert_parser.add_argument('-s', '--stl', help='STL 3D model file (optional)')
    convert_parser.add_argument('-o', '--output', required=True, help='Output directory (creates probe_name/ folder)')
    convert_parser.add_argument('--no-validate', action='store_true', help='Skip validation')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch convert directory')
    batch_parser.add_argument('-i', '--input-dir', required=True, help='Input directory')
    batch_parser.add_argument('-o', '--output-dir', required=True, help='Output directory')
    batch_parser.add_argument('-p', '--pattern', default='*.json', help='File pattern (default: *.json)')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate Pinpoint folder or file')
    validate_parser.add_argument('path', help='Pinpoint folder or JSON file to validate')
    
    return parser


def convert_command(args: argparse.Namespace, logger: logging.Logger):
    """Handle convert command."""
    logger.info(f"Converting {args.input} to {args.output}")
    
    try:
        # Initialize converter
        converter = ProbeConverter(config_path=args.config)
        
        # Run conversion
        result = converter.convert_probe(
            spikeinterface_file=args.input,
            electrode_csv=args.electrodes,
            stl_file=args.stl,
            output_file=args.output,
            validate=not args.no_validate
        )
        
        # Get folder path for logging
        from pathlib import Path
        probe_folder = Path(args.output) / result['probe_name']
        logger.info(f"[SUCCESS] Converted to {probe_folder}")
        logger.info(f"   - Probe: {result['metadata']['name']}")
        logger.info(f"   - Sites: {result['metadata']['sites']}")
        logger.info(f"   - Files: metadata.json, site_map.csv" +
                   (", model.obj" if result.get('model') else ""))

    except Exception as e:
        logger.error(f"[FAILED] Conversion failed: {str(e)}")
        sys.exit(1)


def batch_command(args: argparse.Namespace, logger: logging.Logger):
    """Handle batch command."""
    logger.info(f"Batch converting {args.input_dir} to {args.output_dir}")
    
    try:
        # Initialize converter
        converter = ProbeConverter(config_path=args.config)
        
        # Run batch conversion
        converted_files = converter.batch_convert(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            pattern=args.pattern
        )
        
        logger.info(f"[SUCCESS] Converted {len(converted_files)} probes")
        for file in converted_files:
            logger.info(f"   - {file}")

    except Exception as e:
        logger.error(f"[FAILED] Batch conversion failed: {str(e)}")
        sys.exit(1)


def validate_command(args: argparse.Namespace, logger: logging.Logger):
    """Handle validate command."""
    logger.info(f"Validating {args.path}")

    try:
        # Initialize converter
        converter = ProbeConverter(config_path=args.config)

        # Run validation
        is_valid = converter.validate_output(args.path)

        if is_valid:
            logger.info(f"[VALID] {args.path} is valid Pinpoint format")
        else:
            logger.error(f"[INVALID] {args.path} validation failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"[ERROR] Validation error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
