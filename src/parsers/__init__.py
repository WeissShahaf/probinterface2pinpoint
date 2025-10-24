"""
Parser modules for different input formats
"""

from .spikeinterface import SpikeInterfaceParser
from .csv_parser import CSVParser
from .stl_parser import STLParser

__all__ = ["SpikeInterfaceParser", "CSVParser", "STLParser"]
