"""Pure helpers that turn raw KSM register values into real values.

Mirrors the register filters of the original ESPHome configuration. No Home Assistant imports, so
this module is unit-tested on its own (tests/test_values.py).
"""
from __future__ import annotations

from collections.abc import Mapping

from . import alarms

Registers = Mapping[int, int]


def s16(raw: int) -> int:
    return raw - 0x10000 if raw & 0x8000 else raw


def temp(raw: int | None, zero_invalid: bool = False) -> float | None:
    """S16 x0.1 °C. -50.0 °C and below or above 150 °C = sensor not connected."""
    if raw is None:
        return None
    x = s16(raw)
    if x <= -500 or x > 1500 or (zero_invalid and x == 0):
        return None
    return round(x * 0.1, 1)


def room_target(raw: int | None) -> float | None:
    """Current room setpoint, x0.1 °C; 50.0 °C and more = room thermostat not used."""
    if raw is None:
        return None
    x = s16(raw)
    if x <= -500 or x >= 500:
        return None
    return round(x * 0.1, 1)


def cop(raw: int | None) -> float | None:
    """COP/SCOP: firmwares report it with different scales (same rule as ESPHome)."""
    if raw is None:
        return None
    if raw == 0:
        return 0.0
    fallback = None
    for scale in (1.0, 0.1, 0.01, 0.001):
        v = raw * scale
        if 0 < v <= 20.0:
            if v <= 10.0:
                return round(v, 2)
            if fallback is None:
                fallback = round(v, 2)
    return fallback


def u32(regs: Registers, address: int) -> int | None:
    hi, lo = regs.get(address), regs.get(address + 1)
    if hi is None or lo is None:
        return None
    return (hi << 16) | lo


def sensor_value(desc: dict, regs: Registers, thermal_multiplier: float = 1.0) -> float | int | None:
    kind = desc["kind"]
    addr = desc["address"]
    if kind == "u32":
        v = u32(regs, addr)
        if v is not None and desc.get("thermal"):
            return round(v * thermal_multiplier, 1)
        return v
    raw = regs.get(addr)
    if raw is None:
        return None
    if kind == "temp":
        return temp(raw)
    if kind == "temp0":
        return temp(raw, zero_invalid=True)
    if kind == "troom":
        return room_target(raw)
    if kind == "cop":
        return cop(raw)
    value = s16(raw) if kind == "s16" else raw
    scale = desc.get("scale")
    if scale:
        return round(value * scale, desc.get("prec", 2))
    return value


def enum_value(desc: dict, regs: Registers) -> str | None:
    raw = regs.get(desc["address"])
    if raw is None:
        return None
    return desc["states"].get(raw)


def bit_value(desc: dict, regs: Registers) -> bool | None:
    raw = regs.get(desc["address"])
    if raw is None:
        return None
    return bool(raw & desc["mask"])


def select_raw(desc: dict, regs: Registers) -> int | None:
    raw = regs.get(desc["address"])
    if raw is None:
        return None
    return raw & 0xFF if desc.get("low_byte") else raw


def select_option(desc: dict, regs: Registers) -> str | None:
    raw = select_raw(desc, regs)
    if raw is None:
        return None
    for option, value in desc["map"].items():
        if value == raw:
            return option
    return None


def number_value(desc: dict, regs: Registers) -> float | None:
    raw = regs.get(desc["address"])
    if raw is None:
        return None
    mul = desc.get("mul", 1) or 1
    return round(s16(raw) / mul, 2)


def number_raw(desc: dict, value: float) -> int:
    mul = desc.get("mul", 1) or 1
    return int(round(value * mul)) & 0xFFFF


def active_alarms(regs: Registers, lang: str) -> tuple[list[str], list[str]]:
    """Return (alarms, warnings) texts for the active alarm bits."""
    texts = alarms.TEXTS.get(lang) or alarms.TEXTS["en"]
    errs: list[str] = []
    warns: list[str] = []
    for address, mask, is_alarm, idx in alarms.BITS:
        raw = regs.get(address)
        if raw is None or not raw & mask:
            continue
        text = texts[idx]
        target = errs if is_alarm else warns
        if text not in target:
            target.append(text)
    return errs, warns


def language(hass_language: str | None) -> str:
    """Map Home Assistant's language to one of the alarm text languages."""
    lang = (hass_language or "en").lower()
    for code in ("uk", "sl"):
        if lang.startswith(code):
            return code
    return "en"
