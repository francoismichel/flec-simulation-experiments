#!/usr/bin/env bash

if [ -z "$1" ]
then
    echo "Usage: bash $0 flec_directory (the flec_directory is probably ../flec ?)"
    exit -1
fi

docker build -t pquic-ns3-dce-base-20.04 -f Dockerfile-base-20.04 .
docker build -t pquic-ns3-dce -f Dockerfile-20.04 .

python3 reproduce_experiments.py $1

bash plot_flec_graphs.sh
