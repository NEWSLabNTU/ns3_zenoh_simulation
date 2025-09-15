#include "ns3/core-module.h"
#include "ns3/csma-module.h"
#include "ns3/network-module.h"
#include "ns3/tap-bridge-module.h"

#include <fstream>
#include <iostream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("GeneratedTopologyExample");

int main(int argc, char* argv[])
{
    CommandLine cmd(__FILE__);
    cmd.Parse(argc, argv);

    // Real-time simulation + enable checksums
    GlobalValue::Bind("SimulatorImplementationType", StringValue("ns3::RealtimeSimulatorImpl"));
    GlobalValue::Bind("ChecksumEnabled", BooleanValue(true));

    // Create 3 ghost nodes
    NodeContainer n;
    n.Create(3); // r1, r2, r3

    // --- LAN 10.0.1.* (r1 <-> r2) ---
    CsmaHelper csma1;
    csma1.SetChannelAttribute("DataRate", StringValue("100Mbps"));
    csma1.SetChannelAttribute("Delay", TimeValue(MilliSeconds(1)));
    NetDeviceContainer d1 = csma1.Install(NodeContainer(n.Get(0), n.Get(1)));

    // --- LAN 10.0.2.* (r1 <-> r3) ---
    CsmaHelper csma2;
    csma2.SetChannelAttribute("DataRate", StringValue("10Mbps"));
    csma2.SetChannelAttribute("Delay", TimeValue(MilliSeconds(5)));
    NetDeviceContainer d2 = csma2.Install(NodeContainer(n.Get(0), n.Get(2)));

    // --- LAN 10.0.3.* (r2 <-> r3) ---
    CsmaHelper csma3;
    csma3.SetChannelAttribute("DataRate", StringValue("50Mbps"));
    csma3.SetChannelAttribute("Delay", TimeValue(MilliSeconds(2)));
    NetDeviceContainer d3 = csma3.Install(NodeContainer(n.Get(1), n.Get(2)));

    // Setup TapBridge
    TapBridgeHelper tb;
    tb.SetAttribute("Mode", StringValue("UseBridge"));

    // r1
    tb.SetAttribute("DeviceName", StringValue("tap_1_0")); tb.Install(n.Get(0), d1.Get(0));
    tb.SetAttribute("DeviceName", StringValue("tap_1_1")); tb.Install(n.Get(0), d2.Get(0));
    // r2
    tb.SetAttribute("DeviceName", StringValue("tap_2_0")); tb.Install(n.Get(1), d1.Get(1));
    tb.SetAttribute("DeviceName", StringValue("tap_2_1")); tb.Install(n.Get(1), d3.Get(0));
    // r3
    tb.SetAttribute("DeviceName", StringValue("tap_3_0")); tb.Install(n.Get(2), d2.Get(1));
    tb.SetAttribute("DeviceName", StringValue("tap_3_1")); tb.Install(n.Get(2), d3.Get(1));

    // Run simulation for 10 minutes
    Simulator::Stop(Seconds(600.0));
    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
