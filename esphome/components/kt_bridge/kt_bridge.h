#pragma once

#include <memory>

#include "esphome/components/socket/socket.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"

namespace esphome {
namespace kt_bridge {

class KTBridge : public Component, public uart::UARTDevice {
 public:
  void set_port(uint16_t port) { this->port_ = port; }
  void set_flow_control_pin(GPIOPin *pin) { this->flow_control_pin_ = pin; }

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

 protected:
  void accept_();
  void tcp_to_bus_();
  void bus_to_tcp_();
  void drop_client_(const char *reason);
  void discard_bus_rx_();

  uint16_t port_{502};
  GPIOPin *flow_control_pin_{nullptr};
  std::unique_ptr<socket::Socket> server_;
  std::unique_ptr<socket::Socket> client_;
  HighFrequencyLoopRequester high_freq_;
  uint32_t frames_{0};
};

}  // namespace kt_bridge
}  // namespace esphome
