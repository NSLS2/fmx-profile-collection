#!/bin/bash

# Perform beamline-specific actions in this file.
sudo mkdir -p /etc/bluesky
sudo touch /etc/bluesky/kafka.yml
sudo mkdir -p /etc/tiled
sudo cp profile.yml /etc/tiled/profiles
