#! /usr/bin/python3

import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("-t", help="output file", default="json_to_db.db")
parser.add_argument("--param", help="param=value to only select when param is equal to the specified value (str equality is checked)", default=None)
parser.add_argument("--testnames", help="represents the name of all the tests candidates, separated by commas", default=None)
parser.add_argument("--test-suite-name", help="represents the name of the ns3 test suite that has been run", default="droplist")
parser.add_argument("json_file_path", help="path to the json file containing the ns3 results")

args = parser.parse_args()

class TypeWrapper(object):
    def __init__(self, type_builtin, name):
        self.builtin = type_builtin
        self.name = name

    def __call__(self, *args, **kwargs):
        return self.builtin(*args, **kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


int = TypeWrapper(int, "INTEGER")
float = TypeWrapper(float, "REAL")
str = TypeWrapper(str, "TEXT")


network_parameters = {
    "bw": {"json_name": "bandwidth", "type": float},  # Mbps
    "loss_rate_to_server": {"type": float},  # %
    "loss_rate_to_client": {"type": float},  # %
    # "avg_burst_size_to_client": {"type": float},  # %
    # "avg_burst_size_to_server": {"type": float},  # %
    "delay_ms": {"json_name": "delay", "type": float},  # ms
    "file_size": {"json_name": "filesize", "type": float},  # ms
    # "wifi_distance_meters": {"json_name": "wifi_distance_meters", "type": float},  # ms
    "stream_receive_window_size": {"json_name": "stream_receive_window_size", "type": float},
    "seed": {"type": int},  # ms
}

experiments_results = {
    "time": {"json_name": "transfer_time", "type": float},
}

message_based_metrics = [
    "message_min_delivery_delay",
    "message_max_delivery_delay",
    "message_avg_delivery_delay",
    "message_median_delivery_delay",
    "message_long_deliveries_pct",
    "message_75_pct_delivery_delay",
    "message_90_pct_delivery_delay",
    "message_95_pct_delivery_delay",
    "message_97_pct_delivery_delay",
    "message_98_pct_delivery_delay",
    "message_99_pct_delivery_delay",
]

bytes_based_metrics = [
    "client_bytes_sent",
    "server_bytes_sent",
]

cwin_based_metrics = [
    "avg_cwin_server",
    "med_cwin_server",
    "max_cwin_server",
    "min_cwin_server",
    "pct_75_cwin_server",
    "pct_90_cwin_server",
    "pct_95_cwin_server",
]

metrics = bytes_based_metrics if args.test_suite_name == "rwin-limited-download" else (bytes_based_metrics + message_based_metrics)

additional_metric_module_name = "additional_metrics_bytes_sent" if args.test_suite_name == "rwin-limited-download" else "additional_metrics_message_based"

if args.test_suite_name != "rwin-limited-download":
    network_parameters.pop("stream_receive_window_size")

additional_experiments_results = {
    key: {"type": float} for key in metrics
}


def generate_sql_create_table(tests_names, network_parameters, experiments_results):
    lines = []
    for name in network_parameters:
        lines.append("{} {} NOT NULL".format(name, str(network_parameters[name]["type"])))
    for name in experiments_results:
        for test_name in tests_names:
            lines.append("{}_{} {} NOT NULL".format(name, test_name, str(experiments_results[name]["type"])))


    return """
    CREATE TABLE IF NOT EXISTS results (
      {}
    );
    """.format(',\n'.join(lines))


def generate_sql_insert(row):
    retval = []

    column_names = sorted(row.keys())

    return """ INSERT INTO results ({}) VALUES ({}); """.format(", ".join(column_names), ", ".join([str(row[col]) for col in column_names]))


def build_rows(ns3_results_dict, test_suite_name, tests_names, network_parameters, experiment_results, additional_experiment_results, additional_metrics_collector_name, param_name, param_value):
    ns3_suite_results = ns3_results_dict[test_suite_name]["plugins"]
    rows = []
    delays = []
    for i, tests_results in enumerate(list(zip(*[ns3_suite_results[test_name] for test_name in tests_names]))):
        try:
            delays.append(tests_results[0]["values"]["delay"])
            row = {}
            if any([not result["transfer_time"] for result in tests_results]) or (param_name is not None and any(str(result["values"][param_name][0]) != param_value for result in tests_results)):
                continue
            for result in tests_results:
                result["transfer_time"] = result["transfer_time"].replace(" ms", "")

            # add the network parameters
            for param, param_dict in network_parameters.items():
                json_param_name = param_dict.get("json_name", param)
                if any([tests_results[0]["values"][json_param_name] != result["values"][json_param_name] for result in tests_results[1:]]):
                    print(json_param_name)
                    print(tests_results[0]["values"][json_param_name])
                    raise Exception("cannot match two results")
                if len(tests_results[0]["values"][json_param_name]) != 1:
                    raise Exception("wrong length")
                row[param] = param_dict["type"](tests_results[0]["values"][json_param_name][0])

            # add the first experiments_results
            for param, param_dict in experiment_results.items():
                json_param_name = param_dict.get("json_name", param)
                for test_name, test_results in zip(tests_names, tests_results):
                    row["{}_{}".format(param, test_name)] = test_results[json_param_name]

            # add the additoonal experiments_results
            for param, param_dict in additional_experiment_results.items():
                json_param_name = param_dict.get("json_name", param)
                for test_name, test_results in zip(tests_names, tests_results):
                    row["{}_{}".format(param, test_name)] = test_results["additional_metrics"][additional_metrics_collector_name][json_param_name]
            rows.append(row)
        except Exception as e:
            print("exception", e)
            raise e
    return rows


tests_names = args.testnames.split(",")

with open(args.json_file_path, "r") as f:
    ns3_results_dict = json.load(f)
    [param_name, param_value] = [None, None] if args.param is None else args.param.split("=")
    rows = build_rows(ns3_results_dict, args.test_suite_name, tests_names, network_parameters, experiments_results, additional_experiments_results, additional_metric_module_name, param_name, param_value)

    conn = sqlite3.connect(args.t)
    cursor = conn.cursor()
    cursor.execute(generate_sql_create_table(tests_names, network_parameters,
                                             dict(**experiments_results, **additional_experiments_results)))
    for row in rows:
        cursor.execute(generate_sql_insert(row))
    conn.commit()
