import argparse
import subprocess
import os
import sys

parser = argparse.ArgumentParser(description='Reproduces FlEC experiments')
parser.add_argument('--only', type=str, default=None, help='If set, only runs the specified test name (e.g. rwin_limited_loss_05)')
parser.add_argument('--verbose', action="store_true", default=False, help='Verbose output for debugging purposes')

parser.add_argument('flec_dir', type=str, default="../flec", help='The directory of the FlEC implementation (probably pulled from https://github.com/francoismichel/flec)')


args = parser.parse_args()

additional_metrics = {
    "rwin-limited-download": "additional_metrics_bytes_sent",
    "video-with-losses": "additional_metrics_bytes_sent,additional_metrics_message_based",
}

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

def run_test(test, testsuite, verbose):
    testsuite_command = "python3 testsuite.py -d -r {test}.json -t {testsuite} -f tests_flec_{test}.yaml -m {additional_metrics}".format(test=test, testsuite=testsuite, additional_metrics=additional_metrics[testsuite])
    command = "cd /pquic-ns3-dce/ && export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && export PQUIC_VIDEO=1 && export PYTHONIOENCODING=utf-8 && bash prepare_video.sh && {testsuite_command} && cp -f $NS3_PATH/{test}.json ./results/".format(testsuite_command=testsuite_command, test=test)
    stdout, stderr = (sys.stdout, sys.stderr) if verbose else (subprocess.DEVNULL, subprocess.DEVNULL)
    return subprocess.run(["bash", "run.sh", os.path.abspath(args.flec_dir), command], stdout=stdout, stderr=stderr).returncode


print("Running the simulations... Please be patient, every")
print("test suite may take more than 1h to complete.")
print("The more CPUs you have, the faster it will get.")
print()
print()

if args.only:
    run_test(args.only, test_to_testsuite[args.only], args.verbose)
else:
    i = 0
    for testsuite, tests in experiments.items():
        for test in tests:
            i += 1
            progress = "Doing test suite {}/{} ({}) ...".format(i, len(test_to_testsuite), test)
            feedback = "Done test suite {}/{}".format(i, len(test_to_testsuite))
            print("="*max(len(progress), len(feedback)))
            print(progress)
            if run_test(test, testsuite, args.verbose) != 0:
                print("Failure ! More info may be retrieved with --verbose")
            else:
                print("Success !")
            print(feedback)
            print("="*max(len(progress), len(feedback)))

