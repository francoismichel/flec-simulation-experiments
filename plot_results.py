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
parser.add_argument("-m", help='plot method: can be "CDF", "uni", uni_favorable_path or "scatter"', default="CDF")
parser.add_argument("--cdf-multiplex-metric", help='name of the metric on which to multiplex the CDF curves: one curve for each value of this metric', default=None)
parser.add_argument("--cdf-multiplex-metric-in-bytes", action="store_true", default=False, help='if set, the --cdf-multiplex-metric should be interpreted as bytes and the labels updated accordingly')
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
parser.add_argument("--multi-subfigures", help="if set, plot one subfigure per -f provided", default=None)
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
              'text.latex.preamble': ['\\usepackage{gensymb}','\\usepackage{amsmath}','\\usepackage{amssymb}'],
              'axes.labelsize': 9, # fontsize for x and y labels (was 10)
              'axes.titlesize': 9,
              #'text.fontsize': 9, # was 10
              'legend.fontsize': 9, # was 10
              'xtick.labelsize': 9,
              'ytick.labelsize': 9,
              'text.usetex': True,
              'figure.figsize': [fig_width,fig_height],
              'font.family': 'serif'
    }

    matplotlib.rcParams.update(params)

# plt.figure(figsize=(3, 1.8), dpi=500)
plt.figure(figsize=(3, 2), dpi=500)



latexify()

n_subfigures = len(files) if args.multi_subfigures else 1

maxlen = max(len(files), len(files2), len(files3), len(name1), len(name2), len(name3))

for l in files, files2, files3, name1, name2, name3:
    while len(l) < maxlen:
        l.append(None)

for i, (filename, filename2, filename3, METHOD_1, METHOD_2, METHOD_3) in enumerate(zip(files, files2, files3, name1, name2, name3)):
    if i == 0 or args.multi_subfigures:
        sp = plt.subplot(1, n_subfigures, i+1)
    transform = args.transform
    plot_method = args.m


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
    markers = ["+", ".", "v", "D", "X"]
    lines = ["--", "-", "-.", "dotted", (0, (3, 1, 1, 1, 1, 1))]

    linewidth = 2
    marker = "."
    mew = 0.1
    markersize = 0

    idx = i

    def plot_cdf(x_axes, y_axis, transform, color=None, label=None, linestyle=None, log=False):
        if idx == 0:
            plt.ylabel(args.m if args.ylabel is None else args.ylabel)
        else:
            plt.ylabel(" ")
        plt.xlabel("%s" % transform_unit[transform] if args.xlabel is None else args.xlabel)
        if transforms_output[transform] > 1 or color is None or label is None:
            for i in range(transforms_output[transform]):
                if type(label) is list:
                    l = label[i]
                else:
                    l = label
                plt.plot([math.log(n, 10) for n in x_axes[i]] if log else x_axes[i], y_axis, color=colors[i], linewidth=linewidth, marker=marker, linestyle="-" if linestyle is None else linestyle,
                         markeredgewidth=mew, label=transforms_labels[transform][i] if l is None else l, ms=markersize)
        else:
            plt.plot([math.log(n, 10) for n in x_axes[0]] if log else x_axes[0], y_axis, color=color, linewidth=linewidth/1.33, marker=marker, linestyle="-" if linestyle is None else linestyle,
                     markeredgewidth=mew, label=label, ms=markersize)

    def plot_uni(y_axes, x_axes, transform, marker="+", color=None, label=None, linestyle=None, log=False):
        colors = ["darkblue", "deeppink", "green", "grey", "black"]
        mew = 1
        markersize = 2.5
        if idx == 0:
            plt.ylabel(args.m if args.ylabel is None else args.ylabel)
        else:
            #plt.ylabel(" ")
            pass
        plt.xlabel("%s" % transform_unit[transform] if args.xlabel is None else args.xlabel)
        if transforms_output[transform] > 1 or color is None or label is None:
            for i in range(transforms_output[transform]):
                if type(label) is list:
                    l = label[i]
                else:
                    l = label
                plt.plot(x_axes[i], [math.log(n, 10) for n in y_axes[i]] if log else y_axes[i], color=colors[i], linewidth=linewidth, marker=markers[i], linestyle="-" if linestyle is None else linestyle,
                         markeredgewidth=mew/2, label=transforms_labels[transform][i] if l is None else l, ms=markersize)
        else:

            plt.plot(x_axes[0], [math.log(n, 10) for n in y_axes[0]] if log else y_axes[0], color=color, linewidth=linewidth, marker=marker, linestyle="-" if linestyle is None else linestyle,
                     markeredgewidth=mew/2, label=label, ms=markersize)

        if args.linear_regression and transforms_output[transform] == 1:
            lr = LinearRegression()
            res = {}
            for func in [lr.fit, lr.score]:
                res[func] = func([[x] for i, x in enumerate(x_axes) if not remove_outliers or y_axes[0][i] < 100], [math.log(n, 10) for n in y_axes[0] if not remove_outliers or n < 100] if args.ylog else y_axes[0])
            plt.plot(x_axes, [10 ** n for n in lr.predict([[x] for x in x_axes])] if args.ylog else y_axes[0], color="red", ms=markersize / 8, markeredgewidth=mew / 8, linewidth=linewidth / 8)
            plt.title("{}y = {}*x + {}, R² = {}".format(args.title_prefix, round(float(lr.coef_), 4), round(float(lr.intercept_), 4), round(float(res[lr.score]), 4)), fontsize=6)


    def plot_json(file, color=None, label=None, linestyle=None):
        import json
        with open(file) as f:
            l = sorted(json.loads(f.read()))
            x = [elem[0]/1000000 for elem in l]
            y = [elem[1] for elem in l]
            plt.ylabel("cwin (bytes)")
            plt.xlabel("time (ms)")
            plt.plot(x, y, color="darkblue" if color is None else color, linewidth=0.25, marker=marker, linestyle="-" if linestyle is None else linestyle,
                     markeredgewidth=mew, ms=markersize, label=label)


    plt.rcParams["toolbar"] = "toolmanager"
    plt.tight_layout()

    plt.grid(True)

    if filename[-5:] == ".json":
        plot_json(filename, label=args.legend1)
        if filename2 is not None:
            plot_json(filename2, color="hotpink", linestyle="-", label=args.legend2)
    else:
        conn = sqlite3.connect(filename)

        c = conn.cursor()

        conn2 = None
        c2 = None
        c3 = None

        if args.fsecondtest is not None:
            conn2 = sqlite3.connect(filename2)
            c2 = conn2.cursor()



            if args.fthirdtest is not None:
                conn3 = sqlite3.connect(filename3)
                c3 = conn3.cursor()

        metrics = args.metric.split(",") if "," in args.metric else [args.metric]

        def plot(filesize, metric, marker=None, color=None, label=None, linestyle=None):
            if c2 is None:
                if plot_method == "CDF":
                    c.execute("SELECT {0}_{1}, {0}_{2} {4} FROM results WHERE bw != 0 {3} AND {0}_{1} != -1 AND {0}_{2} > 0"
                              .format(metric, METHOD_1, METHOD_2, ("AND file_size == %d" % filesize) if filesize is not None else "", (", " + args.cdf_multiplex_metric) if args.cdf_multiplex_metric else ""))
                else:
                    c.execute("SELECT {0}_{1}, {0}_{2}, {4} {5} FROM results WHERE bw != 0 {3} AND {0}_{1} != -1 AND {0}_{2} > 0"#" AND stream_receive_window_size = 400000"
                              .format(metric, METHOD_1, METHOD_2, ("AND file_size == %d" % filesize) if filesize is not None else "", ", ".join(args.uni_x_metric.split(",")), (", " + args.cdf_multiplex_metric) if args.cdf_multiplex_metric else ""))
                res = c.fetchall()


            else:
                if args.gemodel:
                    loss_cols = "h, k, p, r"
                else:
                    loss_cols = "loss"
                # search in two different files
                c.execute("SELECT {0}_{1}, bw, {2}, delay_ms, file_size FROM results WHERE bw != 0 {3} AND {0}_{1} > 0"
                          .format(metric, METHOD_1, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

                res1 = c.fetchall()

                c2.execute("SELECT {0}_{1}, bw, {2}, delay_ms, file_size FROM results WHERE bw != 0 {3} AND {0}_{1} > 0"
                          .format(metric, METHOD_2, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

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
                                  .format(metric, METHOD_3, loss_cols, ("AND file_size == %d" % filesize) if filesize is not None else ""))

                        res3 = c3.fetchall()
                    for i, elem in enumerate(res1):
                        if i >= len(tmp_res) or (c3 is not None and i >= len(res3)):
                            break
                        if c3 is not None:
                            res.append((elem[0], tmp_res[i][0], res3[i][0]))
                        else:
                            res.append((elem[0], tmp_res[i][0]))

            metric_vals = []


            if plot_method == "CDF":
                multiplexing_vals = sorted(set([r[2] for r in res])) if args.cdf_multiplex_metric is not None else [None]
                orig_results = res[:]
                for i, val in enumerate(multiplexing_vals):
                    res = [r[:2] for r in orig_results if val is None or r[2] == val]

                    transformed_result = list(map(transforms[transform], res))

                    to_plot = [list(sorted([r[i] for r in transformed_result])) for i in range(transforms_output[transform])]
                    y_axis = [(i+1)/len(res) for i in range(len(res))]
                    if args.transform == "none":
                        if args.labelfirsttest is not None and args.labelsecondtest is not None:
                            label = ["{} {}".format(label, args.labelfirsttest), "{} {}".format(label, args.labelsecondtest)]
                        else:
                            label = ["{} {}".format(label, args.namefirsttest), "{} {}".format(label, args.namesecondtest)]
                    if val is not None and args.cdf_multiplex_metric_in_bytes:
                        label = (str(int(val // 1000)) + "kB") if val < 1000000 else (str(int(val // 1000000)) + "MB")
                    plot_cdf(to_plot, y_axis, transform, color if val is None else colors[i], label, linestyle if val is None else lines[i])#, log=args.log)
            elif plot_method == "uni":
                metric_vals = [r[2:] for r in res]
                res = [r[:2] for r in res]
                if len(metric_vals) > 0 and len(metric_vals[0]) == 1 and transforms_output[transform] > 1:
                    metric_vals = [x * transforms_output[transform] for x in metric_vals]

                transformed_result = list(map(transforms[transform], res))

                to_plot = [[r[i] for r in transformed_result] for i in range(transforms_output[transform])]
                x_axis = [[v[i] for v in metric_vals] for i in range(transforms_output[transform])]
                # x_axis = metric_vals
                if args.transform == "none":
                    if args.labelfirsttest is not None and args.labelsecondtest is not None:
                        label = ["{} {}".format(label or "", args.labelfirsttest), "{} {}".format(label or "", args.labelsecondtest)]
                    else:
                        label = ["{} {}".format(label or "", args.namefirsttest), "{} {}".format(label or "", args.namesecondtest)]
                plot_uni(to_plot, x_axis, transform, marker, color, label, "None")

        if args.log:
            #plt.xlim(-1, 1)
            #plt.xticks([-0.5, 0, 0.5])
            plt.xscale("log")

            if args.xlim is not None:
                a, b = args.xlim.split(",")
                plt.xlim([float(a), float(b)])
            else:
                # plt.xlim(0.25, 4)
                # plt.xlim(0.5, 2)
                pass
                plt.minorticks_off()
            if args.xticks is not None:
                plt.minorticks_off()
                ticks_str, tickslabels = args.xticks.split("=") if "=" in args.xticks else (args.xticks, args.xticks)
                xticks = [float(t) for t in ticks_str.split(",")]
                plt.xticks(xticks, tickslabels.split(","))
            else:
                # plt.xticks([0.1, 0.5, 1, 2, 10], [0.1, 0.5, 1, 2, 10])
                # plt.xticks([0.25, 0.5, 0.75, 1, 1.33, 2, 4], [0.25, 0.5, 0.75, 1, 1.33, 2, 4])
                pass
        else:
            if args.xlim is not None:
                a, b = args.xlim.split(",")
                plt.xlim([float(a), float(b)])
            else:
                pass
            if args.xticks is not None:
                ticks_str, tickslabels = args.xticks.split("=") if "=" in args.xticks else (args.xticks, args.xticks)
                xticks = [float(t) for t in ticks_str.split(",")]
                plt.xticks(xticks, tickslabels.split(","))
            else:
                pass
        if args.ylog:
            plt.yscale("log")

        methods_1 = [METHOD_1] if "," not in METHOD_1 else METHOD_1.split(",")

        files_db = [filename] if "," not in filename else filename.split(",")
        for meth_idx, method_1 in enumerate(methods_1):
            METHOD_1 = method_1
            filename = files_db[meth_idx % len(files_db)]
            conn = sqlite3.connect(filename)

            c = conn.cursor()
            for metric_idx, metric in enumerate(metrics):
                try:
                    filesize = None if args.filesize is None else int(args.filesize)

                    plot(filesize, metric, marker=markers[meth_idx + metric_idx + i] if len(methods_1) > 1 or len(name1) > 0 else None, color=colors[meth_idx + metric_idx + i], label=legends[meth_idx + metric_idx + i] if legends is not None else None)
                except ValueError:
                    for i, size in enumerate([int(i) for i in args.filesize.split(',')]):
                        if size != 0:
                            plot(size, metric, marker=markers[meth_idx + metric_idx + i] if len(methods_1) > 1 else None, color=colors[meth_idx + metric_idx + i], label=legends[meth_idx + metric_idx+i] if legends is not None else ("%sB" % str(size)).replace("000000B", "MB").replace("000B", "kB"), linestyle=lines[i])



if n_subfigures == 1 or len(name1) == 1:
    # legend = plt.legend(framealpha=0.6)
    # change the legend font size
    legend = plt.legend(framealpha=0.6, prop={'size': 8})
    # use the following for the fairness tests
    # handles, labels = sp.get_legend_handles_labels()
    # plt.figlegend(handles, labels)
    # frame = legend.get_frame()
    # frame.set_facecolor('0.8')
    # frame.set_edgecolor('0.8')

else:
    handles, labels = sp.get_legend_handles_labels()
    legend = plt.figlegend(handles, labels, loc='upper center', ncol=5, framealpha=0.1)


if args.xlabel:
    plt.xlabel("%s" % transform_unit[transform] if args.xlabel is None else args.xlabel)
if legend:
    # frame = legend.get_frame()
    # frame.set_facecolor('0.8')
    # frame.set_edgecolor('0.8')
    pass


if args.no_legend:
    plt.legend().remove()

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

limit_plot_frame = False
if limit_plot_frame or args.ylim is not None:
    if args.yticks is not None:
        ticks_str, tickslabels = args.yticks.split("=") if "=" in args.yticks else (args.yticks, args.yticks)
        yticks = [float(t) for t in ticks_str.split(",")]
        plt.yticks(yticks, tickslabels.split(","))
    else:
        plt.yticks(list(plt.yticks()[0]) + [1])
    if args.ylim is not None:
        a, b = args.ylim.split(",")
        plt.ylim([float(a), float(b)])
    else:
        plt.ylim([0.1, 10])
    plt.minorticks_off()

if args.title:
    plt.title("\n".join([args.title]))

if args.t:
    plt.savefig(args.t, bbox_inches="tight")
else:
    plt.show()

