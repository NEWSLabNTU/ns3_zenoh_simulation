#!/usr/bin/env bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check arguments
if [ $# -ne 1 ]; then
    echo "usage: $0 <experiment_name>"
    echo "example: $0 test"
    exit 1
fi

EXPERIMENT_NAME="$1"
CONFIG_DIR="$PROJECT_ROOT/topology/$EXPERIMENT_NAME"
NS3_DIR="$PROJECT_ROOT/ns-3-dev"
NS3_SCRATCH_DIR="$NS3_DIR/scratch"
ZENOH_DEPLOY_DIR="$PROJECT_ROOT/zenohd-auto-deploy"

# Validate directories exist
if [ ! -d "$NS3_DIR" ]; then
    echo "ERROR: ns-3-dev directory not found at $NS3_DIR"
    exit 1
fi

if [ ! -d "$NS3_SCRATCH_DIR" ]; then
    echo "ERROR: ns-3 scratch directory not found at $NS3_SCRATCH_DIR"
    exit 1
fi

if [ ! -d "$ZENOH_DEPLOY_DIR" ]; then
    echo "ERROR: zenohd-auto-deploy directory not found at $ZENOH_DEPLOY_DIR"
    exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "ERROR: topology directory not found at $CONFIG_DIR"
    echo "Available topologies:"
    ls "$PROJECT_ROOT/script/topology/" 2>/dev/null || echo "  No topologies found"
    exit 1
fi

# Validate required files exist
if [ ! -f "$CONFIG_DIR/zenoh.cc" ]; then
    echo "ERROR: $CONFIG_DIR/zenoh.cc not found"
    echo "Required files for topology '$EXPERIMENT_NAME':"
    echo "  - zenoh.cc (ns-3 simulation file)"
    echo "  - NETWORK_CONFIG.json5 (network configuration)"
    exit 1
fi

if [ ! -f "$CONFIG_DIR/NETWORK_CONFIG.json5" ]; then
    echo "ERROR: $CONFIG_DIR/NETWORK_CONFIG.json5 not found"
    echo "Required files for topology '$EXPERIMENT_NAME':"
    echo "  - zenoh.cc (ns-3 simulation file)"
    echo "  - NETWORK_CONFIG.json5 (network configuration)"
    exit 1
fi

# Check if ns3 command exists
if [ ! -f "$NS3_DIR/ns3" ]; then
    echo "ERROR: ns3 build system not found at $NS3_DIR/ns3"
    echo "Make sure ns-3-dev submodule is properly initialized"
    exit 1
fi

echo "Building ns-3 for experiment: $EXPERIMENT_NAME"
echo "Copying files..."

# Copy topology files
cp "$CONFIG_DIR/zenoh.cc" "$NS3_SCRATCH_DIR/"
cp "$CONFIG_DIR/NETWORK_CONFIG.json5" "$ZENOH_DEPLOY_DIR/"

echo "Configuring and building ns-3..."
pushd "$NS3_DIR" || exit 1
./ns3 clean
./ns3 configure --enable-examples --enable-tests --enable-sudo
./ns3 build
popd

echo "Build completed successfully!"
echo "Run with: ./script/run_ns3.sh"
