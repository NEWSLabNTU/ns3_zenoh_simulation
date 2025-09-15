#!/usr/bin/env python3
"""
Convert GraphML to PNG image using Graphviz.
"""

import xml.etree.ElementTree as ET
import argparse
import sys
import subprocess
import tempfile
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


def generate_dot(nodes, edges, layout="neato", dpi=150):
    """Generate DOT format from parsed GraphML."""

    dot_content = f"""graph network_topology {{
    // Graph attributes
    layout={layout};
    dpi={dpi};
    size="10,8!";
    ratio=fill;
    overlap=false;
    splines=true;
    sep="+20,20";
    esep="+10,10";
    nodesep=1.5;
    ranksep=2.0;

    // Node and edge styling
    node [shape=circle, style=filled, fillcolor=lightblue, fontsize=14,
          width=1.2, height=1.2, fixedsize=true, penwidth=2];
    edge [fontsize=11, color=darkblue, penwidth=2, labeldistance=2.5,
          labelangle=0, labelfloat=true];

    // Nodes
"""

    # Add nodes
    for node_id, node_data in nodes.items():
        name = node_data.get("name", node_id)
        dot_content += f'    {node_id} [label="{name}"];\n'

    dot_content += "\n    // Edges\n"

    # Add edges with labels
    for edge in edges:
        source = edge["source"]
        target = edge["target"]

        # Build edge label from attributes
        labels = []
        if "datarate" in edge:
            labels.append(f"Rate: {edge['datarate']}")
        if "delay" in edge:
            labels.append(f"Delay: {edge['delay']}")
        if "network" in edge:
            labels.append(f"Net: {edge['network']}")

        label = "\\n".join(labels) if labels else ""

        if label:
            dot_content += f'    {source} -- {target} [label="{label}"];\n'
        else:
            dot_content += f'    {source} -- {target};\n'

    dot_content += "}\n"

    return dot_content


def check_graphviz():
    """Check if Graphviz is installed."""
    try:
        subprocess.run(["dot", "-V"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_png(dot_content, output_file, layout="neato", format="png", dpi=150):
    """Generate image from DOT content using Graphviz."""

    if not check_graphviz():
        print("Error: Graphviz not found. Install with: sudo apt-get install graphviz", file=sys.stderr)
        sys.exit(1)

    # Use temporary file for DOT content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as temp_dot:
        temp_dot.write(dot_content)
        temp_dot_path = temp_dot.name

    try:
        # Run Graphviz to generate image with DPI setting
        cmd = [layout, f"-T{format}", f"-Gdpi={dpi}", temp_dot_path, "-o", output_file]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error running Graphviz: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    finally:
        # Clean up temporary file
        Path(temp_dot_path).unlink()


def main():
    parser = argparse.ArgumentParser(description="Convert GraphML to PNG image using Graphviz")
    parser.add_argument("graphml_file", help="Input GraphML file")
    parser.add_argument("-o", "--output", help="Output image file (default: topology.png)")
    parser.add_argument("-l", "--layout", default="neato",
                       choices=["dot", "neato", "circo", "fdp", "sfdp", "twopi"],
                       help="Graphviz layout engine (default: neato)")
    parser.add_argument("-f", "--format", default="png",
                       choices=["png", "svg", "pdf", "jpg", "gif"],
                       help="Output format (default: png)")
    parser.add_argument("-d", "--dpi", type=int, default=150,
                       help="Output resolution in DPI (default: 150)")

    args = parser.parse_args()

    # Set default output filename based on input and format
    if not args.output:
        input_stem = Path(args.graphml_file).stem
        args.output = f"{input_stem}.{args.format}"

    if not Path(args.graphml_file).exists():
        print(f"Error: GraphML file '{args.graphml_file}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"Parsing GraphML file: {args.graphml_file}")
        nodes, edges = parse_graphml(args.graphml_file)

        print(f"Generating DOT content (layout: {args.layout}, dpi: {args.dpi})")
        dot_content = generate_dot(nodes, edges, args.layout, args.dpi)

        print(f"Creating {args.format.upper()} image: {args.output}")
        generate_png(dot_content, args.output, args.layout, args.format, args.dpi)

        print(f"✓ Successfully generated: {args.output}")
        print(f"  Nodes: {len(nodes)}, Links: {len(edges)}")

        # Show file size
        file_size = Path(args.output).stat().st_size
        print(f"  File size: {file_size:,} bytes")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
