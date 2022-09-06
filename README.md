# flec-simulation-experiments

  docker build -t pquic-ns3-dce-base -f Dockerfile-base .
  docker build -t pquic-ns3-dce .
  pushd .. && git clone --recurse-submodules https://github.com/francoismichel/flec && popd
  sh run.sh $(pwd)/../flec
  
