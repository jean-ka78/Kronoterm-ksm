from __future__ import annotations

from conftest import alarms, registers, values


def by_key(group, key):
    return next(d for d in group if d["key"] == key)


def test_temperatures():
    assert values.temp(41) == 4.1
    assert values.temp(0xFFF6) == -1.0
    assert values.temp(0xFE0C) is None  # -50.0 = sensor missing
    assert values.temp(1501) is None
    assert values.temp(0, zero_invalid=True) is None
    assert values.temp(233, zero_invalid=True) == 23.3


def test_room_target_tenths():
    # Firmware fix from 15 Nov: register 2191 is in tenths (220 = 22.0 °C), 500 = unused
    assert values.room_target(220) == 22.0
    assert values.room_target(500) is None


def test_cop_scales():
    assert values.cop(429) == 4.29
    assert values.cop(4) == 4.0
    assert values.cop(48) == 4.8
    assert values.cop(0) == 0.0


def test_u32_and_thermal_multiplier():
    regs = {2360: 0, 2361: 581, 2362: 0, 2363: 2803}
    assert values.sensor_value(by_key(registers.SENSORS, "electrical_energy"), regs) == 581
    assert values.sensor_value(by_key(registers.SENSORS, "thermal_energy"), regs, 0.1) == 280.3


def test_pressure_scale():
    assert values.sensor_value(by_key(registers.SENSORS, "system_pressure"), {2325: 16}) == 1.6


def test_mode_select_low_byte():
    desc = by_key(registers.SELECTS, "mode")
    assert values.select_option(desc, {2016: 0x0103}) == "auto"
    assert values.select_option(by_key(registers.SELECTS, "loop_1_mode"), {2041: 2}) == "schedule"


def test_numbers_roundtrip():
    desc = by_key(registers.NUMBERS, "loop_1_target")
    assert values.number_value(desc, {2186: 220}) == 22.0
    assert values.number_raw(desc, 22.5) == 225
    off = by_key(registers.NUMBERS, "loop_1_eco_offset")
    assert values.number_raw(off, -0.5) == 0xFFFB
    assert values.number_value(off, {2046: 0xFFFB}) == -0.5


def test_enum_and_bits():
    assert values.enum_value(by_key(registers.ENUM_SENSORS, "current_function"), {2000: 0}) == "heating"
    assert values.enum_value(by_key(registers.ENUM_SENSORS, "current_function"), {2000: 99}) is None
    assert values.bit_value(by_key(registers.BINARY_SENSORS, "dhw_pump"), {2027: 2}) is True
    assert values.bit_value(by_key(registers.BINARY_SENSORS, "circulation_pump"), {2027: 2}) is False


def test_alarms_translated():
    # 2113 (doc 2114) bit 0x8 = "Visok tlak" (alarm), 2116 (doc 2117) bit 0x100 = "Ni pretoka" (warning)
    regs = {2113: 0x8, 2116: 0x100}
    errs, warns = values.active_alarms(regs, "uk")
    assert errs == ["Високий тиск"] and warns == ["Немає протоку"]
    errs, warns = values.active_alarms(regs, "sl")
    assert errs == ["Visok tlak"] and warns == ["Ni pretoka"]
    errs, _ = values.active_alarms(regs, "en")
    assert errs == ["High pressure"]
    assert values.active_alarms({}, "en") == ([], [])


def test_language_mapping():
    assert values.language("uk") == "uk"
    assert values.language("sl") == "sl"
    assert values.language("de") == "en"
    assert values.language(None) == "en"


def test_alarm_tables_consistent():
    n = len(alarms.TEXTS["sl"])
    assert n == len(alarms.TEXTS["en"]) == len(alarms.TEXTS["uk"])
    assert all(0 <= idx < n for *_, idx in alarms.BITS)
    assert set(alarms.REGISTERS) == {a for a, *_ in alarms.BITS}
