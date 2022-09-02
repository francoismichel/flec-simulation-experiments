import json

import pprint

def collect_metrics(file_serv, file_cli, params, message_deadline=250000):
    """

    :param file_server: the server log file
    :param file_client: the client log file
    :param message_deadline: the server log filename
    :param params: the dictionary containing the ns3 network params
    :return: {
        "message_min_delivery_delay": [float],
        "message_max_delivery_delay": [float],
        "message_median_delivery_delay": [float],
        "message_avg_delivery_delay": [float],
        "message_long_deliveries_pct": [float] (in [0,1]) # long_pct is the percentile where the delivery delay goes beyond the allowed deadline
    }
    returns {} if not packet reception event occurred
    """

    result = []
    messages_sent = {}
    delivered_stream_events = {}

    base = 0

    init_time_client = -1
    init_time_server = -2

    for line in file_serv:
        if "INIT TIME" in line:
            print("serv", line)

        if "EVENT::" in line:
            ev = json.loads(line.replace("EVENT::", ""))
            if ev["type"] == "packet_sent":
                ev["type"] = "server_packet_sent"
            elif ev["type"] == "cwin":
                ev["type"] = "cwin_server"
            elif ev["type"] == "init":
                init_time_server = ev["time"]
            result.append(ev)
            if base == 0:
                base = ev["time"]
            time = ev["time"] - base

    for line in file_cli:
        if "INIT TIME" in line:
            print("cli", line)
        if "EVENT::" in line:
            ev = json.loads(line.replace("EVENT::", ""))
            if ev["type"] == "packet_sent":
                ev["type"] = "client_packet_sent"
            elif ev["type"] == "cwin":
                ev["type"] = "cwin_client"
            elif ev["type"] == "init":
                init_time_client = ev["time"]
            result.append(ev)
            if base == 0:
                base = ev["time"]
            time = ev["time"] - base

    total_byte_sent_client = 0
    total_byte_sent_server = 0

    stream_ids = set()
    current_message_offset = {}
    cwin_values = []
    for ev in result:
        if ev["type"] == "client_packet_sent":
            total_byte_sent_client += ev["length"]
        elif ev["type"] == "server_packet_sent":
            total_byte_sent_server += ev["length"]
        elif ev["type"] == "cwin_server":
            cwin_values.append(ev["cwin"])

    sorted_cwin_values = sorted(cwin_values) or [-1]

    retval = {
        "client_bytes_sent": total_byte_sent_client,
        "server_bytes_sent": total_byte_sent_server,

        "avg_cwin_server": sum(sorted_cwin_values)/len(sorted_cwin_values),
        "med_cwin_server": sorted_cwin_values[len(sorted_cwin_values)//2],
        "max_cwin_server": sorted_cwin_values[-1],
        "min_cwin_server": sorted_cwin_values[0],
        "pct_75_cwin_server": sorted_cwin_values[int(0.75*len(sorted_cwin_values))],
        "pct_90_cwin_server": sorted_cwin_values[int(0.90*len(sorted_cwin_values))],
        "pct_95_cwin_server": sorted_cwin_values[int(0.95*len(sorted_cwin_values))],
    }

    pprint.pprint(retval)

    return retval


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as file_serv:
        with open(sys.argv[2]) as file_cli:
            collect_metrics(file_serv, file_cli, {}, message_deadline=250000)
