"""Golden Pot public API."""

from .comparator import compare_directories
from .config import GoldenPotConfig, load_config

__all__ = ["GoldenPotConfig", "compare_directories", "load_config"]
__version__ = "0.1.0"
