#!/usr/bin/env bash

set -e

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        TARGET="x86_64-unknown-linux-musl"
        LINKER="musl-gcc"
        ;;
    aarch64)
        TARGET="aarch64-unknown-linux-musl"
        LINKER="aarch64-linux-gnu-gcc"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "Building for target: $TARGET"

# Check if musl tools are installed
echo "Checking musl tools installation..."
if [ "$ARCH" = "x86_64" ]; then
    if ! command -v musl-gcc &> /dev/null; then
        echo "ERROR: musl-gcc not found. Install with: sudo apt-get install musl-tools"
        exit 1
    fi
elif [ "$ARCH" = "aarch64" ]; then
    if ! command -v aarch64-linux-gnu-gcc &> /dev/null; then
        echo "ERROR: aarch64-linux-gnu-gcc not found. Install with: sudo apt-get install gcc-aarch64-linux-gnu"
        exit 1
    fi
    if ! dpkg -l | grep -q musl-tools; then
        echo "ERROR: musl-tools not found. Install with: sudo apt-get install musl-tools"
        exit 1
    fi
fi

# Check if Rust target is installed
echo "Checking Rust target installation..."
if ! rustup target list --installed | grep -q "^$TARGET$"; then
    echo "Installing Rust target: $TARGET"
    rustup target add $TARGET
fi

# Get script directory and navigate to zenoh directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ZENOH_DIR="$PROJECT_ROOT/zenoh"

if [ ! -d "$ZENOH_DIR" ]; then
    echo "ERROR: zenoh directory not found at $ZENOH_DIR"
    exit 1
fi

cd "$ZENOH_DIR" || exit

# Set RUSTFLAGS for the build
export RUSTFLAGS="-C target-feature=-crt-static -C link-arg=-lm"

echo "Building zenoh with target $TARGET..."
cargo build --profile fast --all-targets --target $TARGET
