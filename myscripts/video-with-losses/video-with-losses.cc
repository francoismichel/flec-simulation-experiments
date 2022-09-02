#include "ns3/core-module.h"
#include "ns3/error-model.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/ipv4-routing-protocol.h"
#include "ns3/dce-module.h"
#include "ns3/output-stream-wrapper.h"
#include "ns3/bridge-helper.h"
#include "ns3/ipv4-interface-address.h"
#include "../helper/quic-video-playback-network-simulator-helper.h"
#include "../helper/quic-point-to-point-helper.h"

using namespace ns3;
using namespace std;

NS_LOG_COMPONENT_DEFINE("ns3 simulator");

int main(int argc, char *argv[]) {
    std::string delay, bandwidth, queue, client_drops_in, server_drops_in, filesize, videofile, random_seed, cc_algo, use_fec_api_str, wifi_standard_str, wifi_distance_meters_str;
    double client_in_rate_pct = 0;
    double server_in_rate_pct = 0;
    int set_fixed_cwin = 0;
    int wifi_distance_meters = 1;
    CommandLine cmd;
    
    cmd.AddValue("delay", "delay of the p2p link", delay);
    cmd.AddValue("bandwidth", "bandwidth of the p2p link", bandwidth);
    cmd.AddValue("queue", "queue size of the p2p link (in packets)", queue);
    cmd.AddValue("filesize", "filesize to request (in bytes)", filesize);
    cmd.AddValue("loss_rate_to_client", "loss rate of the link towards the client", client_in_rate_pct);
    cmd.AddValue("loss_rate_to_server", "loss rate of the link towards the server", server_in_rate_pct);
    cmd.AddValue("videofile", "video file to use", videofile);
    cmd.AddValue("seed", "seed for the loss generator", random_seed);
    cmd.AddValue("use_fec_api", "set to 0 if the app must not use the fec-defined API, set tu !0 otherwise", use_fec_api_str);
    cmd.AddValue("set_fixed_cwin", "set to 0 if the cwin must be fixed to the BDP", set_fixed_cwin);
    cmd.AddValue("set_cc_algo", "set to cubic|bbr|newreno to set the cc algo", cc_algo);
    cmd.AddValue("wifi_standard", "802.11b, 802.11n-2.4GHz or 802.11n-5GHz", wifi_standard_str);
    cmd.AddValue("wifi_distance_meters", "integer number of meters to the Wi-Fi AP", wifi_distance_meters);
    cmd.Parse (argc, argv);

    wifi_standard_t wifi_standard = WIFI_NO_WIFI;
    if (wifi_standard_str == std::string("802.11b")) {
        wifi_standard = WIFI_80211B;
    } else if (wifi_standard_str == std::string("802.11n-2.4GHz")) {
        wifi_standard = WIFI_80211N_2DOT4GHz;
    } else if (wifi_standard_str == std::string("802.11n-5GHz")) {
        wifi_standard = WIFI_80211N_5GHz;
    } else if (!wifi_standard_str.empty()) {
        std::cerr << "wrong wifi standard: " << wifi_standard_str;
        return -1;
    }

    ns3::RngSeedManager::SetSeed(std::stoi(random_seed));

    Ptr<RateErrorModel> client_drops = CreateObject<RateErrorModel>();
    Ptr<RateErrorModel> server_drops = CreateObject<RateErrorModel>();

    client_drops->SetRate((client_in_rate_pct == -1 ? server_in_rate_pct : client_in_rate_pct)/100.0);
    server_drops->SetRate((server_in_rate_pct == -1 ? client_in_rate_pct : server_in_rate_pct)/100.0);

    client_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);
    server_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);

    NS_ABORT_MSG_IF(delay.length() == 0, "Missing parameter: delay");
    NS_ABORT_MSG_IF(bandwidth.length() == 0, "Missing parameter: bandwidth");
    NS_ABORT_MSG_IF(queue.length() == 0, "Missing parameter: queue");
    NS_ABORT_MSG_IF(filesize.length() == 0, "Missing parameter: filesize");

    double bandwidth_to_set = 0;
    if (set_fixed_cwin != 0) {
        // Get the first occurrence
        std::string bw;
        bw.assign(bandwidth);
        size_t pos = bw.find("Mbps");
        bw.replace(pos, bw.size(), "");



        bandwidth_to_set = stof(bw)*1000000.0/8.0*(2.0*stof(delay)/1000.0)*0.9;

    }

    int use_fec_api = std::stoi(use_fec_api_str);
    if (!wifi_distance_meters_str.empty()) {
        wifi_distance_meters = std::stoi(wifi_distance_meters_str);
    }

    QuicVideoPlaybackNetworkSimulatorHelper sim = QuicVideoPlaybackNetworkSimulatorHelper(filesize, "tixeo_trace.repr", use_fec_api != 0, (long int) bandwidth_to_set, cc_algo, wifi_standard, std::string("capture_seed_" + random_seed + "_delay_" + delay), wifi_distance_meters);//videofile);
    // before ToN major revision:
//    QuicVideoPlaybackNetworkSimulatorHelper sim = QuicVideoPlaybackNetworkSimulatorHelper(filesize, "bbb_720p_25fps_realtime.mp4.repr", use_fec_api != 0, (long int) bandwidth_to_set, cc_algo, wifi_standard, std::string("capture_seed_" + random_seed + "_delay_" + delay), wifi_distance_meters);//videofile);
//    QuicVideoPlaybackNetworkSimulatorHelper sim = QuicVideoPlaybackNetworkSimulatorHelper(filesize, "bbb_720p_30fps_low_br.mp4.repr", use_fec_api != 0);//videofile);
//    QuicVideoPlaybackNetworkSimulatorHelper sim = QuicVideoPlaybackNetworkSimulatorHelper(filesize, "bbb_720p_30fps.mp4.repr", use_fec_api != 0);//videofile);

    // Stick in the point-to-point line between the sides.
    QuicPointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue(bandwidth));
    p2p.SetChannelAttribute("Delay", StringValue(delay));
    p2p.SetQueueSize(StringValue(queue + "p"));


    NetDeviceContainer devices = p2p.Install(sim.GetLeftNode(), sim.GetRightNode());
    p2p.EnablePcapAll ("p2ppcaptest");

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("192.168.50.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign(devices);
    if (sim.UseWiFi()) {
        ipv4.SetBase("192.168.51.0", "255.255.255.0");
        Ipv4InterfaceContainer interface_sta = ipv4.Assign(sim.GetWiFiStaDeviceContainer());
        Ipv4InterfaceContainer interface_ap = ipv4.Assign(sim.GetWiFiAPDeviceContainer());
        Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper> (&std::cout);

        Ipv4StaticRoutingHelper helper;
        Ptr<Ipv4> nodeIpv4 = sim.GetWiFiNode()->GetObject<Ipv4>();

        Ptr<Ipv4> rightNodeIpv4 = sim.GetRightNode()->GetObject<Ipv4>();
        Ipv4Address 	 rightNodeAddress = rightNodeIpv4->GetAddress(1, 0).GetLocal();

        uint8_t buf[4];
        rightNodeAddress.Serialize(buf);
//        printf("SERVER ADDRESS %u.%u.%u.%u\n", buf[0], buf[1], buf[2], buf[3]);
        char server_address[50];
        snprintf(server_address, 49, "%u.%u.%u.%u", buf[0], buf[1], buf[2], buf[3]);
        // server address should be 192.168.50.2


        Ptr<Ipv4StaticRouting> Ipv4stat = helper.GetStaticRouting(nodeIpv4);
        Ipv4stat->RemoveRoute(1);
        Ipv4stat->AddNetworkRouteTo(Ipv4Address("192.168.50.0"), Ipv4Mask("255.255.255.0"), Ipv4Address("192.168.51.2"), 1, 0);
        Ipv4stat->AddNetworkRouteTo(Ipv4Address("192.168.51.0"), Ipv4Mask("255.255.255.0"), 1, 0);
        Ipv4stat->SetDefaultRoute(Ipv4Address("192.168.51.2"), 1, 0);

        Ipv4stat = helper.GetStaticRouting(rightNodeIpv4);
        Ipv4stat->AddNetworkRouteTo(Ipv4Address("192.168.51.0"), Ipv4Mask("255.255.255.0"), Ipv4Address("192.168.50.1"), 1, 0);
        Ipv4stat->AddNetworkRouteTo(Ipv4Address("192.168.50.0"), Ipv4Mask("255.255.255.0"), 1, 0);
        Ipv4stat->SetDefaultRoute(Ipv4Address("192.168.50.1"), 1, 0);

//    BridgeHelper bridge;
//    NetDeviceContainer bridgeDev;
//    bridgeDev = bridge.Install (sim.GetWiFiNode(), NetDeviceContainer(sim.GetWiFiStaDeviceContainer(), devices.Get(1)));
//    Create<OutputStreamWrapper> ("all_the_routes.txt", std::ios::out);
        Ipv4GlobalRoutingHelper g;
        g.RecomputeRoutingTables();

//        g.PrintRoutingTableAllAt (Seconds (0), routingStream);
//    sim.GetWiFiNode()->GetObject<Ipv4> ()->GetRoutingProtocol ().PrintRoutingTable(routingStream, Time::Unit::S);
    }
    if (!sim.UseWiFi()) {
        devices.Get(0)->SetAttribute("ReceiveErrorModel", PointerValue(client_drops));
    }
    if (!sim.UseWiFi()) {
        devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(server_drops));
    }

    sim.Run(Seconds(600));
}
