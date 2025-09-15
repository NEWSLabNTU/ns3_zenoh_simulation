#!/usr/bin/env bash
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

EXPERIMENT_NAME="$1"

echo "=== Cleaning up simulation resources ==="

if [ ! -z "$EXPERIMENT_NAME" ]; then
    echo "Experiment: $EXPERIMENT_NAME"
fi

# 1. Stop all running Zenoh containers
echo "Stopping Zenoh containers..."
docker ps --format "table {{.Names}}" | grep "zenohd_" | while read -r container; do
    if [ "$container" != "NAMES" ]; then
        echo "  Stopping container: $container"
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    fi
done

# 2. Clean up network bridges and interfaces
echo "Cleaning up network interfaces..."
# Remove TAP devices
ip link show | grep "tap_" | awk '{print $2}' | sed 's/:$//' | while read -r interface; do
    echo "  Removing TAP device: $interface"
    sudo ip link del "$interface" 2>/dev/null || true
done

# Remove bridges
ip link show | grep "br_" | awk '{print $2}' | sed 's/:$//' | while read -r bridge; do
    echo "  Removing bridge: $bridge"
    sudo ip link del "$bridge" 2>/dev/null || true
done

# Remove veth pairs
ip link show | grep "internal_\|external_" | awk '{print $2}' | sed 's/:$//' | while read -r veth; do
    echo "  Removing veth: $veth"
    sudo ip link del "$veth" 2>/dev/null || true
done

# 3. Clean up network namespaces
echo "Cleaning up network namespaces..."
sudo rm -f /var/run/netns/* 2>/dev/null || true

# 4. Clean up iptables rules
echo "Cleaning up iptables rules..."
# Remove our specific FORWARD rules (be careful not to remove system rules)
sudo iptables -L FORWARD --line-numbers | grep "physdev-is-bridged" | while read -r line; do
    if [[ $line =~ ^([0-9]+) ]]; then
        rule_num=${BASH_REMATCH[1]}
        echo "  Removing iptables rule: $rule_num"
        sudo iptables -D FORWARD "$rule_num" 2>/dev/null || true
    fi
done

# 5. Kill any remaining tmux sessions
echo "Cleaning up tmux sessions..."
tmux list-sessions 2>/dev/null | grep "zenohd_" | cut -d: -f1 | while read -r session; do
    echo "  Killing tmux session: $session"
    tmux kill-session -t "$session" 2>/dev/null || true
done

# 6. Kill any ns-3 processes
echo "Cleaning up ns-3 processes..."
pkill -f "ns3.*topology" 2>/dev/null || true
pkill -f "ns3.*zenoh" 2>/dev/null || true

# 7. Clean up any zombie processes
echo "Checking for zombie processes..."
ps aux | grep -E "(zenoh|ns3)" | grep -v grep | while read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    process=$(echo "$line" | awk '{print $11}')
    echo "  Found process: $process (PID: $pid)"
    # Uncomment the following line if you want to force kill
    # kill -9 "$pid" 2>/dev/null || true
done

echo ""
echo "✓ Cleanup completed successfully"
echo ""
echo "Note: If you see any remaining processes above, you may need to manually terminate them."
echo "Use 'docker ps' to check for remaining containers."
echo "Use 'ip link show' to check for remaining network interfaces."
