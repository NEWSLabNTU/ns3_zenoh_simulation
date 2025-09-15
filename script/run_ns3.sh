#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

pushd "$PROJECT_ROOT/ns-3-dev"
./ns3 run scratch/topology --no-build
popd
