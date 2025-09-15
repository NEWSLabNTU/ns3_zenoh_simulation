#!/usr/bin/env python3
"""
Generate Zenoh NETWORK_CONFIG.json5 from GraphML topology description.
"""

import xml.etree.ElementTree as ET
import argparse
import sys
import json
import hashlib
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


def generate_zid(node_id):
    """Generate consistent ZID for a node based on its ID."""
    # Create a consistent hash from node_id
    hash_obj = hashlib.md5(f"zenoh_node_{node_id}".encode())
    return hash_obj.hexdigest()


def extract_listen_endpoints(node_id, edges, nodes):
    """Extract listen endpoints for a node from edge data."""
    endpoints = []
    node_numeric_id = nodes[node_id].get("id", "0")

    for edge in edges:
        if edge["source"] == node_id:
            # This node is the source, use tap_device_a
            tap_device = edge.get("tap_device_a", f"tap_{node_numeric_id}_0")
            network = edge.get("network", "10.0.1.*")

            # Extract IP from network pattern (e.g., "10.0.1.*" -> "10.0.1")
            base_ip = network.split("*")[0].rstrip(".")
            ip_addr = f"{base_ip}.{int(node_numeric_id) + 1}"
            port = 8000 + int(node_numeric_id)

            endpoints.append(f"tcp/{ip_addr}:{port}")

        elif edge["target"] == node_id:
            # This node is the target, use tap_device_b
            tap_device = edge.get("tap_device_b", f"tap_{node_numeric_id}_1")
            network = edge.get("network", "10.0.1.*")

            # Extract IP from network pattern
            base_ip = network.split("*")[0].rstrip(".")
            ip_addr = f"{base_ip}.{int(node_numeric_id) + 1}"
            port = 8000 + int(node_numeric_id)

            endpoints.append(f"tcp/{ip_addr}:{port}")

    return endpoints


def generate_zenoh_config(nodes, edges, experiment_name, zenoh_binary_path):
    """Generate Zenoh configuration from parsed GraphML."""

    config = {
        "experiment": experiment_name,
        "docker_image": {
            "tag": "eclipse/zenoh:1.4.0",
            "clean_first": False
        },
        "volume": zenoh_binary_path,
        "nodes": {},
        "links": []
    }

    # Generate node configurations
    for node_id, node_data in nodes.items():
        numeric_id = node_data.get("id", "0")
        node_name = node_data.get("name", node_id)

        listen_endpoints = extract_listen_endpoints(node_id, edges, nodes)

        config["nodes"][numeric_id] = {
            "zid": {
                "set": True,
                "value": generate_zid(node_id)
            },
            "listen_endpoints": listen_endpoints,
            "role": "router"
        }

    # Generate link configurations
    for edge in edges:
        source_id = nodes[edge["source"]].get("id", "0")
        target_id = nodes[edge["target"]].get("id", "0")

        # Find endpoint indices for the link
        source_endpoints = extract_listen_endpoints(edge["source"], edges, nodes)
        target_endpoints = extract_listen_endpoints(edge["target"], edges, nodes)

        config["links"].append({
            "a": source_id,
            "a_idx": 0,  # Simplified - could be enhanced to track actual indices
            "b": target_id,
            "b_idx": 0
        })

    return config


def write_json5_config(config, output_file):
    """Write configuration as JSON5 format."""

    # Convert to JSON string first
    json_str = json.dumps(config, indent=4)

    # Convert to JSON5-like format with comments
    json5_content = f"""{{
    experiment: "{config['experiment']}",

    docker_image: {{
        tag: "{config['docker_image']['tag']}",
        clean_first: {str(config['docker_image']['clean_first']).lower()}
    }},

    volume: "{config['volume']}",

    nodes: {{"""

    # Add nodes
    for node_id, node_config in config["nodes"].items():
        endpoints_str = ",\n            ".join([f'"{ep}"' for ep in node_config["listen_endpoints"]])

        json5_content += f"""
        "{node_id}": {{
            zid: {{set: true, value: "{node_config['zid']['value']}"}},
            listen_endpoints: [
                {endpoints_str}
            ],
            role: "{node_config['role']}"
        }},"""

    # Remove trailing comma
    json5_content = json5_content.rstrip(",")

    json5_content += """
    },

    links: ["""

    # Add links
    for link in config["links"]:
        json5_content += f"""
        {{ a: "{link['a']}", a_idx: {link['a_idx']}, b: "{link['b']}", b_idx: {link['b_idx']} }},"""

    # Remove trailing comma and close
    json5_content = json5_content.rstrip(",")
    json5_content += """
    ]
}
"""

    with open(output_file, "w") as f:
        f.write(json5_content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Zenoh NETWORK_CONFIG.json5 from GraphML topology"
    )
    parser.add_argument("graphml_file", help="Input GraphML file")
    parser.add_argument("-o", "--output", help="Output JSON5 file")
    parser.add_argument("-n", "--name", help="Experiment name (default: derived from GraphML filename)")
    parser.add_argument("-z", "--zenoh-path",
                       default="/home/aeon/repos/ns3_zenoh_simulation/zenoh",
                       help="Path to Zenoh binaries (default: ../zenoh)")

    args = parser.parse_args()

    if not Path(args.graphml_file).exists():
        print(f"Error: GraphML file '{args.graphml_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Set defaults
    if not args.name:
        args.name = Path(args.graphml_file).parent.name

    if not args.output:
        output_dir = Path(args.graphml_file).parent
        args.output = output_dir / "NETWORK_CONFIG.json5"

    try:
        print(f"Parsing GraphML file: {args.graphml_file}")
        nodes, edges = parse_graphml(args.graphml_file)

        print(f"Generating Zenoh configuration for experiment: {args.name}")
        config = generate_zenoh_config(nodes, edges, args.name, args.zenoh_path)

        print(f"Writing configuration to: {args.output}")
        write_json5_config(config, args.output)

        print(f"✓ Successfully generated Zenoh config: {args.output}")
        print(f"  Experiment: {args.name}")
        print(f"  Nodes: {len(nodes)}, Links: {len(edges)}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
