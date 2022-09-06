#!/usr/bin/env python3
import builtins
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import argparse
import tempfile
import io
from functools import partial
import random
from time import sleep, time

import yaml

from experimental_design import load_wsp, ParamsGenerator

if not os.path.exists('/.dockerenv'):
    print('This script is meant to be run inside the container', file=sys.stderr)
    exit(-1)

parser = argparse.ArgumentParser(description='Runs a suite of NS3 DCE tests against PQUIC')
parser.add_argument('-t', '--test', type=str, default=None, help='Only runs TEST')
parser.add_argument('-r', '--results', type=str, default='results.json', metavar='FILE', help='Stores the results in FILE (default results.json)')
parser.add_argument('-m', '--additional-metrics-modules', type=str, default=None, help='a comma-separated list of modules collecting additional metrics about the experiments')
parser.add_argument('-l', '--limit', type=int, default=None, help='the max number of experiments to perform for each variant (perform all experiments by default)')
parser.add_argument('-d', '--debug', action='store_true', help='Turns on debugging')
parser.add_argument('-f', '--test-file', type=str, default="tests.yaml", help='Defines the test YAML file describing the tests to run')

test_args = parser.parse_args()

script_dir = os.path.dirname(os.path.abspath(__file__))
ns3_dir = os.environ['NS3_PATH']
pquic_dir = os.environ['DCE_PATH']

print = partial(print, flush=True)

additional_metrics_modules = []
if test_args.additional_metrics_modules is not None:
    additional_metrics_modules = test_args.additional_metrics_modules.split(",")



def run(*args, stdout=True, stderr=True, shell=True, env=None, timeout=None):
    kwargs = {}
    if not stdout:
        kwargs['stdout'] = subprocess.DEVNULL
    if not stderr:
        kwargs['stderr'] = subprocess.DEVNULL
    if env:
        kwargs['env'] = os.environ.copy()
        kwargs['env'].update(env)

    p = subprocess.Popen(args, universal_newlines=True, shell=shell, **kwargs)
    try:
        return p.wait(timeout=timeout)
    except:
        p.terminate()
        return 'timeout'


def build_ns3():
    os.chdir(ns3_dir)
    if run('./waf', stderr=test_args.debug) is not 0:
        print('Building ns-3 failed', file=sys.stderr)
        exit(0)
    os.chdir(script_dir)


def build_pquic():
    if run(os.path.join(script_dir, 'prepare_pquic.sh'), stdout=test_args.debug, stderr=test_args.debug) is not 0:
        print('Building pquic failed', file=sys.stderr)
        exit(0)


def compute_queue(bandwidth, delay):
    return 1.5 * (bandwidth / 8) * 1024 * 1024 * (2 * delay / 1000) // 1200


def read_all(filename, mode='r'):
    with open(filename, mode=mode, encoding="utf-8") as f:
        try:
            return f.read()
        except Exception as e:
            print("error in file", os.path.abspath(f.name))
            raise e


def collect_additional_metrics(additional_modules, server_log_file, client_log_file, network_params):
    additional_metrics = {}
    try:
        for module_name in additional_modules:
            module = __import__(module_name)
            additional_metrics[module_name] = module.collect_metrics(server_log_file, client_log_file, network_params)
    except Exception as e:
        print(e)
        pass
    return additional_metrics


def run_binary(tests, binary, params, values, sim_timeout, hard_timeout, variant_additional_params, env=None):
    bw, fs = values['bandwidth'][0], values['filesize'][0]
    failures = []

    params['queue'] = {'type': int}
    values['queue'] = [compute_queue(values['bandwidth'][0], values['delay'][0])]
    args = []
    for p, v in values.items():
        value_str = ','.join(('%d' if params[p]['type'] is int else '%.2f') % e for e in v)
        args.append('--%s=%s%s' % (p, value_str, params[p].get('units', '')))

    for p, v in variant_additional_params.items():
        args.append('--{}={}'.format(p, v))

    with tempfile.TemporaryDirectory(prefix='pquic_ns3_%s_' % b) as tmp_dir:
        os.chdir(tmp_dir)
        shutil.copytree(os.path.join(ns3_dir, 'files-0'), os.path.join(tmp_dir, 'files-0'), symlinks=True)
        shutil.copytree(os.path.join(ns3_dir, 'files-1'), os.path.join(tmp_dir, 'files-1'), symlinks=True)

        start = time()
        if (fs / 1024 / 1024) / (bw / 8) > sim_timeout:
            print("Transfering %d bytes over a %.2fMbps link in less than %d secs is deemed impossible, skipping" % (fs, bw, sim_timeout), file=sys.stderr)
            failures.append("Link speed and filesize do not match timeout")
        else:
            print('Test started:', binary, ' '.join(args), env)
            c = run(os.path.join(ns3_dir, 'build', 'myscripts', tests['binaries'][binary]), *args, shell=False, env=env, timeout=hard_timeout)
            if c is not 0 and c != 'timeout':
                print("Failed test: %s returned %d" % (b, c), file=sys.stderr)
                failures.append("Failed test")
            elif c == 'timeout':
                print("Timeout reached", file=sys.stderr)
                failures.append("Timeout reached")

        end = time()


        rand_key = "%x" % random.getrandbits(128)

        for dir in ["pcaps", "keys", "logs"]:
            path = "/pquic-ns3-dce/captures/{}/{}".format(rand_key, dir)
            if not os.path.exists(path):
                os.system("mkdir -p {}".format(path))


        if os.environ.get('PQUIC_CAPTURE'):
            os.system("cp {} /pquic-ns3-dce/captures/{}/pcaps/".format("*.pcap", rand_key))
            os.system("cp {} /pquic-ns3-dce/captures/{}/keys/".format(os.path.join(tmp_dir, 'files-0/var/log/*.keys.log'), rand_key))
        if os.environ.get('PQUIC_DEBUG'):
            os.system("cp {} /pquic-ns3-dce/captures/{}/logs/files-0-stdout".format(os.path.join(tmp_dir, 'files-0/var/log/*/stdout'), rand_key))
            os.system("cp {} /pquic-ns3-dce/captures/{}/logs/files-0-stderr".format(os.path.join(tmp_dir, 'files-0/var/log/*/stderr'), rand_key))
            os.system("cp {} /pquic-ns3-dce/captures/{}/logs/files-1-stdout".format(os.path.join(tmp_dir, 'files-1/var/log/*/stdout'), rand_key))
            os.system("cp {} /pquic-ns3-dce/captures/{}/logs/files-1-stderr".format(os.path.join(tmp_dir, 'files-1/var/log/*/stderr'), rand_key))

        client_stdout, server_stdout = None, None
        client_stderr, server_stderr = None, None
        client_status, server_status = None, None


        for root, dirs, files in os.walk(tmp_dir):
            if 'stdout' in files:
                if 'files-0' in root:
                    client_stdout = read_all(os.path.join(root, 'stdout'))
                elif 'files-1' in root:
                    server_stdout = read_all(os.path.join(root, 'stdout'))
            if 'stderr' in files:
                if 'files-0' in root:
                    client_stderr = read_all(os.path.join(root, 'stderr'))
                elif 'files-1' in root:
                    server_stderr = read_all(os.path.join(root, 'stderr'))
            if 'status' in files:
                if 'files-0' in root:
                    client_status = read_all(os.path.join(root, 'status'))
                elif 'files-1' in root:
                    server_status = read_all(os.path.join(root, 'status'))

        # Check that both are disconnected
        if server_stdout is not None  and 'Connection state = 17' not in server_stdout:
            failures.append('Server not disconnected')
        if client_stdout is not None  and 'All done, Closing the connection.' not in client_stdout and 'Received a request to close the connection.' not in client_stdout:
            failures.append('Client not disconnected')

        # Check that the file was successfully transferred
        if client_stdout is not None  and '-1.0' in client_stdout:
            failures.append('Client did not receive the file')

        # Check the client return code
        if client_stdout is not None and 'Client exit with code = 0\n' not in client_stdout:
            failures.append('Client exit code was not 0')
        additional_metrics = {}
        transfer_time = None
        if failures:
            print("client stdout start")
            print(repr(client_status), repr(client_stdout[:10000]))
            print('+' * 20)
            print("client stdout end")
            print(repr(client_stdout[-10000:]))
            print('-' * 20)
            print("server stdout start")
            print(repr(server_status), repr(server_stdout[:10000]))
            print('+' * 20)
            print("server stdout end")
            print(repr(server_stdout[-10000:]))
            print('-' * 20)
            print("client stderr start")
            print(repr(client_stderr[:10000]))
            print('+' * 20)
            print("client stderr end")
            print(repr(client_stderr[-10000:]))
            print('-' * 20)
            print("server stderr start")
            print(repr(server_stderr[:10000]))
            print('+' * 20)
            print("server stderr end")
            print(repr(server_stderr[-10000:]))
            print(failures)
            print('Test crashed:', binary, ' '.join(args), env, 'after (real-time) %.2fs' % (end - start))
        else:
            lines = client_stdout.splitlines()
            for i in range(5):
                try:
                    t = float(lines[-1 - i].split()[0])
                    transfer_time = lines[-1 - i]
                    break
                except ValueError:
                    pass
            client_stdout_file = io.StringIO(client_stdout)
            server_stdout_file = io.StringIO(server_stdout)
            additional_metrics = collect_additional_metrics(additional_metrics_modules, server_stdout_file, client_stdout_file, values)
            print('Test finished:', binary, ' '.join(args), env, 'in (simulated)', transfer_time, '(real-time) %.2fs' % (end - start))

        return {'start': start, 'end': end, 'values': values, 'cmdline': '%s %s' % (binary, ' '.join(args)),
                'failures': failures, 'transfer_time': transfer_time, 'additional_metrics': additional_metrics}


results = {}

wsp_matrix = load_wsp(os.path.join(script_dir, 'wsp_20_col'), 20, 95)
with open(os.path.join(script_dir, test_args.test_file)) as f:
    tests = yaml.load(f)

build_ns3()
build_pquic()
os.chdir(ns3_dir)
os.system("rm -rf files-0/var/log/*")
os.system("rm -rf files-1/var/log/*")

# test that we can open the file
with open(os.path.join(test_args.results), 'a+') as f:
    json.dump(results, f)

print("ok for writing in", test_args.results)

for b, opts in tests['definitions'].items():

    if test_args.test and b != test_args.test:
        continue
    if b not in tests['binaries']:
        print('Unknown binary: %s' % b, file=sys.stderr)
        continue

    params = opts['params']
    for p, attrs in params.items():
        if attrs['type'] in vars(builtins):
            attrs['type'] = vars(builtins)[attrs['type']]

    results[b] = {'plugins': {}}

    variants = ["filesize", "loss_rate_to_client", "avg_burst_size_to_client", "avg_burst_size_to_server", "stream_receive_window_size"]

    def recurse(variants, plugin_paths):
        if len(variants) == 0:
            raise Exception("should not happen")
        variant, tail = variants[0], variants[1:]
        for val in opts['variants'].get(variant, [None]):
            if val is not None and not variant in params:
                params[variant] = {'range': [val, val], 'type': type(val)}
            if tail:
                recurse(tail, plugin_paths)
            else:
                with multiprocessing.Pool(processes=os.environ.get('NPROC')) as pool:
                    r = results[b]['plugins'].get(p_id, [])
                    r.extend(pool.starmap(run_binary, [(tests, b, params, v, opts['sim_timeout'], opts['hard_timeout'], tests['plugins'][p_id].get("additional_params", {}), {'PQUIC_PLUGINS': plugin_paths}) for v in ParamsGenerator(params, wsp_matrix).generate_values_until(test_args.limit)]))
                    results[b]['plugins'][p_id] = r
            if val:
                del params[variant]

        # save a backup just in case
        with open(os.path.join("{}.bkp".format(test_args.results)), 'w') as f:
            json.dump(results, f)
            print("saved backup")
        os.system("rm -rf /tmp/pquic*")


    for p_id in opts['variants']['plugins']:
        plugin_paths = ','.join(tests['plugins'][p_id]['plugins']).strip()
        recurse(variants, plugin_paths)














    #
    # for p_id in opts['variants']['plugins']:
    #     plugin_paths = ','.join(tests['plugins'][p_id]['plugins']).strip()
    #     for f in opts['variants'].get('filesize', [None]):
    #         if f and not 'filesize' in params:
    #             params['filesize'] = {'range': [f, f], 'type': type(f)}
    #         for lr in opts['variants'].get('loss_rate_to_client', [None]):
    #             if lr and not 'loss_rate_to_client' in params:
    #                 params['loss_rate_to_client'] = {'range': [lr, lr], 'type': type(lr)}
    #             for rwin in opts['variants'].get('stream_receive_window_size', [None]):
    #                 if rwin and not 'stream_receive_window_size' in params:
    #                     params['stream_receive_window_size'] = {'range': [rwin, rwin], 'type': type(rwin)}
    #                 with multiprocessing.Pool(processes=os.environ.get('NPROC')) as pool:
    #                     r = results[b]['plugins'].get(p_id, [])
    #                     r.extend(pool.starmap(run_binary, [(tests, b, params, v, opts['sim_timeout'], opts['hard_timeout'], tests['plugins'][p_id].get("additional_params", {}), {'PQUIC_PLUGINS': plugin_paths}) for v in ParamsGenerator(params, wsp_matrix).generate_all_values()]))
    #                     results[b]['plugins'][p_id] = r
    #                 if rwin:
    #                     del params['stream_receive_window_size']
    #             if lr:
    #                 del params['loss_rate_to_client']
    #
    #         if f:
    #             del params['filesize']

with open(os.path.join(test_args.results), 'w') as f:
    json.dump(results, f)
