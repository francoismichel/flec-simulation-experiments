import argparse
import subprocess
import os

parser = argparse.ArgumentParser(description='Reproduces FlEC experiments')
parser.add_argument('--only', type=str, default=None, help='If set, only runs the specified test name (e.g. rwin_limited_loss_05)')
parser.add_argument('flec_dir', type=str, default=os.path.abspath("../flec"), help='The directory of the FlEC implementation (probably pulled from https://github.com/francoismichel/flec)')


args = parser.parse_args()


experiments = {
    "rwin-limited-download": [
        "bulk", "rwin_limited_experimental_design_bursty",  "rwin_limited_loss_05",  "rwin_limited_scatter_150kB",
        "rwin_limited_experimental_design", "rwin_limited_loss_2", "rwin_limited_scatter_6MB"
    ],
    "video-with-losses": [
        "messages_experimental_design", "messages_loss_1"
    ]
}

test_to_testsuite = {}
for testsuite, tests in experiments.items():
    for test in tests:
        test_to_testsuite[test] = testsuite

for testsuite, tests in experiments.items():
    for test in tests:
        testsuite_command = "python3 testsuite.py -d -r {test}.json -t {testsuite} -f tests_flec_{test}.yaml".format(test=test, testsuite=testsuite)
        command = "cd /pquic-ns3-dce/ && export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && {testsuite_command} && cp -f $NS3_PATH/{test}.json ./results/".format(testsuite_command=testsuite_command, test=test)
        subprocess.run(["bash", "run.sh", args.flec_dir, command])
