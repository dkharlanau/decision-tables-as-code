"""Decision Tables as Code public API."""

from .engine import DecisionResult, evaluate
from .io import load_table
from .validate import Diagnostic, validate_table

__all__ = ["DecisionResult", "Diagnostic", "evaluate", "load_table", "validate_table"]
__version__ = "0.1.0"
