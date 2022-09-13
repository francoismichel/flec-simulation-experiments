#!/usr/bin/env bash

docker build -t flec-matplotlib -f Dockerfile-matplotlib .

TESTSUITE="rwin-limited-download"
TESTNAMES="simple_fec_bulk_bbr,simple_fec_ac_rlnc_bbr,bbr"

mkdir -p results_db
mkdir -p results_plots

for test in bulk ; do
    rm -f results_db/${test}.db
    echo parsing $test results...
    docker run --rm -v $(pwd):/plots -w /plots flec-matplotlib python3 json_to_db.py --testnames ${TESTNAMES} \
        --test-suite-name ${TESTSUITE} -t results_db/${test}.db results/${test}.json
done

TESTNAMES="simple_fec_causal_bbr,bbr"
for test in rwin_limited_experimental_design_bursty rwin_limited_loss_05 \
            rwin_limited_scatter_150kB rwin_limited_experimental_design rwin_limited_loss_2 \
            rwin_limited_scatter_6MB ; do
    rm -f results_db/${test}.db
    echo parsing $test results...
    docker run --rm -v $(pwd):/plots -w /plots flec-matplotlib python3 json_to_db.py --testnames ${TESTNAMES} \
        --test-suite-name ${TESTSUITE} -t results_db/${test}.db results/${test}.json
done

TESTSUITE="video-with-losses"
TESTNAMES="simple_fec_message_bbr,bbr,simple_fec_message_bbr_without_api"
for test in messages_experimental_design messages_loss_1 ; do
    rm -f results_db/${test}.db
    echo parsing $test results...
    docker run --rm -v $(pwd):/plots -w /plots flec-matplotlib python3 json_to_db.py --testnames ${TESTNAMES} \
        --test-suite-name ${TESTSUITE} -t results_db/${test}.db results/${test}.json
done

echo "Generating the graphs from the results..."

docker run --rm -v $(pwd):/plots -w /plots flec-matplotlib bash plots.sh

echo "Done !"