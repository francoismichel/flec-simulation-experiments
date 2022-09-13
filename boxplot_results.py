import argparse
import math
import os
import shutil
import sqlite3

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from sklearn.linear_model import LinearRegression


parser = argparse.ArgumentParser()
parser.add_argument("-f", help="input filename")
parser.add_argument("-fsecondtest", help="input filename for the second test", default=None)
parser.add_argument("-t", help="output file", default="")
parser.add_argument("--metric", help="name of the metric we want to plot", default="time")
parser.add_argument("-m", help='plot method: currently always "boxplot"', default="boxplot")
parser.add_argument("--uni-x-metric", help='name of the metric to put on the x axis if the method is uni', default="delay_ms")
parser.add_argument("--transform", help='transform method: can be "none" "ratio" or "difference"', default="none")
parser.add_argument("--filesize", type=str, help='file size for which the data must be looked at', default=None)
parser.add_argument("--namefirsttest", help="represents the name of the first test", default=None)
parser.add_argument("--namesecondtest", help="represents the name of the second test", default=None)
parser.add_argument("--labelfirsttest", help="represents the short name of the first test", default=None)
parser.add_argument("--labelsecondtest", help="represents the short name of the second test", default=None)
parser.add_argument("--gemodel", action="store_true", default=False)
parser.add_argument("--log", action="store_true", default=False)
parser.add_argument("--ylog", action="store_true", default=False)
parser.add_argument("--xlabel", type=str, default=None)
parser.add_argument("--ylabel", type=str, default=None)
parser.add_argument("--xlim", type=str, default=None)
parser.add_argument("--ylim", type=str, default=None)
parser.add_argument("--xticks", type=str, default=None)
parser.add_argument("--yticks", type=str, default=None)
parser.add_argument("--title", type=str, default=None)
parser.add_argument("--legend1", type=str, default=None)
parser.add_argument("--legend2", type=str, default=None)
parser.add_argument("--legends", type=str, default=None)
parser.add_argument("--no-legend", action="store_true", default=False)
parser.add_argument("-fthirdtest", help="input filename for the third test", default=None)
parser.add_argument("--namethirdtest", help="represents the name of the third test", default=None)
parser.add_argument("--linear-regression", action="store_true", help="if set and the plot method is uni, draw a linear regression")
parser.add_argument("--title-prefix", help="specifies a text to prepend to the plot title if the plot method is uni", default="")

args = parser.parse_args()

files = args.f.split(",")
files2 = args.fsecondtest.split(",") if args.fsecondtest is not None else [None]*len(files)
files3 = args.fthirdtest.split(",") if args.fthirdtest is not None else [None]*len(files)
name1 = args.namefirsttest.split(",") if args.namefirsttest is not None else [None]*len(files)
name2 = args.namesecondtest.split(",") if args.namesecondtest is not None else [None]*len(files)
name3 = args.namethirdtest.split(",") if args.namethirdtest is not None else [None]*len(files)
legends = args.legends.split(",") if args.legends is not None else None

remove_outliers = True
limit_plot_frame = True

plt.figure(figsize=(3, 1.8), dpi=500)


def latexify(fig_width=None, fig_height=None, columns=1):
    """Set up matplotlib's RC params for LaTeX plotting.
    Call this before plotting a figure.

    Parameters
    ----------
    fig_width : float, optional, inches
    fig_height : float,  optional, inches
    columns : {1, 2}
    """

    # code adapted from http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples

    # Width and max height in inches for IEEE journals taken from
    # computer.org/cms/Computer.org/Journal%20templates/transactions_art_guide.pdf

    from math import sqrt

    assert(columns in [1,2])

    if fig_width is None:
        fig_width = 3.39 if columns==1 else 6.9 # width in inches

    if fig_height is None:
        golden_mean = (sqrt(5)-1.0)/2.0    # Aesthetic ratio
        fig_height = fig_width*golden_mean # height in inches

    MAX_HEIGHT_INCHES = 8.0
    if fig_height > MAX_HEIGHT_INCHES:
        print("WARNING: fig_height too large:" + fig_height +
              "so will reduce to" + MAX_HEIGHT_INCHES + "inches.")
        fig_height = MAX_HEIGHT_INCHES

    params = {'backend': 'ps',
              'text.latex.preamble': ['\\usepackage{gensymb}'],
              'axes.labelsize': 9, # fontsize for x and y labels (was 10)
              'axes.titlesize': 9,
              'legend.fontsize': 9, # was 10
              'xtick.labelsize': 9,
              'ytick.labelsize': 9,
              'text.usetex': True,
              'figure.figsize': [fig_width,fig_height],
              'font.family': 'serif'
    }

    matplotlib.rcParams.update(params)

latexify()

for i, (filename, filename2, filename3, METHOD_1, METHOD_2, METHOD_3) in enumerate(zip(files, files2, files3, name1, name2, name3)):
    sp = plt.subplot(1, len(files), i+1)
    transform = args.transform
    plot_method = args.m


    # METHOD_1 =  args.namefirsttest if args.namefirsttest is not None else "http_fec"
    # METHOD_2 =  args.namesecondtest if args.namesecondtest is not None else "http_non_fec"

    METHODS = [METHOD_1, METHOD_2]

    PARAMS = [TIME_AGGRESSIVE, TIME_DEFAULT, DELAY_0_IN, DELAY_0_OUT, DELAY_1_IN, DELAY_1_OUT, LAST_IP] = list(range(7))

    transforms = {
        "none": lambda x: x,
        "difference": lambda x: [x[0]-x[1]],
        "ratio": lambda x: [x[0]/x[1]]
    }

    transforms_output = {
        "none": 2,
        "difference": 1,
        "ratio": 1
    }

    transforms_labels = {
        "none": METHODS,
        "difference": ["{0}_{1} - {0}_{1}".format(args.metric, tuple(METHODS))],
        "ratio": ["{0}_{1}/{0}_{1}".format(args.metric, tuple(METHODS))]
    }

    transform_unit = {
        "none": "{0}".format(args.metric),
        "difference": "{0}_{1} - {0}_{1} (ms)".format(args.metric, tuple(METHODS)),
        "ratio": "{0}_{1}/{0}_{1}".format(args.metric, tuple(METHODS))
    }

    colors = ["darkblue", "hotpink", "green", "grey", "black"]
    lines = ["--", "-", "-.", "dotted", '-']

    linewidth = 2
    marker = "."
    mew = 0.1
    markersize = 0

    idx = i

    def boxplot(boxes, x_axis, transform, label=None, log=False):
        if idx == 0:
            # plt.ylabel(args.m)
            plt.ylabel(args.m if args.ylabel is None else args.ylabel)
        else:
            plt.ylabel(" ")
        plt.xlabel("%s" % transform_unit[transform] if args.xlabel is None else args.xlabel)
        boxes_to_plot = []
        for box in boxes:
            if log:
                boxes_to_plot.append([math.log(n, 10) for n in box])
            else:
                boxes_to_plot.append(box)
        if label is None:
            plt.boxplot(boxes_to_plot)
        else:
            plt.boxplot(boxes_to_plot)

        plt.xticks(range(1, len(boxes) + 1), [(str(int(size//1000)) + "kB") if size < 1000000 else (str(int(size//1000000)) + "MB") for size in x_axis]  ) # x_axis
        if args.xticks is not None:
            ticks_str, tickslabels = args.xticks.split("=") if "=" in args.xticks else (args.xticks, args.xticks)
            xticks = range(1, len(boxes) + 1)
            plt.xticks(xticks, tickslabels.split(","))


    plt.rcParams["toolbar"] = "toolmanager"
    plt.tight_layout()
    plt.grid(True)

    conn = sqlite3.connect(filename)

    c = conn.cursor()

    conn2 = None
    c2 = None

    if args.fsecondtest is not None:
        conn2 = sqlite3.connect(filename2)
        c2 = conn2.cursor()



        if args.fthirdtest is not None:
            conn3 = sqlite3.connect(filename3)
            c3 = conn3.cursor()



    def plot(filesize, color=None, label=None, linestyle=None):
        if c2 is None:
            if plot_method == "CDF":
                c.execute("SELECT {0}_{1}, {0}_{2} FROM results WHERE bw != 0 {3} AND {0}_{1} != -1 AND {0}_{2} > 0"
                          .format(args.metric, METHOD_1, METHOD_2, ("AND file_size == %d" % filesize) if filesize is not None else ""))
            else:
                c.execute("SELECT {0}_{1}, {0}_{2}, {4} FROM results WHERE bw != 0 {3} AND {0}_{1} != -1 AND {0}_{2} > 0"
                          .format(args.metric, METHOD_1, METHOD_2, ("AND file_size == %d" % filesize) if filesize is not None else "", args.uni_x_metric))
            res = c.fetchall()


        else:
            if args.gemodel:
                loss_cols = "h, k, p, r"
            else:
                loss_cols = "loss"
            # search in two different files
            c.execute("SELECT {0}_{1}, bw, {2}, delay_ms, file_size FROM results WHERE bw != 0 {3} AND {0}_{1} > 0"
                      .format(args.metric, METHOD_1, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

            res1 = c.fetchall()

            c2.execute("SELECT {0}_{1}, bw, {2}, delay_ms, file_size FROM results WHERE bw != 0 {3} AND {0}_{1} > 0"
                      .format(args.metric, METHOD_2, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

            tmp_res = c2.fetchall()
            res = []
            join = False
            if join:
                for elem in res1:
                    for elem2 in tmp_res:
                        if elem2[1:] == elem[1:]:  # if the parameters are the same
                            res.append((elem[0], elem2[0]))
                            break
            else:
                if c3 is not None:
                    c3.execute("SELECT {0}_{1}, bw, {2}, delay_ms, file_size FROM results WHERE bw != 0 {3} AND {0}_{1} > 0"
                              .format(args.metric, METHOD_3, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

                    res3 = c3.fetchall()
                for i, elem in enumerate(res1):
                    if i >= len(tmp_res) or (c3 is not None and i >= len(res3)):
                        break
                    if c3 is not None:
                        res.append((elem[0], tmp_res[i][0], res3[i][0]))
                    else:
                        res.append((elem[0], tmp_res[i][0]))

        ticks = args.xticks.split("=")[0].split(",")

        metric_vals = sorted(set([r[2] for r in res  if not all([r[2] != float(x) for x in ticks])]))

        boxes = []

        for xval in metric_vals:
            box_vals = [r[:2] for r in res if r[2] == xval]
            box = (list(map(transforms[transform], box_vals)))
            if transforms_output[transform] == 1:
                box = list(map(lambda x: x[0], box))
            boxes.append(box)


        if plot_method == "boxplot":
            x_axis = metric_vals
            boxplot(boxes, x_axis, transform, label)

    if args.ylog:
        plt.yscale("log")
    try:
        filesize = None if args.filesize is None else int(args.filesize)
        plot(filesize, label=legends[idx % len(legends)] if legends is not None else None)
    except ValueError:
        for i, size in enumerate([int(i) for i in args.filesize.split(',')]):
            if size != 0:
                plot(size, color=colors[i], label=("%sB" % str(size)).replace("000000B", "MB").replace("000B", "kB"), linestyle=lines[i])

if len(name1) == 1:
    legend = plt.legend()

else:
    handles, labels = sp.get_legend_handles_labels()
    legend = plt.figlegend(handles, labels, loc='upper center', ncol=5, bbox_to_anchor=(0.52, 1.1))

if args.xlabel:
    plt.xlabel("%s" % transform_unit[transform] if args.xlabel is None else args.xlabel)
if args.title:
    plt.title(args.title)
if legend:
    frame = legend.get_frame()
    frame.set_facecolor('0.8')
    frame.set_edgecolor('0.8')


if args.no_legend:
    plt.legend().remove()

plt.tight_layout()

limit_plot_frame = True

if limit_plot_frame or args.ylim is not None:
    if args.yticks is not None:
        ticks_str, tickslabels = args.yticks.split("=") if "=" in args.yticks else (args.yticks, args.yticks)
        yticks = [float(t) for t in ticks_str.split(",")]
        plt.yticks(yticks, tickslabels.split(","))
    else:
        yticks = [0.5, 0.75, 0.9, 10/9, 1.33, 2]
        labels = ["{:.2f}".format(tick) for tick in yticks]
        plt.yticks(list(plt.yticks()[0]) + [1])
    if args.ylim is not None:
        a, b = args.ylim.split(",")
        plt.ylim([float(a), float(b)])
    else:
        plt.ylim([0.5, 2])
    plt.minorticks_off()


if args.t:
    plt.savefig(args.t, bbox_inches="tight")
else:
    plt.show()

