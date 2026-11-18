"""Constants for the Kronoterm KSM integration."""
from __future__ import annotations

DOMAIN = "kronoterm_ksm"
MANUFACTURER = "Kronoterm"
MODEL = "KSM controller"

CONF_PROTOCOL = "protocol"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_THERMAL_MULTIPLIER = "thermal_multiplier"

DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 20
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_THERMAL_MULTIPLIER = 1.0

# Register used to test the connection (outdoor temperature)
PROBE_ADDRESS = 2102

# Registers used by derived entities (energy split, climates, alarms)
REG_FUNCTION = 2000  # current function: 0 heating, 1 DHW, 2 cooling, 3 pool, 4 disinfection, 5 standby, 7 remote off
REG_ERROR_STATUS = 2005  # 0 none, 1 warning, 2 alarm, 3 notice
REG_ELECTRICAL_POWER = 2128
REG_ERROR_ACK = 2112
