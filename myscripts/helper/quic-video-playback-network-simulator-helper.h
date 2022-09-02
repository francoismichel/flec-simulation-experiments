#ifndef QUIC_NETWORK_SIMULATOR_HELPER_H
#define QUIC_NETWORK_SIMULATOR_HELPER_H

#include "ns3/node.h"

using namespace ns3;

typedef enum {
    WIFI_NO_WIFI,
    WIFI_80211B,
    WIFI_80211N_2DOT4GHz,
    WIFI_80211N_5GHz
} wifi_standard_t;

class QuicVideoPlaybackNetworkSimulatorHelper {
public:
    QuicVideoPlaybackNetworkSimulatorHelper(std::string, std::string, bool, long int, std::string, wifi_standard_t, std::string, int);
  void Run(Time);
  Ptr<Node> GetLeftNode() const;
  Ptr<Node> GetRightNode() const;
  Ptr<Node> GetWiFiNode() const;
  NetDeviceContainer GetWiFiStaDeviceContainer() const;
  NetDeviceContainer GetWiFiAPDeviceContainer() const;
  bool UseWiFi() const;

private:
  void RunSynchronizer() const;
  Ptr<Node> left_node_, right_node_, wifi_sta_node_; // wifi_sta_node_ is only used when Wi-Fi is used: in this case,
                                                     // the QUIC client becomes wifi_sta_node_ and left_node_ thus becomes the Wi-Fi AP
  NetDeviceContainer wifi_sta_device_container_, wifi_ap_device_container_;
  wifi_standard_t wifi_standard_;
};

#endif /* QUIC_NETWORK_SIMULATOR_HELPER_H */
