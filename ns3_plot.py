#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import yaml


class Interval:
    def __call__(self, string):
        match = re.fullmatch(r"(?P<l>\d+\.?\d*?),(?P<h>\d+\.?\d*?)$", string.strip())
        if not match:
            raise argparse.ArgumentTypeError('Interval must be of form a,b')
        try:
            return float(match.group('l')), float(match.group('h'))
        except:
            raise argparse.ArgumentTypeError('Cannot convert interval values to float')


def deep_set(d, a, b, v):
    s = d.get(a, {})
    l = s.get(b, [])
    l.append(v)
    s[b] = l
    d[a] = s


parser = argparse.ArgumentParser(description='Plots results from a result file')
parser.add_argument('file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

subparsers = parser.add_subparsers(help='plot type help', dest='plot_type')
dct_ratio_cdf_parser = subparsers.add_parser('dct_ratio_cdf', help='plots a ratio of the DCT between two groups')
dct_ratio_cdf_parser.add_argument('-r', '--ref', type=str, required=True, help='the reference split group to compute the ratio from')  # TODO rephrase

dct_ratio_cdf_parser = subparsers.add_parser('dct_ratio_boxplot', help='plots a ratio of the DCT between two groups')
dct_ratio_cdf_parser.add_argument('-r', '--ref', type=str, required=True, help='the reference split group to compute the ratio from')  # TODO rephrase

gp_boxplot = subparsers.add_parser('gp_boxplot', help='plots the achieved goodput')

parser.add_argument('-t', '--test', help='plots results for TEST')
groups = {'filesize', 'plugin'}
parser.add_argument('-g', '--group-by', type=str, choices=groups, default='filesize', help='groups the plots in a single figure for this group')
parser.add_argument('-s', '--split-by', type=str, choices=groups, default='plugin', help='separates the plots over several figures for this group')
parser.add_argument('-xs', '--exclude-split', type=str, default='', help='excludes a group from the split group')
parser.add_argument('-xg', '--exclude-group', type=str, default='', help='excludes a group from the group group')
parser.add_argument('--xlim', type=Interval(), help='x axis limit interval')
parser.add_argument('--ylim', type=Interval(), help='y axis limit interval')

args = parser.parse_args()

if args.group_by == args.split_by:
    print("group-by and split-by parameters must be different groups")
    exit(-1)

script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'tests.yaml')) as f:
    tests = yaml.load(f, Loader=yaml.SafeLoader)

results = json.load(args.file)
documents = []

groups.discard(args.split_by)
params_id = {'bandwidth', 'delay', 'paths', 'queue', 'bandwidth_balance', 'delay_balance'} | set(groups)
unused_fields = {'cmdline', 'start', 'end'}
mandatory_fields = {'transfer_time'}

colors = ['#4daf4a', '#984ea3', '#f781bf', '#377eb8', '#ff7f00', '#e41a1c', '#a65628', '#999999']

for t, variants in results.items():
    for v, variant_results in variants['plugins'].items():
        for r in variant_results:
            r['plugin'] = v
            r['test'] = t
            try:
                r['transfer_time'] = float(re.match(r"\d+\.\d+\s(?=ms)", r['transfer_time'])[0])
            except:
                print("Invalid result:", r)
            for p, val in r['values'].items():
                r[p] = val
            del r['values']
            documents.append(r)

transfer_times = {}

for d in documents:
    for f in unused_fields:
        if f in d:
            del d[f]

    params = {}
    for p in params_id:
        if p in d:
            params[p] = d[p]
            if p != args.group_by:
                del d[p]

    times = transfer_times.get(str(params), [])
    times.append(d)
    transfer_times[str(params)] = times


def set_box_color(bp, color):
    plt.setp(bp['boxes'], color=color)
    plt.setp(bp['whiskers'], color=color)
    plt.setp(bp['caps'], color=color)
    plt.setp(bp['medians'], color=color)
    plt.setp(bp['fliers'], color=color, marker='.')


def new_fig():
    plt.figure()
    plt.clf()
    if args.xlim:
        plt.xlim(*args.xlim)
    if args.ylim:
        plt.ylim(*args.ylim)


ratios = {}
goodputs = {}

for params, runs in transfer_times.items():
    ref_time = None
    for r in runs:
        if 'ref' in args and str(r[args.split_by]) == args.ref:
            ref_time = r['transfer_time']

    if 'ref' in args and ref_time is None:
        print("Unable to get ref_time for ref:", args.ref)
        exit(0)
        continue

    for r in runs:
        group = str(r[args.group_by])
        split = str(r[args.split_by])
        if ('ref' not in args or split != args.ref) and split != args.exclude_split and group != args.exclude_group:
            if ref_time:
                ratio = r['transfer_time'] / ref_time
                deep_set(ratios, split, group, ratio)
            goodput = ((r['filesize'][0] * 8) / 1000000) / (r['transfer_time'] / 1000)
            deep_set(goodputs, split, group, goodput)

if args.plot_type == 'dct_ratio_boxplot':
    new_fig()
    plt.ylabel('DCT ratio (reference %s)' % args.ref)
    plt.xlabel(args.group_by.title())
    for s, c in zip(ratios, colors):
        set_box_color(plt.boxplot(ratios[s].values(), labels=ratios[s].keys(), sym='.', widths=0.6), c)
        plt.plot([], c=c, label=s.title())

    plt.legend()

elif args.plot_type == 'dct_ratio_cdf':
    for s in ratios:
        new_fig()
        plt.ylabel('CDF')
        plt.ylim(0, 1)
        plt.xlabel('DCT ratio %s/%s' % (s, args.ref))
        for (g, data), c in zip(ratios[s].items(), colors):
            increment = 1.0 / len(data)
            plt.plot(sorted(data), np.arange(0, 1, increment), c=c, label=g)

        plt.legend()
elif args.plot_type == 'gp_boxplot':
    new_fig()
    plt.ylabel('Achieved goodput (Mbps)')
    plt.xlabel(args.group_by.title())
    for s, c in zip(goodputs, colors):
        set_box_color(plt.boxplot(goodputs[s].values(), labels=goodputs[s].keys(), sym='.', widths=0.6), c)
        plt.plot([], c=c, label=s.title())

    plt.legend()

plt.show()
