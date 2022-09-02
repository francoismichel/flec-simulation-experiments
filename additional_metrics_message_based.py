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

    if init_time_client - init_time_server != 5000000:
        raise Exception("wrong client-server clock synchronization: {} VS {}...".format(init_time_client, init_time_server))

    total_byte_sent_client = 0
    total_byte_sent_server = 0

    stream_ids = set()
    current_message_offset = {}
    cwin_values = []
    for ev in result:
        if ev["type"] == "message_enqueue":
            stream_ids.add(ev["stream_id"])
            length = ev["length"]
            if ev["stream_id"] not in messages_sent:
                messages_sent[ev["stream_id"]] = {}
                current_message_offset[ev["stream_id"]] = 0
            offset = current_message_offset[ev["stream_id"]]
            messages_sent[ev["stream_id"]][offset] = {"offset": offset, "length": length, "end": offset+length, "time": ev["time"]}
            current_message_offset[ev["stream_id"]] += length
        elif ev["type"] == "stream_deliver":
            [offset, length] = ev["range"]
            if ev["stream_id"] not in delivered_stream_events:
                delivered_stream_events[ev["stream_id"]] = {}
            delivered_stream_events[ev["stream_id"]][offset] = {"offset": offset, "length": length, "end": offset+length, "time": ev["time"]}
        elif ev["type"] == "client_packet_sent":
            total_byte_sent_client += ev["length"]
        elif ev["type"] == "server_packet_sent":
            total_byte_sent_server += ev["length"]
        elif ev["type"] == "cwin_server":
            cwin_values.append(ev["cwin"])

    received_messages = []
    for id in stream_ids:
        if id in delivered_stream_events:
            # sorted by last byte
            sorted_delivered_stream_events = sorted([((offset + val["length"]), val) for offset, val in delivered_stream_events[id].items() if val["length"] > 0])
            sorted_messages = sorted([(offset, offset + val["length"]) for offset, val in messages_sent[id].items()])
            current_message_idx = 0
            # O(n)
            for end, val in sorted_delivered_stream_events:
                if val["length"] > 0:
                    message_offset, message_end = sorted_messages[current_message_idx]
                    if end >= message_end:
                        # the message has been delivered at this time
                        messages_sent[id][message_offset]["delivery_time"] = val["time"] - \
                                                                         messages_sent[id][message_offset]["time"]
                        if messages_sent[id][message_offset]["delivery_time"] < 0:
                            with open("/tmp/weird_serv.txt", "w") as f:
                                file_serv.seek(0)
                                f.write(file_serv.read())
                            with open("/tmp/weird_cli.txt", "w") as f:
                                file_cli.seek(0)
                                f.write(file_cli.read())
                            raise Exception("negative value")
                        current_message_idx += 1
                              # because there could be more than 1 message sent for one stream id
            received_messages += [(float(x["delivery_time"]), id) for offset, x in messages_sent[id].items() if "delivery_time" in x]


    total_messages_sent = 0
    for id, messages in messages_sent.items():
        total_messages_sent += len(messages)

    if not received_messages:
        return {}
    received_messages = sorted(received_messages)
    received_times = [x[0] for x in received_messages]
    median_dataset = received_times if len(received_times) == total_messages_sent else (received_times + [9999999999 for _ in range(total_messages_sent - len(received_times))])
    median = median_dataset[int(len(median_dataset)/2)]

    pct = {p: median_dataset[int(len(median_dataset)*p/100)] for p in [75, 90, 95, 97, 98, 99]}

    minimum = median_dataset[0]
    maximum = median_dataset[-1]
    avg = sum(received_times)/len(received_times)
    long_pct = 1


    print(len(received_messages), "messages received in total")
    out_of_deadline_messages = [x for x in received_messages if x[0] > message_deadline]
    print(len(out_of_deadline_messages), "messages received out of deadline")
    print("\n".join(["{}, {}".format(x[0], x[1]) for x in out_of_deadline_messages]))
    print()
    print(total_messages_sent, "messages sent in total")

    sorted_cwin_values = sorted(cwin_values)

    retval = {
        "message_min_delivery_delay": minimum,
        "message_max_delivery_delay": maximum,
        "message_median_delivery_delay": median,

        "message_75_pct_delivery_delay": pct[75],
        "message_90_pct_delivery_delay": pct[90],
        "message_95_pct_delivery_delay": pct[95],
        "message_97_pct_delivery_delay": pct[97],
        "message_98_pct_delivery_delay": pct[98],
        "message_99_pct_delivery_delay": pct[99],

        "message_avg_delivery_delay": avg,
        # "message_long_deliveries_pct": float(len([x for x, val in messages_sent.items() if val["delivery_time"] <= message_deadline]))/float(len(received_times)),
        "message_long_deliveries_pct": float(len([x for x in received_times if x <= message_deadline]))/float(total_messages_sent),
        "client_bytes_sent": total_byte_sent_client,
        "server_bytes_sent": total_byte_sent_server,


        "avg_cwin_server": sum(sorted_cwin_values)/max(len(sorted_cwin_values), 1),
        "med_cwin_server": (sorted_cwin_values or [-1])[len(sorted_cwin_values)//2],
        "max_cwin_server": (sorted_cwin_values or [-1])[-1],
        "min_cwin_server": (sorted_cwin_values or [-1])[0],
        "pct_75_cwin_server": (sorted_cwin_values or [-1])[int(0.75*len((sorted_cwin_values or [-1])))],
        "pct_90_cwin_server": (sorted_cwin_values or [-1])[int(0.90*len((sorted_cwin_values or [-1])))],
        "pct_95_cwin_server": (sorted_cwin_values or [-1])[int(0.95*len((sorted_cwin_values or [-1])))],
    }

    pprint.pprint(retval)

    return retval


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as file_serv:
        with open(sys.argv[2]) as file_cli:
            collect_metrics(file_serv, file_cli, {}, message_deadline=250000)
