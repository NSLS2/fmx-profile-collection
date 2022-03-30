#!/bin/bash

# Perform beamline-specific actions in this file.

sudo mkdir -v -p /GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/bnlpx_config/fmx_bluesky_config/
sudo chown -Rv $USER: /GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/bnlpx_config/fmx_bluesky_config/

pip install git+https://github.com/NSLS-II-AMX/mxtools.git@${MXTOOLS_BRANCH}
