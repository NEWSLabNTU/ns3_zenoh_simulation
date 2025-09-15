#!/usr/bin/env python3
"""
Generate ns-3 C++ code from GraphML topology description.
"""

import xml.etree.ElementTree as ET
import argparse
import sys
from pathlib import Path


def parse_graphml(graphml_file):
    """Parse GraphML file and extract network topology."""
    tree = ET.parse(graphml_file)
    root = tree.getroot()

    # GraphML namespace
    ns = {"graphml": "http://graphml.graphdrawing.org/xmlns"}

    # Parse key definitions
    keys = {}
    for key in root.findall(".//graphml:key", ns):
        keys[key.get("id")] = {
            "for": key.get("for"),
            "name": key.get("attr.name"),
            "type": key.get("attr.type"),
        }

    # Parse nodes
    nodes = {}
    for node in root.findall(".//graphml:node", ns):
        node_id = node.get("id")
        nodes[node_id] = {"id": node_id}

        for data in node.findall("graphml:data", ns):
            key_id = data.get("key")
            if key_id in keys:
                attr_name = keys[key_id]["name"]
                nodes[node_id][attr_name] = data.text

    # Parse edges
    edges = []
    for edge in root.findall(".//graphml:edge", ns):
        edge_data = {
            "id": edge.get("id"),
            "source": edge.get("source"),
            "target": edge.get("target"),
        }

        for data in edge.findall("graphml:data", ns):
            key_id = data.get("key")
            if key_id in keys:
                attr_name = keys[key_id]["name"]
                edge_data[attr_name] = data.text

        edges.append(edge_data)

    return nodes, edges


def convert_delay_to_ns3(delay_str):
    """Convert delay string to ns-3 TimeValue format."""
    if delay_str.endswith("ms"):
        return f"TimeValue(MilliSeconds({delay_str[:-2]}))"
    elif delay_str.endswith("us"):
        return f"TimeValue(MicroSeconds({delay_str[:-2]}))"
    elif delay_str.endswith("s"):
        return f"TimeValue(Seconds({delay_str[:-1]}))"
    else:
        # Default to milliseconds if no unit specified
        return f"TimeValue(MilliSeconds({delay_str}))"


def generate_ns3_code(nodes, edges, output_file):
    """Generate ns-3 C++ code from parsed topology."""

    # Sort nodes by their numeric id for consistent ordering
    sorted_nodes = sorted(nodes.items(), key=lambda x: int(x[1].get("id", 0)))
    node_count = len(sorted_nodes)

    cpp_code = f"""#include "ns3/core-module.h"
#include "ns3/csma-module.h"
#include "ns3/network-module.h"
#include "ns3/tap-bridge-module.h"

#include <fstream>
#include <iostream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("GeneratedTopologyExample");

int main(int argc, char* argv[])
{{
    CommandLine cmd(__FILE__);
    cmd.Parse(argc, argv);

    // Real-time simulation + enable checksums
    GlobalValue::Bind("SimulatorImplementationType", StringValue("ns3::RealtimeSimulatorImpl"));
    GlobalValue::Bind("ChecksumEnabled", BooleanValue(true));

    // Create {node_count} ghost nodes
    NodeContainer n;
    n.Create({node_count}); // {', '.join([node[1].get('name', f'node{i}') for i, node in enumerate(sorted_nodes)])}

"""

    # Generate CSMA links for each edge
    for i, edge in enumerate(edges):
        # Find node indices
        source_idx = next(
            (
                idx
                for idx, (node_id, node_data) in enumerate(sorted_nodes)
                if node_id == edge["source"]
            ),
            0,
        )
        target_idx = next(
            (
                idx
                for idx, (node_id, node_data) in enumerate(sorted_nodes)
                if node_id == edge["target"]
            ),
            0,
        )

        datarate = edge.get("datarate", "100Mbps")
        delay = edge.get("delay", "1ms")
        network = edge.get("network", f"10.0.{i+1}.*")

        cpp_code += f"""    // --- LAN {network} ({edge['source']} <-> {edge['target']}) ---
    CsmaHelper csma{i+1};
    csma{i+1}.SetChannelAttribute("DataRate", StringValue("{datarate}"));
    csma{i+1}.SetChannelAttribute("Delay", {convert_delay_to_ns3(delay)});
    NetDeviceContainer d{i+1} = csma{i+1}.Install(NodeContainer(n.Get({source_idx}), n.Get({target_idx})));

"""

    # Generate TapBridge configuration
    cpp_code += """    // Setup TapBridge
    TapBridgeHelper tb;
    tb.SetAttribute("Mode", StringValue("UseBridge"));

"""

    # Group tap devices by node for cleaner output
    node_taps = {}
    for i, edge in enumerate(edges):
        source_idx = next(
            (
                idx
                for idx, (node_id, node_data) in enumerate(sorted_nodes)
                if node_id == edge["source"]
            ),
            0,
        )
        target_idx = next(
            (
                idx
                for idx, (node_id, node_data) in enumerate(sorted_nodes)
                if node_id == edge["target"]
            ),
            0,
        )

        tap_a = edge.get("tap_device_a", f"tap_{source_idx}_{i}")
        tap_b = edge.get("tap_device_b", f"tap_{target_idx}_{i}")

        if source_idx not in node_taps:
            node_taps[source_idx] = []
        if target_idx not in node_taps:
            node_taps[target_idx] = []

        node_taps[source_idx].append(
            f'tb.SetAttribute("DeviceName", StringValue("{tap_a}")); tb.Install(n.Get({source_idx}), d{i+1}.Get(0));'
        )
        node_taps[target_idx].append(
            f'tb.SetAttribute("DeviceName", StringValue("{tap_b}")); tb.Install(n.Get({target_idx}), d{i+1}.Get(1));'
        )

    # Output tap bridge configurations grouped by node
    for node_idx in sorted(node_taps.keys()):
        node_name = sorted_nodes[node_idx][1].get("name", f"node{node_idx}")
        cpp_code += f"    // {node_name}\n"
        for tap_config in node_taps[node_idx]:
            cpp_code += f"    {tap_config}\n"

    cpp_code += """
    // Run simulation for 10 minutes
    Simulator::Stop(Seconds(600.0));
    Simulator::Run();
    Simulator::Destroy();

    return 0;
}
"""

    with open(output_file, "w") as f:
        f.write(cpp_code)


def main():
    parser = argparse.ArgumentParser(
        description="Generate ns-3 C++ code from GraphML topology"
    )
    parser.add_argument("graphml_file", help="Input GraphML file")
    parser.add_argument(
        "-o",
        "--output",
        default="topology.cc",
        help="Output C++ file (default: topology.cc)",
    )

    args = parser.parse_args()

    if not Path(args.graphml_file).exists():
        print(f"Error: GraphML file '{args.graphml_file}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        nodes, edges = parse_graphml(args.graphml_file)
        generate_ns3_code(nodes, edges, args.output)
        print(f"Generated ns-3 code: {args.output}")
        print(f"Nodes: {len(nodes)}, Links: {len(edges)}")
    except Exception as e:
        print(f"Error generating code: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
