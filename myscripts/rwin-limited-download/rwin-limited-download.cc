#include "ns3/core-module.h"
#include "ns3/error-model.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "../helper/quic-network-simulator-helper.h"
#include "../helper/quic-point-to-point-helper.h"

using namespace ns3;
using namespace std;

NS_LOG_COMPONENT_DEFINE("ns3 simulator");

int main(int argc, char *argv[]) {
    std::string delay, bandwidth, queue, client_drops_in, server_drops_in, filesize, random_seed, stream_receive_window_size, cc_algo, wifi_standard_str, wifi_distance_meters_str, repair_receive_window_size = "-1", use_fec_api_str;
    double client_in_rate_pct = 0;
    double server_in_rate_pct = 0;
    double client_avg_burst_size = 0;
    double server_avg_burst_size = 0;
    double double_loss_rate_after_30s = 0;
    int set_fixed_cwin = 0;
    int apply_malus_on_rwin = 0;
    int wifi_distance_meters = 1;
    CommandLine cmd;
    
    cmd.AddValue("delay", "delay of the p2p link", delay);
    cmd.AddValue("bandwidth", "bandwidth of the p2p link", bandwidth);
    cmd.AddValue("queue", "queue size of the p2p link (in packets)", queue);
    cmd.AddValue("filesize", "filesize to request (in bytes)", filesize);
    cmd.AddValue("loss_rate_to_client", "loss rate of the link towards the client", client_in_rate_pct);
    cmd.AddValue("loss_rate_to_server", "loss rate of the link towards the server", server_in_rate_pct);
    cmd.AddValue("avg_burst_size_to_client", "loss rate of the link towards the client (0 to use uniform loss model instead of bursty)", client_avg_burst_size);
    cmd.AddValue("avg_burst_size_to_server", "loss rate of the link towards the server (0 to use uniform loss model instead of bursty)", server_avg_burst_size);
    cmd.AddValue("seed", "seed for the loss generator", random_seed);
    cmd.AddValue("double_loss_rate_after_30s", "if set,  to 0, the loss rate does not vary during the connection. If set to 1, the loss rate doubles after 30s", double_loss_rate_after_30s);
    cmd.AddValue("stream_receive_window_size", "the size in bytes of the receive window", stream_receive_window_size);
    cmd.AddValue("apply_malus_on_rwin", "set to 1  if the rwin should be reduced of max(10kB, 0.01*rwin) bytes compared to the advertized value of stream_receive_window_size", apply_malus_on_rwin);
    cmd.AddValue("use_fec_api", "set to 0 if the app must not use the fec-defined API, set tu !0 otherwise", use_fec_api_str);
    cmd.AddValue("set_fixed_cwin", "set to 0 if the cwin must be fixed to the BDP", set_fixed_cwin);
    cmd.AddValue("set_cc_algo", "set to cubic|bbr|newreno to set the cc algo", cc_algo);
    cmd.AddValue("wifi_standard", "802.11b, 802.11n-2.4GHz or 802.11n-5GHz", wifi_standard_str);
    cmd.AddValue("wifi_distance_meters", "integer number of meters to the Wi-Fi AP", wifi_distance_meters);
    cmd.Parse (argc, argv);

    ns3::RngSeedManager::SetSeed(std::stoi(random_seed));


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

    double client_loss_length_bound = std::min(4.0, 2*(client_avg_burst_size == -1 ? server_avg_burst_size : client_avg_burst_size));
    double server_loss_length_bound = std::min(4.0, 2*(server_avg_burst_size == -1 ? client_avg_burst_size : server_avg_burst_size));

    Ptr<ErrorModel> client_drops_generic;
    Ptr<ErrorModel> server_drops_generic;

    Ptr<RateErrorModel> client_drops_uni = NULL;
    Ptr<RateErrorModel> server_drops_uni = NULL;

    Ptr<BurstErrorModel> client_drops_burst = NULL;
    Ptr<BurstErrorModel> server_drops_burst = NULL;

    if (client_avg_burst_size != 0) {
        client_drops_burst = CreateObject<BurstErrorModel>();
        Ptr<ExponentialRandomVariable> burst_size = CreateObject<ExponentialRandomVariable>();
        burst_size->SetAttribute ("Mean", DoubleValue(client_avg_burst_size == -1 ? server_avg_burst_size : client_avg_burst_size));
        burst_size->SetAttribute ("Bound", DoubleValue(client_loss_length_bound));
//        Ptr<UniformRandomVariable> burst_size = CreateObject<UniformRandomVariable> ();
//        burst_size->SetAttribute ("Min", DoubleValue (1));
//        burst_size->SetAttribute ("Max", DoubleValue (client_loss_length_bound));
        client_drops_burst->SetBurstRate((client_in_rate_pct == -1 ? server_in_rate_pct : client_in_rate_pct)/100.0);
        client_drops_burst->SetRandomBurstSize(burst_size);
        client_drops_generic = client_drops_burst;
    } else {
        client_drops_uni = CreateObject<RateErrorModel>();
        client_drops_uni->SetRate((client_in_rate_pct == -1 ? server_in_rate_pct : client_in_rate_pct)/100.0);
        client_drops_uni->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);
        client_drops_generic = client_drops_uni;
    }

    if (server_avg_burst_size != 0) {
        server_drops_burst = CreateObject<BurstErrorModel>();
//        Ptr<UniformRandomVariable> burst_size = CreateObject<UniformRandomVariable> ();
//        burst_size->SetAttribute ("Min", DoubleValue (1));
//        burst_size->SetAttribute ("Max", DoubleValue (server_loss_length_bound));
        Ptr<ExponentialRandomVariable> burst_size = CreateObject<ExponentialRandomVariable>();
        burst_size->SetAttribute ("Mean", DoubleValue(server_avg_burst_size == -1 ? client_avg_burst_size : server_avg_burst_size));
        burst_size->SetAttribute ("Bound", DoubleValue(server_loss_length_bound));
        server_drops_burst->SetBurstRate((server_in_rate_pct == -1 ? client_in_rate_pct : server_in_rate_pct)/100.0);
        server_drops_burst->SetRandomBurstSize(burst_size);
        server_drops_generic = server_drops_burst;
    } else {
        server_drops_uni = CreateObject<RateErrorModel>();
        server_drops_uni->SetRate((server_in_rate_pct == -1 ? client_in_rate_pct : server_in_rate_pct)/100.0);
        server_drops_uni->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);
        server_drops_generic = server_drops_uni;
    }






//    Ptr<RateErrorModel> client_drops = CreateObject<RateErrorModel>();
//    Ptr<RateErrorModel> server_drops = CreateObject<RateErrorModel>();
//
//    client_drops->SetRate((client_in_rate_pct == -1 ? server_in_rate_pct : client_in_rate_pct)/100.0);
//    server_drops->SetRate((server_in_rate_pct == -1 ? client_in_rate_pct : server_in_rate_pct)/100.0);
//
//    client_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);
//    server_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);

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

    if (apply_malus_on_rwin != 0) {
        long int rwin = stof(stream_receive_window_size);
        stream_receive_window_size = std::to_string((long int) std::min(0.95*rwin, rwin - 10000.0));
        repair_receive_window_size = std::to_string((long int) rwin - stof(stream_receive_window_size));
    }

    if (!wifi_distance_meters_str.empty()) {
        wifi_distance_meters = std::stoi(wifi_distance_meters_str);
    }

    QuicNetworkSimulatorHelper sim = QuicNetworkSimulatorHelper(filesize, stream_receive_window_size, repair_receive_window_size, (long int) bandwidth_to_set, cc_algo, wifi_standard, std::string("capture_seed_" + random_seed + "_delay_" + delay), wifi_distance_meters);

    // Stick in the point-to-point line between the sides.
    QuicPointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue(bandwidth));
    p2p.SetChannelAttribute("Delay", StringValue(delay));
    p2p.SetQueueSize(StringValue(queue + "p"));
    
    NetDeviceContainer devices = p2p.Install(sim.GetLeftNode(), sim.GetRightNode());
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
        devices.Get(0)->SetAttribute("ReceiveErrorModel", PointerValue(client_drops_generic));
        devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(server_drops_generic));
    }

    if (double_loss_rate_after_30s == 0) {
        sim.Run(Seconds(600));
    } else {
        // let's double the rate
        if (client_drops_uni != NULL) {
            client_drops_uni->SetRate(client_drops_uni->GetRate()*2.0);
            client_drops_generic = client_drops_uni;
        } else {
            client_drops_burst->SetBurstRate(client_drops_burst->GetBurstRate()*2.0);
            client_drops_generic = client_drops_burst;
        }

        if (server_drops_uni != NULL) {
            server_drops_uni->SetRate(server_drops_uni->GetRate()*2.0);
            server_drops_generic = server_drops_uni;
        } else {
            server_drops_burst->SetBurstRate(server_drops_burst->GetBurstRate()*2.0);
            server_drops_generic = server_drops_burst;
        }



    }
}
