#include "kt_bridge.h"

#include <cerrno>

#include "esphome/core/log.h"

namespace esphome {
namespace kt_bridge {

static const char *const TAG = "kt_bridge";
static const size_t BUF_SIZE = 260;  // max Modbus RTU frame is 256 bytes

void KTBridge::setup() {
  if (this->flow_control_pin_ != nullptr) {
    this->flow_control_pin_->setup();
    this->flow_control_pin_->digital_write(false);  // receive
  }

  this->server_ = socket::socket_ip(SOCK_STREAM, 0);
  if (this->server_ == nullptr) {
    ESP_LOGE(TAG, "Could not create socket");
    this->mark_failed();
    return;
  }
  int enable = 1;
  this->server_->setsockopt(SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable));
  if (this->server_->setblocking(false) != 0) {
    ESP_LOGE(TAG, "Could not make socket non-blocking");
    this->mark_failed();
    return;
  }
  struct sockaddr_storage address;
  socklen_t len = socket::set_sockaddr_any((struct sockaddr *) &address, sizeof(address), this->port_);
  if (len == 0 || this->server_->bind((struct sockaddr *) &address, len) != 0) {
    ESP_LOGE(TAG, "Could not bind port %u", this->port_);
    this->mark_failed();
    return;
  }
  if (this->server_->listen(1) != 0) {
    ESP_LOGE(TAG, "Could not listen on port %u", this->port_);
    this->mark_failed();
    return;
  }
  this->high_freq_.start();  // run loop() often: a Modbus answer takes only a few ms
}

void KTBridge::dump_config() {
  ESP_LOGCONFIG(TAG, "Kronoterm Modbus bridge:");
  ESP_LOGCONFIG(TAG, "  TCP port: %u", this->port_);
  LOG_PIN("  Flow control pin: ", this->flow_control_pin_);
}

void KTBridge::loop() {
  this->accept_();
  if (this->client_ != nullptr)
    this->tcp_to_bus_();
  this->bus_to_tcp_();
}

void KTBridge::accept_() {
  struct sockaddr_storage address;
  socklen_t len = sizeof(address);
  auto socket = this->server_->accept((struct sockaddr *) &address, &len);
  if (socket == nullptr)
    return;
  socket->setblocking(false);
  int enable = 1;
  socket->setsockopt(IPPROTO_TCP, TCP_NODELAY, &enable, sizeof(enable));
  if (this->client_ != nullptr)
    ESP_LOGI(TAG, "New client replaces the previous one");
  this->client_ = std::move(socket);
  this->discard_bus_rx_();
  ESP_LOGI(TAG, "Client connected");
}

void KTBridge::drop_client_(const char *reason) {
  ESP_LOGI(TAG, "Client disconnected (%s)", reason);
  this->client_->close();
  this->client_ = nullptr;
}

void KTBridge::discard_bus_rx_() {
  uint8_t byte;
  while (this->available() > 0)
    this->read_byte(&byte);
}

void KTBridge::tcp_to_bus_() {
  uint8_t buf[BUF_SIZE];
  ssize_t n = this->client_->read(buf, sizeof(buf));
  if (n == 0) {
    this->drop_client_("closed");
    return;
  }
  if (n < 0) {
    if (errno == EWOULDBLOCK || errno == EAGAIN)
      return;
    this->drop_client_("read error");
    return;
  }
  // A new request: anything still in the RX buffer is a stale answer.
  this->discard_bus_rx_();
  if (this->flow_control_pin_ != nullptr)
    this->flow_control_pin_->digital_write(true);  // transmit
  this->write_array(buf, n);
  this->flush();  // wait until the last byte has left the UART
  if (this->flow_control_pin_ != nullptr)
    this->flow_control_pin_->digital_write(false);  // back to receive
  this->frames_++;
}

void KTBridge::bus_to_tcp_() {
  uint8_t buf[BUF_SIZE];
  size_t n = 0;
  while (this->available() > 0 && n < sizeof(buf)) {
    if (!this->read_byte(&buf[n]))
      break;
    n++;
  }
  if (n == 0 || this->client_ == nullptr)
    return;  // nobody to send to: bytes dropped
  ssize_t sent = this->client_->write(buf, n);
  if (sent < 0 && errno != EWOULDBLOCK && errno != EAGAIN)
    this->drop_client_("write error");
}

}  // namespace kt_bridge
}  // namespace esphome
