"""CH10-1553-FlightGen - Generate realistic CH10 files with 1553 flight test data."""

__version__ = "1.0.0"
__author__ = "CH10-1553-FlightGen Team"

# Import key modules to make them available at package level
from .icd import load_icd, validate_icd_file
from .flight_profile import FlightProfile, FlightState
from .schedule import build_schedule_from_icd
from .ch10_writer import write_ch10_file, Ch10WriterConfig
from .config import get_config
from .validate import validate_file

# Import core modules
from .core.encode1553 import *
from .core.tmats import *

# Import utility modules
from .utils.errors import *
from .utils.util_time import *
from .utils.channel_config import *

__all__ = [
    'load_icd',
    'validate_icd_file', 
    'FlightProfile',
    'FlightState',
    'build_schedule_from_icd',
    'write_ch10_file',
    'Ch10WriterConfig',
    'get_config',
    'validate_file',
    # Core modules
    'encode1553',
    'tmats',
    # Utility modules
    'errors',
    'util_time',
    'channel_config'
]
