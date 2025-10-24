"""
Utility for querying Cambridge Neurotech probe database
"""

import csv
import logging
from pathlib import Path
from typing import Optional, Dict, Any


class ProbeDatabase:
    """
    Read probe specifications from ProbesDataBase_2Dshanks_2025.csv
    """

    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize probe database reader.

        Args:
            csv_path: Path to ProbesDataBase_2Dshanks_2025.csv
                     If None, uses default ref/ directory path
        """
        self.logger = logging.getLogger(__name__)

        if csv_path is None:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            csv_path = project_root / 'ref' / 'ProbesDataBase_2Dshanks_2025.csv'

        self.csv_path = Path(csv_path)
        self._data = None

        if self.csv_path.exists():
            self._load_database()
        else:
            self.logger.warning(f"Probe database not found at {self.csv_path}")

    def _load_database(self):
        """Load CSV database into memory."""
        try:
            self._data = {}

            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    part = row.get('part', '').strip()
                    if part:
                        self._data[part] = row

            self.logger.info(f"Loaded {len(self._data)} probe models from database")

        except Exception as e:
            self.logger.error(f"Failed to load probe database: {str(e)}")
            self._data = None

    def get_shank_thickness(self, probe_name: str) -> Optional[float]:
        """
        Get shank thickness in micrometers for a probe.

        Extracts the probe part code (e.g., "H7" from "ASSY-77-H7")
        and looks up shank_thickness_um in the database.

        Args:
            probe_name: Full probe name (e.g., "ASSY-77-H7")

        Returns:
            Shank thickness in micrometers, or None if not found
        """
        if self._data is None:
            return None

        # Extract part code from probe name
        # Examples: "ASSY-77-H7" -> "H7", "ASSY-276-H2" -> "H2"
        part_code = self._extract_part_code(probe_name)

        if not part_code:
            self.logger.warning(f"Could not extract part code from: {probe_name}")
            return None

        # Look up in database
        if part_code in self._data:
            row = self._data[part_code]
            thickness_str = row.get('shank_thickness_um', '').strip()

            try:
                thickness = float(thickness_str)
                self.logger.debug(
                    f"Found shank thickness for {probe_name} ({part_code}): {thickness} μm"
                )
                return thickness
            except ValueError:
                self.logger.warning(
                    f"Invalid shank thickness value for {part_code}: {thickness_str}"
                )
                return None
        else:
            self.logger.warning(f"Part code {part_code} not found in database")
            return None

    def _extract_part_code(self, probe_name: str) -> Optional[str]:
        """
        Extract probe part code from full probe name.

        Examples:
            "ASSY-77-H7" -> "H7"
            "ASSY-276-H2" -> "H2"
            "ASSY-156-M1v1" -> "M1v1"
            "H7" -> "H7" (already just the part code)

        Args:
            probe_name: Full probe name

        Returns:
            Part code, or None if cannot be extracted
        """
        if not probe_name:
            return None

        name = probe_name.strip()

        # Check if it's already just a part code (e.g., "H7")
        if not name.startswith('ASSY-'):
            return name

        # Extract from ASSY-XX-YY format
        # Split by '-' and take the last part
        parts = name.split('-')
        if len(parts) >= 3:
            part_code = parts[-1]
            return part_code

        return None

    def get_probe_info(self, probe_name: str) -> Optional[Dict[str, Any]]:
        """
        Get all database information for a probe.

        Args:
            probe_name: Full probe name (e.g., "ASSY-77-H7")

        Returns:
            Dictionary with probe specs, or None if not found
        """
        if self._data is None:
            return None

        part_code = self._extract_part_code(probe_name)
        if not part_code:
            return None

        if part_code in self._data:
            # Convert numeric fields
            row = self._data[part_code].copy()

            numeric_fields = [
                'electrodes_n', 'shank_lenght_mm', 'shanks_n', 'shank_thickness_um',
                'electrodes_total', 'electrodesPerShank_n', 'electrodeWidth_um',
                'electrodeHeight_um', 'shankBaseWidth_um', 'shankTipWidth_um',
                'electrode_cols_n', 'electrode_rows_n', 'shankSpacing_um',
                'electrodeSpacingWidth_um', 'electrodeSpacingHeight_um',
                'electrodeSpanWidth_um', 'electrodeSpanHeight_um'
            ]

            for field in numeric_fields:
                if field in row and row[field]:
                    try:
                        row[field] = float(row[field])
                    except ValueError:
                        pass

            return row

        return None
