#!/bin/bash

# Run Zenoh network using zenohd-auto-deploy
# Usage: run_zenoh.sh [experiment_name]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Get experiment name from argument or use 'test' as default
EXPERIMENT=${1:-test}
TOPOLOGY_DIR="$PROJECT_DIR/topology/$EXPERIMENT"

if [[ ! -d "$TOPOLOGY_DIR" ]]; then
    echo "Error: Topology directory not found: $TOPOLOGY_DIR"
    exit 1
fi

CONFIG_FILE="$TOPOLOGY_DIR/NETWORK_CONFIG.json5"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Network config not found: $CONFIG_FILE"
    exit 1
fi

echo "Starting Zenoh network for experiment: $EXPERIMENT"
echo "Config: $CONFIG_FILE"

# Change to zenohd-auto-deploy directory and run launch_routers.py
cd "$PROJECT_DIR/zenohd-auto-deploy"
exec python3 launch_routers.py -c "$CONFIG_FILE"