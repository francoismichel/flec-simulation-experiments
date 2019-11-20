#!/usr/bin/env bash

set -e
docker build -f Dockerfile-base.14.04 -t pquic-ns3-dce-base .
docker build -t pquic-ns3-dce .
