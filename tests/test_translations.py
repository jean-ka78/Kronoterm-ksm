"""Every entity has a name (and every option/state a label) in every language."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from conftest import PKG_DIR, registers

LANGS = ["en", "uk", "sl"]


def load(lang):
    return json.loads((PKG_DIR / "translations" / f"{lang}.json").read_text(encoding="utf-8"))


def literal_keys(module: str, call_arg_index: int = 1) -> set[str]:
    """String keys passed to super().__init__(coordinator, "key") in a platform module."""
    tree = ast.parse((PKG_DIR / module).read_text(encoding="utf-8"))
    keys = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "__init__"
            and len(node.args) > call_arg_index
        ):
            arg = node.args[call_arg_index]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.add(arg.value)
    return keys


def expected() -> dict[str, dict[str, set[str] | None]]:
    exp: dict[str, dict] = {p: {} for p in ("sensor", "binary_sensor", "select", "switch", "number", "button", "climate")}
    for d in registers.SENSORS:
        exp["sensor"][d["key"]] = None
    for d in registers.ENUM_SENSORS:
        exp["sensor"][d["key"]] = set(d["states"].values())
    for d in registers.BINARY_SENSORS:
        exp["binary_sensor"][d["key"]] = None
    for d in registers.SELECTS:
        exp["select"][d["key"]] = set(d["map"])
    for d in registers.SWITCHES:
        exp["switch"][d["key"]] = None
    for d in registers.NUMBERS:
        exp["number"][d["key"]] = None
    return exp


@pytest.mark.parametrize("lang", LANGS)
def test_all_register_entities_translated(lang):
    ent = load(lang)["entity"]
    for platform, keys in expected().items():
        for key, states in keys.items():
            assert key in ent[platform], f"{lang}: {platform}.{key} missing"
            assert ent[platform][key]["name"].strip()
            if states:
                assert set(ent[platform][key]["state"]) == states, f"{lang}: {platform}.{key} states"


@pytest.mark.parametrize("lang", LANGS)
def test_local_entities_translated(lang):
    ent = load(lang)["entity"]
    for module, platform in (
        ("sensor.py", "sensor"),
        ("binary_sensor.py", "binary_sensor"),
        ("button.py", "button"),
    ):
        for key in literal_keys(module):
            assert key in ent[platform], f"{lang}: {platform}.{key} missing"
    climate_src = (PKG_DIR / "climate.py").read_text(encoding="utf-8")
    for key in ("dhw", "buffer", "loop_1", "loop_2", "loop_3", "loop_4", "pool"):
        assert f'"key": "{key}"' in climate_src
        assert key in ent["climate"]
    number_src = (PKG_DIR / "number.py").read_text(encoding="utf-8")
    for key in ("main_pump_power", "loop_1_pump_power", "dhw_pump_power", "circulation_pump_power"):
        assert f'"{key}"' in number_src and key in ent["number"]


def test_strings_json_equals_english():
    assert json.loads((PKG_DIR / "strings.json").read_text(encoding="utf-8")) == load("en")


@pytest.mark.parametrize("lang", LANGS)
def test_same_structure_as_english(lang):
    def shape(obj, prefix=""):
        if isinstance(obj, dict):
            out = set()
            for k, v in obj.items():
                out |= shape(v, f"{prefix}/{k}")
            return out
        return {prefix}

    assert shape(load(lang)) == shape(load("en"))


def test_manifest():
    manifest = json.loads((PKG_DIR / "manifest.json").read_text())
    assert manifest["domain"] == "kronoterm_ksm" and manifest["config_flow"] is True
    assert manifest["requirements"] == []


def test_python_files_compile():
    for path in Path(PKG_DIR).glob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
