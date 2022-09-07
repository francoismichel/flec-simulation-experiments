#!/usr/bin/env bash

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 pquic_dir [command]"
    exit -1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ $# -lt 2 ]]; then
    docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --security-opt apparmor=unconfined -i -t -v $DIR/myscripts:/home/ns3dce/dce-linux-dev/source/ns-3-dce/myscripts -v $DIR:/pquic-ns3-dce -v $1:/home/ns3dce/pquic pquic-ns3-dce
else
    docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined --security-opt apparmor=unconfined --entrypoint bash --rm -v $DIR/myscripts:/home/ns3dce/dce-linux-dev/source/ns-3-dce/myscripts -v $DIR:/pquic-ns3-dce -v $1:/home/ns3dce/pquic pquic-ns3-dce bash -c "$2"
fi
