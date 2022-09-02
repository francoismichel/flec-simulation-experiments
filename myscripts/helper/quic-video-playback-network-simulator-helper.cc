#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include "ns3/wifi-module.h"
#include "ns3/yans-wifi-helper.h"
#include "ns3/mobility-module.h"
#include "ns3/core-module.h"
#include "ns3/fd-net-device-module.h"
#include "ns3/internet-module.h"
#include "ns3/dce-module.h"
#include "quic-video-playback-network-simulator-helper.h"
#include "ns3/bridge-helper.h"

using namespace ns3;

std::vector <std::string> split(std::string str, std::string sep) {
    char *cstr = const_cast<char *>(str.c_str());
    char *current;
    std::vector <std::string> arr;
    current = strtok(cstr, sep.c_str());
    while (current != NULL) {
        arr.push_back(current);
        current = strtok(NULL, sep.c_str());
    }
    return arr;
}

void installNetDevice(Ptr<Node> node, std::string deviceName, Mac48AddressValue macAddress, Ipv4InterfaceAddress ipv4Address) {
  EmuFdNetDeviceHelper emu;
  emu.SetDeviceName(deviceName);
  NetDeviceContainer devices = emu.Install(node);
  Ptr<NetDevice> device = devices.Get(0);
  device->SetAttribute("Address", macAddress);

  Ptr<Ipv4> ipv4 = node->GetObject<Ipv4>();
  uint32_t interface = ipv4->AddInterface(device);
  ipv4->AddAddress(interface, ipv4Address);
  ipv4->SetMetric(interface, 1);
  ipv4->SetUp(interface);
}

QuicVideoPlaybackNetworkSimulatorHelper::QuicVideoPlaybackNetworkSimulatorHelper(std::string filesize, std::string video_filename, bool use_fec_api, long int fixed_cwin, std::string cc_algo, wifi_standard_t wifi_standard, std::string wifi_pcap_filename, int wifi_distance_meters) {
  wifi_standard_ = wifi_standard;
  NodeContainer nodes;
//  NodeContainer wifi_nodes;
  if (wifi_standard != WIFI_NO_WIFI) {
      nodes.Create(3);
//      wifi_nodes.Create(1);
      InternetStackHelper internet;
      Ipv4DceRoutingHelper routing = Ipv4DceRoutingHelper();
      internet.SetRoutingHelper(routing);
      wifi_sta_node_ = nodes.Get(0);
      right_node_ = nodes.Get(1);
      left_node_ = nodes.Get(2);
//      internet.Install(wifi_nodes);



//      mobility.Install (sv);
//      mobility.Install (router);
//      mobility.Install (ar);

      MobilityHelper mobility;
      Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator> ();

      positionAlloc->Add (Vector (0.0, 0.0, 0.0));
      positionAlloc->Add (Vector (1.0, (double) wifi_distance_meters, 0.0));
      mobility.SetPositionAllocator (positionAlloc);
      mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
//      mobility.SetMobilityModel ("ns3::RandomDirection2dMobilityModel",
//                                 "Bounds", RectangleValue (Rectangle (-200, 60, 0, 70)),
//                                 "Speed", StringValue ("ns3::ConstantRandomVariable[Constant=50.0]"),
//                                 "Pause", StringValue ("ns3::ConstantRandomVariable[Constant=0.2]"));

      // Wi-Fi
      WifiHelper wifi;
      WifiMacHelper mac;
      YansWifiPhyHelper phy;
      YansWifiChannelHelper phyChannel = YansWifiChannelHelper::Default ();
      switch (wifi_standard) {
          case WIFI_80211N_2DOT4GHz:
              wifi.SetRemoteStationManager ("ns3::MinstrelHtWifiManager");
              wifi.SetStandard (WIFI_STANDARD_80211n_2_4GHZ);
              break;
          case WIFI_80211N_5GHz:
              wifi.SetRemoteStationManager ("ns3::MinstrelHtWifiManager");
              wifi.SetStandard (WIFI_STANDARD_80211n_5GHZ);
              break;
          default:
              break;
      }


      // setup Wifi sta.
      phy.SetChannel (phyChannel.Create ());
      Ssid ssid1 = Ssid ("wifi-ap1");
      mac.SetType ("ns3::StaWifiMac",
                   "Ssid", SsidValue (ssid1),
                   "ActiveProbing", BooleanValue (false));
      wifi_sta_device_container_ = wifi.Install (phy, mac, wifi_sta_node_);
      // setup ap.
      mac.SetType ("ns3::ApWifiMac",
                   "Ssid", SsidValue (ssid1));
      wifi_ap_device_container_ = wifi.Install (phy, mac, left_node_);

      mobility.Install (wifi_sta_node_);
      mobility.Install (left_node_);
      internet.Install(nodes);
      if (!wifi_pcap_filename.empty()) {
          phy.EnablePcap (wifi_pcap_filename, nodes);
      }



  } else {

      nodes.Create(2);
      InternetStackHelper internet;
      Ipv4DceRoutingHelper routing = Ipv4DceRoutingHelper();
      internet.SetRoutingHelper(routing);
      internet.Install(nodes);

      left_node_ = nodes.Get(0);
      right_node_ = nodes.Get(1);

  }
  DceManagerHelper dceManager;
  dceManager.Install(nodes);
//  dceManager.Install(wifi_nodes);

  DceApplicationHelper dce;
  ApplicationContainer apps;
  dce.SetStackSize(1 << 20);

  bool debug = std::getenv("PQUIC_DEBUG") && strlen(std::getenv("PQUIC_DEBUG"));

  std::vector<std::string> plugins;
  if (std::getenv("PQUIC_PLUGINS") && strlen(std::getenv("PQUIC_PLUGINS"))) {
      plugins = split(std::getenv("PQUIC_PLUGINS"), ",");
  }

  bool qlog = std::getenv("PQUIC_QLOG") && strlen(std::getenv("PQUIC_QLOG"));

  dce.SetBinary("picoquicvideo");
  dce.ResetArguments();
  dce.ResetEnvironment();
  if (!debug) {
      dce.AddArgument("-l");
      dce.AddArgument("/dev/null");
  }
  if (qlog) {
      dce.AddArgument("-q");
      dce.AddArgument("server.qlog.json");
  }
  for (size_t i = 0; i < plugins.size(); i++) {
      dce.AddArgument("-P");
      dce.AddArgument(plugins[i]);
  }
  dce.AddArgument("-1");
  if (fixed_cwin != 0) {
      dce.AddArgument("-W");
      dce.AddArgument(std::to_string(fixed_cwin));
  }

  dce.AddArgument("-X");
  dce.AddArgument(std::string("/var/log/") + wifi_pcap_filename + std::string(".keys.log"));
  dce.AddArgument("-V");
  dce.AddArgument(video_filename);

  dce.AddArgument("-O");
  dce.AddArgument("/dev/null");

  if (use_fec_api) {
      dce.AddArgument("-a");
  }

  if (!cc_algo.empty()) {
      dce.AddArgument("-A");
      dce.AddArgument(cc_algo);
  }

  dce.AddArgument("-p");
  dce.AddArgument("4443");

  apps = dce.Install(right_node_);
  apps.Start(Seconds(10.0));

  dce.SetBinary("picoquicvideo");
  dce.ResetArguments();
  dce.ResetEnvironment();
  if (!debug) {
      dce.AddArgument("-l");
      dce.AddArgument("/dev/null");
  }
  if (qlog) {
      dce.AddArgument("-q");
      dce.AddArgument("client.qlog.json");
  }
  for (size_t i = 0; i < plugins.size(); i++) {
      dce.AddArgument("-P");
      dce.AddArgument(plugins[i]);
  }
  dce.AddArgument("-X");
  dce.AddArgument(std::string("/var/log/") + wifi_pcap_filename + std::string(".keys.log"));
  dce.AddArgument("-4");
  dce.AddArgument("-G");
  dce.AddArgument(filesize);
  dce.AddArgument("-O");
  dce.AddArgument("/dev/null");
  dce.AddArgument("-V");
  dce.AddArgument(video_filename);
  if (use_fec_api) {
      dce.AddArgument("-a");
  }
  if (!cc_algo.empty()) {
      dce.AddArgument("-A");
      dce.AddArgument(cc_algo);
  }
  dce.AddArgument("192.168.50.2");
  dce.AddArgument("4443");

  if (wifi_standard_ != WIFI_NO_WIFI) {
      apps = dce.Install(wifi_sta_node_);
  } else {
      apps = dce.Install(left_node_);
  }
  apps.Start(Seconds(15.0));
}

void QuicVideoPlaybackNetworkSimulatorHelper::Run(Time duration) {
  Ipv4GlobalRoutingHelper::PopulateRoutingTables();
  // write the routing table to file
  Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper>("dynamic-global-routing.routes", std::ios::out);
  Ipv4RoutingHelper::PrintRoutingTableAllAt(Seconds(0.), routingStream);

  Simulator::Stop(duration);
  Simulator::Run();
  Simulator::Destroy();
}

Ptr<Node> QuicVideoPlaybackNetworkSimulatorHelper::GetLeftNode() const {
  return left_node_;
}

Ptr<Node> QuicVideoPlaybackNetworkSimulatorHelper::GetRightNode() const {
  return right_node_;
}

Ptr<Node> QuicVideoPlaybackNetworkSimulatorHelper::GetWiFiNode() const {
  return wifi_sta_node_;
}

NetDeviceContainer QuicVideoPlaybackNetworkSimulatorHelper::GetWiFiStaDeviceContainer() const {
  return wifi_sta_device_container_;
}

NetDeviceContainer QuicVideoPlaybackNetworkSimulatorHelper::GetWiFiAPDeviceContainer() const {
  return wifi_ap_device_container_;
}

bool QuicVideoPlaybackNetworkSimulatorHelper::UseWiFi() const {
  return wifi_standard_ != WIFI_NO_WIFI;
}