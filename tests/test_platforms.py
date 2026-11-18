"""Run the whole integration (coordinator + every entity) against the fake KSM,
using the Home Assistant stand-ins from ha_stub.py."""
from __future__ import annotations

import asyncio
import importlib
import sys
import types

import ha_stub
from conftest import PKG_DIR
from fake_ksm import FakeKSM

ha_stub.install()
pkg = sys.modules["custom_components.kronoterm_ksm"]
exec(compile((PKG_DIR / "__init__.py").read_text(encoding="utf-8"), str(PKG_DIR / "__init__.py"), "exec"), pkg.__dict__)

coordinator_mod = importlib.import_module("custom_components.kronoterm_ksm.coordinator")
PLATFORM_NAMES = ["sensor", "binary_sensor", "switch", "select", "number", "button", "climate"]
platforms = {name: importlib.import_module(f"custom_components.kronoterm_ksm.{name}") for name in PLATFORM_NAMES}


def heat_pump_registers() -> dict[int, int]:
    regs = {a: 0 for a in coordinator_mod.needed_addresses()}
    regs.update({
        2102: 41,      # outdoor 4.1
        2103: 432,     # flow 43.2
        2101: 413,     # DHW 41.3
        2022: 450,     # DHW target 45.0
        2025: 2,       # DHW mode schedule
        2130: 392,     # buffer 39.2
        2033: 433,     # buffer calculated 43.3
        2307: 500, 2312: 370,  # buffer curve
        2129: 381,     # loop 1 temperature
        2127: 435,     # loop 1 calculated
        2159: 233,     # loop 1 room 23.3 (KT-2 present)
        2186: 220,     # loop 1 room target 22.0
        2308: 500, 2313: 370,
        2041: 2, 2034: 1,
        2000: 0,       # function heating
        2128: 1502,    # electrical power
        2317: 1,       # compressor on
        2037: 1,       # main pump on
        2016: 0x0103,  # mode auto
        2325: 16,      # 1.6 bar
        2370: 429, 2371: 482,
        2360: 0, 2361: 581, 2362: 0, 2363: 2803,
        2113: 0x8,     # alarm "high pressure"
        2005: 2,       # error status: alarm
        2160: 0, 2161: 0, 2162: 0,  # loops 2-4: no room thermostat
        2109: 300, 2187: 350, 2309: 450, 2314: 300,  # loop 2 curve mode
    })
    return regs


class Hass:
    config = types.SimpleNamespace(language="uk")


def test_full_integration():
    async def scenario():
        ksm = FakeKSM(heat_pump_registers())
        await ksm.start()
        entry = ha_stub.ConfigEntry(
            {"host": "127.0.0.1", "port": ksm.port, "slave_id": 20, "protocol": "rtu_over_tcp"}
        )
        hass = Hass()
        # set up like async_setup_entry does (hass.config_entries is not stubbed)
        client = pkg.KronotermModbusClient("127.0.0.1", ksm.port, 20, "rtu_over_tcp", timeout=1)
        coordinator = coordinator_mod.KronotermCoordinator(hass, entry, client)
        await coordinator.async_config_entry_first_refresh()
        assert coordinator.last_update_success
        entry.runtime_data = coordinator

        entities = {}
        for name, module in platforms.items():
            added = []
            await module.async_setup_entry(hass, entry, lambda ents, added=added: added.extend(ents))
            for ent in added:
                ent.hass = hass
                await ent.async_added_to_hass()
                entities[(name, ent._attr_translation_key)] = ent
        # unique ids, fixed language-independent entity_ids, translation keys
        assert len({e._attr_unique_id for e in entities.values()}) == len(entities)
        assert len({e.entity_id for e in entities.values()}) == len(entities)
        for (platform, key), ent in entities.items():
            assert ent.entity_id == f"{platform}.kronoterm_{key}"
        assert all(e._attr_translation_key for e in entities.values())

        get = lambda p, k: entities[(p, k)]  # noqa: E731
        assert get("sensor", "outdoor_temperature").native_value == 4.1
        assert get("sensor", "system_pressure").native_value == 1.6
        assert get("sensor", "cop").native_value == 4.29
        assert get("sensor", "electrical_energy").native_value == 581
        assert get("sensor", "current_function").native_value == "heating"
        assert get("sensor", "active_alarms").native_value == "Високий тиск"
        assert get("sensor", "active_warnings").native_value == "-"
        assert get("binary_sensor", "problem").is_on is True
        assert get("binary_sensor", "main_pump").is_on is True
        assert get("select", "mode").current_option == "auto"
        assert get("number", "loop_1_target").native_value == 22.0
        assert get("sensor", "pumps_power").native_value == 45.0

        # every entity property can be evaluated
        for (platform, _key), ent in entities.items():
            for attr in ("native_value", "is_on", "current_option", "current_temperature",
                         "target_temperature", "hvac_mode", "hvac_action", "extra_state_attributes",
                         "min_temp", "max_temp", "available"):
                if hasattr(type(ent), attr):
                    getattr(ent, attr)

        # energy integration: two updates -> some kWh in heating, none in DHW
        heat, dhw = get("sensor", "energy_heating"), get("sensor", "energy_dhw")
        heat._handle_coordinator_update()
        dhw._handle_coordinator_update()
        heat._last_time -= 3600  # pretend an hour passed... but gaps > 5 min are skipped
        heat._handle_coordinator_update()
        assert heat.native_value == 0
        heat._last_time -= 60  # one minute at 1502 W = 0.025 kWh
        heat._handle_coordinator_update()
        assert abs(heat.native_value - 0.025) < 0.001
        dhw._last_time -= 60
        dhw._handle_coordinator_update()
        assert dhw.native_value == 0

        # writes
        await get("switch", "dhw_quick_heating").async_turn_on()
        assert ksm.registers[2014] == 1
        await get("select", "loop_1_mode").async_select_option("off")
        assert ksm.registers[2041] == 0
        await get("number", "dhw_target").async_set_native_value(47.5)
        assert ksm.registers[2022] == 475
        await get("number", "loop_1_eco_offset").async_set_native_value(-0.5)
        assert ksm.registers[2046] == 0xFFFB
        await get("button", "acknowledge_error").async_press()
        assert ksm.registers[2112] == 0

        # climate: loop 1 in room mode (KT-2) writes the room setpoint
        loop1 = get("climate", "loop_1")
        assert loop1.extra_state_attributes["control"] == "room"
        assert loop1.current_temperature == 23.3 and loop1.target_temperature == 22.0
        assert (loop1.min_temp, loop1.max_temp) == (17.0, 27.0)
        await loop1.async_set_temperature(temperature=21.5)
        assert ksm.registers[2186] == 215
        await loop1.async_set_temperature(temperature=35)  # clamped to 27
        assert ksm.registers[2186] == 270

        # climate: loop 2 without room thermostat shifts the curve
        loop2 = get("climate", "loop_2")
        assert loop2.extra_state_attributes["control"] == "curve"
        assert loop2.target_temperature == 35.0
        await loop2.async_set_temperature(temperature=37)
        assert (ksm.registers[2309], ksm.registers[2314]) == (470, 320)

        # climate: buffer shifts its curve, DHW writes its setpoint, modes
        buffer = get("climate", "buffer")
        assert buffer.hvac_action == "heating"
        await buffer.async_set_temperature(temperature=42.3)  # calc 43.3 -> -1.0
        assert (ksm.registers[2307], ksm.registers[2312]) == (490, 360)
        dhw_climate = get("climate", "dhw")
        await dhw_climate.async_set_temperature(temperature=50)
        assert ksm.registers[2022] == 500
        await dhw_climate.async_set_hvac_mode("off")
        assert ksm.registers[2025] == 0
        assert dhw_climate.hvac_action == "off"

        # write error surfaces as HomeAssistantError
        await client.close()
        await ksm.stop()
        try:
            await get("switch", "vacation").async_turn_on()
        except ha_stub.HomeAssistantError as err:
            assert err.translation_key == "write_failed"
        else:
            raise AssertionError("expected HomeAssistantError")

        # update with the pump gone -> update fails, entities unavailable
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False
        await client.close()

    asyncio.run(scenario())


def test_silent_heat_pump_fails_fast():
    """Pump not answering: the update gives up after the first block, not after 29 timeouts."""

    async def scenario():
        ksm = FakeKSM(heat_pump_registers(), slave=21)  # answers nothing for slave 20
        await ksm.start()
        client = pkg.KronotermModbusClient("127.0.0.1", ksm.port, 20, timeout=0.3)
        coordinator = coordinator_mod.KronotermCoordinator(Hass(), ha_stub.ConfigEntry({}), client)
        loop = asyncio.get_running_loop()
        start = loop.time()
        try:
            await coordinator.async_refresh()
            assert coordinator.last_update_success is False
            assert loop.time() - start < 1.0
        finally:
            await client.close()
            await ksm.stop()

    asyncio.run(scenario())


def test_unsupported_register_is_skipped():
    async def scenario():
        regs = heat_pump_registers()
        del regs[2130]  # undocumented buffer register missing on another model
        ksm = FakeKSM(regs)
        await ksm.start()
        entry = ha_stub.ConfigEntry({})
        client = pkg.KronotermModbusClient("127.0.0.1", ksm.port, 20, timeout=1)
        coordinator = coordinator_mod.KronotermCoordinator(Hass(), entry, client)
        try:
            await coordinator.async_refresh()
            assert coordinator.last_update_success
            assert 2130 not in coordinator.data and coordinator.data[2129] == 381
            assert 2130 in coordinator._unsupported
            ksm.requests.clear()
            await coordinator.async_refresh()
            assert not any(a <= 2130 < a + c for f, a, c in ksm.requests if f == 3)
        finally:
            await client.close()
            await ksm.stop()

    asyncio.run(scenario())
