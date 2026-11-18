"""Load the HA-independent modules of the integration without importing Home Assistant."""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "custom_components" / "kronoterm_ksm"

for name, path in (("custom_components", ROOT / "custom_components"), ("custom_components.kronoterm_ksm", PKG_DIR)):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # namespace-like package, __init__.py is NOT executed
        sys.modules[name] = module

modbus = importlib.import_module("custom_components.kronoterm_ksm.modbus")
values = importlib.import_module("custom_components.kronoterm_ksm.values")
registers = importlib.import_module("custom_components.kronoterm_ksm.registers")
alarms = importlib.import_module("custom_components.kronoterm_ksm.alarms")
