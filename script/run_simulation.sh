#!/usr/bin/env bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check arguments
if [ $# -ne 1 ]; then
    echo "usage: $0 <experiment_name>"
    echo "example: $0 test"
    echo ""
    echo "This script runs a complete simulation workflow:"
    echo "  1. Generate topology.cc and topology.png from GraphML"
    echo "  2. Generate Zenoh NETWORK_CONFIG.json5 from GraphML"
    echo "  3. Build ns-3 with the topology"
    echo "  4. Launch Zenoh network containers"
    echo "  5. Run ns-3 simulation"
    exit 1
fi

EXPERIMENT_NAME="$1"
TOPOLOGY_DIR="$PROJECT_ROOT/topology/$EXPERIMENT_NAME"
GRAPHML_FILE="$TOPOLOGY_DIR/topology.graphml"

echo "=== Starting Simulation Workflow for: $EXPERIMENT_NAME ==="
echo "Topology directory: $TOPOLOGY_DIR"

# Validate experiment directory and GraphML file exist
if [ ! -d "$TOPOLOGY_DIR" ]; then
    echo "ERROR: Experiment directory not found: $TOPOLOGY_DIR"
    echo "Available experiments:"
    ls "$PROJECT_ROOT/topology/" 2>/dev/null || echo "  No experiments found"
    exit 1
fi

if [ ! -f "$GRAPHML_FILE" ]; then
    echo "ERROR: topology.graphml not found: $GRAPHML_FILE"
    echo "Required files for experiment '$EXPERIMENT_NAME':"
    echo "  - topology.graphml (network topology description)"
    echo "  - NETWORK_CONFIG.json5 (will be generated if missing)"
    exit 1
fi

echo ""
echo "=== Step 1: Generate topology files from GraphML ==="
echo "Generating topology.cc and topology.png from $GRAPHML_FILE"

# Generate topology.cc and topology.png
if python3 "$SCRIPT_DIR/generate_ns3_from_graph.py" "$GRAPHML_FILE" -o "$TOPOLOGY_DIR/topology.cc"; then
    echo "✓ Generated topology.cc"
else
    echo "✗ Failed to generate topology.cc"
    exit 1
fi

if python3 "$SCRIPT_DIR/graphml2png.py" "$GRAPHML_FILE" -o "$TOPOLOGY_DIR/topology.png" -d 200; then
    echo "✓ Generated topology.png"
else
    echo "⚠ Failed to generate topology.png (continuing anyway)"
fi

echo ""
echo "=== Step 2: Generate Zenoh configuration ==="
echo "Generating NETWORK_CONFIG.json5 from GraphML"

# Generate Zenoh configuration
if python3 "$SCRIPT_DIR/generate_zenoh_config.py" "$GRAPHML_FILE" -n "$EXPERIMENT_NAME"; then
    echo "✓ Generated NETWORK_CONFIG.json5"
else
    echo "✗ Failed to generate NETWORK_CONFIG.json5"
    exit 1
fi

echo ""
echo "=== Step 3: Build ns-3 simulation ==="
echo "Building ns-3 with topology: $EXPERIMENT_NAME"

# Build ns-3 (this will copy files to appropriate locations)
if "$SCRIPT_DIR/build_ns3.sh" "$EXPERIMENT_NAME"; then
    echo "✓ ns-3 build completed successfully"
else
    echo "✗ ns-3 build failed"
    exit 1
fi

echo ""
echo "=== Step 4: Launch Zenoh network ==="
echo "Starting Zenoh router containers"

# Start Zenoh network in background
echo "Launching Zenoh routers..."
"$SCRIPT_DIR/run_zenoh.sh" &
ZENOH_PID=$!
if kill -0 $ZENOH_PID 2>/dev/null; then
    echo "✓ Zenoh network started (PID: $ZENOH_PID)"
    sleep 3  # Give time for containers to start
else
    echo "✗ Failed to start Zenoh network"
    exit 1
fi

echo ""
echo "=== Step 5: Run ns-3 simulation ==="
echo "Starting ns-3 simulation..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "=== Cleaning up simulation ==="
    if [ ! -z "$ZENOH_PID" ]; then
        echo "Stopping Zenoh network (PID: $ZENOH_PID)..."
        kill $ZENOH_PID 2>/dev/null || true
        wait $ZENOH_PID 2>/dev/null || true
    fi
    
    # Run cleanup script if it exists
    if [ -f "$SCRIPT_DIR/cleanup_simulation.sh" ]; then
        "$SCRIPT_DIR/cleanup_simulation.sh" "$EXPERIMENT_NAME"
    fi
    
    echo "✓ Cleanup completed"
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

# Run ns-3 simulation
if "$SCRIPT_DIR/run_ns3.sh"; then
    echo "✓ ns-3 simulation completed successfully"
else
    echo "✗ ns-3 simulation failed"
    exit 1
fi

echo ""
echo "=== Simulation Workflow Completed Successfully ==="
echo "Experiment: $EXPERIMENT_NAME"
echo "Duration: $(date)"
echo ""
echo "Generated files:"
echo "  - $TOPOLOGY_DIR/topology.cc"
echo "  - $TOPOLOGY_DIR/topology.png" 
echo "  - $TOPOLOGY_DIR/NETWORK_CONFIG.json5"
echo ""
echo "To run again: $0 $EXPERIMENT_NAME"