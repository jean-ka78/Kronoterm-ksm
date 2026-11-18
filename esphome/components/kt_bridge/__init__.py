"""kt_bridge: transparent Modbus RTU <-> TCP bridge for the Kronoterm KSM.

Bytes from the TCP client go to the RS485 bus (with DE/RE switching for
MAX485-type modules), bytes from the bus go back to the TCP client.
Used with the Home Assistant integration custom_components/kronoterm_ksm
(protocol "RTU over TCP").
"""
import esphome.codegen as cg
from esphome import pins
from esphome.components import uart
import esphome.config_validation as cv
from esphome.const import CONF_FLOW_CONTROL_PIN, CONF_ID, CONF_PORT

DEPENDENCIES = ["uart", "network"]
AUTO_LOAD = ["socket"]
MULTI_CONF = False

kt_bridge_ns = cg.esphome_ns.namespace("kt_bridge")
KTBridge = kt_bridge_ns.class_("KTBridge", cg.Component, uart.UARTDevice)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(KTBridge),
            cv.Optional(CONF_PORT, default=502): cv.port,
            cv.Optional(CONF_FLOW_CONTROL_PIN): pins.gpio_output_pin_schema,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_port(config[CONF_PORT]))
    if CONF_FLOW_CONTROL_PIN in config:
        pin = await cg.gpio_pin_expression(config[CONF_FLOW_CONTROL_PIN])
        cg.add(var.set_flow_control_pin(pin))
