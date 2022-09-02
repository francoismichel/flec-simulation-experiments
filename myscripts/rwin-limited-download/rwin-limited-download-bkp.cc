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
    std::string delay, bandwidth, queue, client_drops_in, server_drops_in, filesize, random_seed, stream_receive_window_size, use_fec_api_str;
    double client_in_rate_pct = 0;
    double server_in_rate_pct = 0;
    CommandLine cmd;

    cmd.AddValue("delay", "delay of the p2p link", delay);
    cmd.AddValue("bandwidth", "bandwidth of the p2p link", bandwidth);
    cmd.AddValue("queue", "queue size of the p2p link (in packets)", queue);
    cmd.AddValue("filesize", "filesize to request (in bytes)", filesize);
    cmd.AddValue("loss_rate_to_client", "loss rate of the link towards the client", client_in_rate_pct);
    cmd.AddValue("loss_rate_to_server", "loss rate of the link towards the server", server_in_rate_pct);
    cmd.AddValue("seed", "seed for the loss generator", random_seed);
    cmd.AddValue("stream_receive_window_size", "the size in bytes of the receive window", stream_receive_window_size);
    cmd.AddValue("use_fec_api", "set to 0 if the app must not use the fec-defined API, set tu !0 otherwise", use_fec_api_str); // ignored
    cmd.Parse (argc, argv);

    ns3::RngSeedManager::SetSeed(std::stoi(random_seed));

    Ptr<RateErrorModel> client_drops = CreateObject<RateErrorModel>();
    Ptr<RateErrorModel> server_drops = CreateObject<RateErrorModel>();

    client_drops->SetRate((client_in_rate_pct == -1 ? server_in_rate_pct : client_in_rate_pct)/100.0);
    server_drops->SetRate((server_in_rate_pct== -1 ? client_in_rate_pct : server_in_rate_pct)/100.0);

    client_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);
    server_drops->SetUnit(RateErrorModel::ERROR_UNIT_PACKET);

    NS_ABORT_MSG_IF(delay.length() == 0, "Missing parameter: delay");
    NS_ABORT_MSG_IF(bandwidth.length() == 0, "Missing parameter: bandwidth");
    NS_ABORT_MSG_IF(queue.length() == 0, "Missing parameter: queue");
    NS_ABORT_MSG_IF(filesize.length() == 0, "Missing parameter: filesize");

    QuicNetworkSimulatorHelper sim = QuicNetworkSimulatorHelper(filesize, stream_receive_window_size);

    // Stick in the point-to-point line between the sides.
    QuicPointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue(bandwidth));
    p2p.SetChannelAttribute("Delay", StringValue(delay));
    p2p.SetQueueSize(StringValue(queue + "p"));

    NetDeviceContainer devices = p2p.Install(sim.GetLeftNode(), sim.GetRightNode());
    Ipv4AddressHelper ipv4;
    ipv4.SetBase("192.168.50.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign(devices);

    devices.Get(0)->SetAttribute("ReceiveErrorModel", PointerValue(client_drops));
    devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(server_drops));

    sim.Run(Seconds(600));
}
