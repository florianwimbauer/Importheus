#! /bin/bash

# This script is for the whole setup process of hermes after a reboot. Only the mount of the download Data in /mnt needs to be done from olympus and is thus not represented in this script
# should be executed with sudo to be sure everything goes well

# Installs the special version of python with all the dependencies that are needed in my framework
if [ -z "$(ls -A /venv 2>/dev/null)" ]; then
    echo "INSTALLING PYTHON3"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

### This script sets up the ClickHouse Environment on the node
##  see https://clickhouse.com/docs/install
if ! command -v clickhouse >/dev/null 2>&1; then
    echo "INSTALLING CLICKHOUSE"

    # Install prerequisite packages
    apt-get install -y apt-transport-https ca-certificates curl gnupg
    # Download the ClickHouse GPG key and store it in the keyring
    curl -fsSL 'https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key' | gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg
    # Get the system architecture
    ARCH=$(dpkg --print-architecture)
    # Add the ClickHouse repository to apt sources
    echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg arch=${ARCH}] https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list
    # Update apt package lists
    apt-get update
    # Installing now
    sudo apt-get install -y clickhouse-server clickhouse-client

    # Starts the ClickHouse Server Service
    echo STARTING CLICKHOUSE SERVER
    service clickhouse-server start
fi

echo Setup Complete. Bye!
