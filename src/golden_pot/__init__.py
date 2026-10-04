"""Golden Pot public API."""

from .comparator import compare_directories
from .config import GoldenPotConfig, load_config
from .merger import create_merged_folder

__all__ = ["GoldenPotConfig", "compare_directories", "create_merged_folder", "load_config"]
__version__ = "0.3.1"
