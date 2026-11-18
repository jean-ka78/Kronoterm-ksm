"""kt_bridge: transparent Modbus RTU <-> TCP bridge for the Kronoterm KSM.

Bytes from the TCP client go to the RS485 bus (with DE/RE switching for
MAX485-type modules), bytes from the bus go back to the TCP client.
Used with the Home Assistant integration custom_components/kronoterm_ksm
(protocol "RTU over TCP").
"""
import esphome.codegen as cg
from esphome import pins
from esphome.components import socket, uart
import esphome.config_validation as cv
from esphome.const import CONF_FLOW_CONTROL_PIN, CONF_ID, CONF_PORT

DEPENDENCIES = ["uart", "network"]
AUTO_LOAD = ["socket"]
MULTI_CONF = False

kt_bridge_ns = cg.esphome_ns.namespace("kt_bridge")
KTBridge = kt_bridge_ns.class_("KTBridge", cg.Component, uart.UARTDevice)

def _consume_sockets(config):
    """Reserve lwIP resources: 1 listening socket (port 502) + 1 client connection.

    ESPHome sizes the lwIP pools from what components declare. Without this the
    listen() on port 502 can fail on RP2040 because all listening slots are taken
    by api / ota / web_server. The API changed between ESPHome versions, so try the
    typed form first (SocketType.TCP_LISTEN / TCP) and fall back to the plain count.
    """
    consume = getattr(socket, "consume_sockets", None)
    if consume is None:
        return config
    socket_type = getattr(socket, "SocketType", None)
    if socket_type is not None and hasattr(socket_type, "TCP_LISTEN") and hasattr(socket_type, "TCP"):
        try:
            consume(1, "kt_bridge", socket_type.TCP_LISTEN)(config)
            consume(1, "kt_bridge_client", socket_type.TCP)(config)
            return config
        except TypeError:
            pass
    consume(2, "kt_bridge")(config)
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(KTBridge),
            cv.Optional(CONF_PORT, default=502): cv.port,
            cv.Optional(CONF_FLOW_CONTROL_PIN): pins.gpio_output_pin_schema,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA),
    _consume_sockets,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_port(config[CONF_PORT]))
    if CONF_FLOW_CONTROL_PIN in config:
        pin = await cg.gpio_pin_expression(config[CONF_FLOW_CONTROL_PIN])
        cg.add(var.set_flow_control_pin(pin))
