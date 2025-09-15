#!/usr/bin/env bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TOPOLOGY_BASE_DIR="$PROJECT_ROOT/topology"

echo "Generating code and images for all topologies..."

# Check if topology directory exists
if [ ! -d "$TOPOLOGY_BASE_DIR" ]; then
    echo "INFO: No topology directory found at $TOPOLOGY_BASE_DIR"
    echo "Creating topology directory structure..."
    mkdir -p "$TOPOLOGY_BASE_DIR"
    echo "Place topology directories under $TOPOLOGY_BASE_DIR/"
    exit 0
fi

# Find all topology.graphml files
FOUND_TOPOLOGIES=0
GENERATED_COUNT=0
ERROR_COUNT=0

for topology_dir in "$TOPOLOGY_BASE_DIR"/*/; do
    if [ ! -d "$topology_dir" ]; then
        continue
    fi

    topology_name=$(basename "$topology_dir")
    graphml_file="$topology_dir/topology.graphml"

    if [ ! -f "$graphml_file" ]; then
        echo "SKIP: $topology_name (no topology.graphml found)"
        continue
    fi

    FOUND_TOPOLOGIES=$((FOUND_TOPOLOGIES + 1))
    echo "Processing topology: $topology_name"

    # Generate .cc file from GraphML
    cc_file="$topology_dir/topology.cc"
    echo "  Generating $cc_file..."

    if python3 "$SCRIPT_DIR/generate_ns3_from_graph.py" "$graphml_file" -o "$cc_file"; then
        echo "  ✓ Generated topology.cc"
    else
        echo "  ✗ Failed to generate topology.cc"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        continue
    fi

    # Generate PNG image from GraphML
    png_file="$topology_dir/topology.png"
    echo "  Generating $png_file..."

    if python3 "$SCRIPT_DIR/graphml2png.py" "$graphml_file" -o "$png_file" -d 200; then
        echo "  ✓ Generated topology.png"
        GENERATED_COUNT=$((GENERATED_COUNT + 1))
    else
        echo "  ✗ Failed to generate topology.png"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    echo ""
done

echo "Summary:"
echo "  Topologies found: $FOUND_TOPOLOGIES"
echo "  Successfully processed: $GENERATED_COUNT"
echo "  Errors: $ERROR_COUNT"

if [ $FOUND_TOPOLOGIES -eq 0 ]; then
    echo ""
    echo "No topologies found. To create a topology:"
    echo "  1. Create directory: mkdir $TOPOLOGY_BASE_DIR/my_topology"
    echo "  2. Add GraphML file: $TOPOLOGY_BASE_DIR/my_topology/topology.graphml"
    echo "  3. Add network config: $TOPOLOGY_BASE_DIR/my_topology/NETWORK_CONFIG.json5"
    echo "  4. Run this script again"
    exit 0
fi

if [ $ERROR_COUNT -gt 0 ]; then
    echo ""
    echo "Some topologies failed to generate. Check error messages above."
    exit 1
fi

echo ""
echo "All topologies generated successfully!"
