#!/usr/bin/env bash


docker build -t pquic-ns3-dce-base-20.04 -f Dockerfile-base-20.04 .
docker build -t pquic-ns3-dce -f Dockerfile-20.04 .

python3 reproduce_experiments.py $1

bash plot_flec_graphs.sh

