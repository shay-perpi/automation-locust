import os
import sys
from datetime import time

myDir = os.getcwd()
sys.path.append(myDir)
from pathlib import Path

path = Path(myDir)
a = str(path.parent.absolute())
sys.path.append(a)
from common.strings import (
    BETWEEN_TIMER_STR,
    CONSTANT_PACING_TIMER_STR,
    CONSTANT_THROUGHPUT_TIMER_STR,
    CONSTANT_TIMER_STR,
    INVALID_TIMER_STR,
)
from config.config import WmtsConfig, config_obj
from locust import (
    HttpUser,
    between,
    constant,
    constant_pacing,
    constant_throughput,
    task, events,
)
from locust_plugins.csvreader import CSVReader

from utils.percentile_calculation import extract_response_time_from_record, count_rsp_time_by_rsp_time_ranges, \
    get_percentile_value, write_rsp_time_percentile_ranges

file_name = __name__ +'- stats.csv'
stat_file = open(file_name, 'w')
wmts_csv_path = WmtsConfig.WMTS_CSV_PATH
# wmts_csv_path = "/home/shayavr/Desktop/git/automation-locust-framework/csv_data/data/wmts_shaziri.csv"

ssn_reader = CSVReader(wmts_csv_path)


class User(HttpUser):
    timer_selection = config_obj["wmts"].WAIT_TIME_FUNC
    wait_time = config_obj["wmts"].WAIT_TIME
    timer_selection = timer_selection[0]
    wait_time = wait_time[0]
    if timer_selection == 1:
        wait_time = constant(wait_time)
        print(CONSTANT_TIMER_STR)
    elif timer_selection == 2:
        wait_time = constant_throughput(wait_time)
        print(CONSTANT_THROUGHPUT_TIMER_STR)
    elif timer_selection == 3:
        wait_time = between(config_obj["wmts"].MIN_WAIT, config_obj["wmts"].MAX_WAIT)
        print(BETWEEN_TIMER_STR)
    elif timer_selection == 4:
        wait_time = constant_pacing(wait_time)
        print(CONSTANT_PACING_TIMER_STR)
    else:
        print(INVALID_TIMER_STR)

    @task(1)
    def index(self):
        points = next(ssn_reader)
        if config_obj["wmts"].TOKEN is None:
            self.client.get(
                f"/{config_obj['wmts'].LAYER_TYPE}/"
                f"{config_obj['wmts'].LAYER_NAME}/"
                f"{config_obj['wmts'].GRID_NAME}/"
                f"{points[0]}/{points[1]}/{points[2]}"
                f"{config_obj['wmts'].IMAGE_FORMAT}",
            )
        else:
            self.client.get(
                f"/{config_obj['wmts'].LAYER_TYPE}/"
                f"{config_obj['wmts'].LAYER_NAME}/"
                f"{config_obj['wmts'].GRID_NAME}/"
                f"{points[0]}/{points[1]}/{points[2]}"
                f"{config_obj['wmts'].IMAGE_FORMAT}"
                f"?token={config_obj['wmts'].TOKEN}",
            )

    host = config_obj["wmts"].HOST

    # host = "http://lb-mapcolonies.gg.wwest.local/mapproxy-ww"

    def on_stop(self):
        rsp_list = extract_response_time_from_record(
            csv_path=file_name)

        # rsp_list_millisecond = convert_to_millisecond(response_time_list=rsp_list)
        percentile_rages_dict = {}
        rsp_time_ranges = [(0, 100), (101, 500), (501, None)]
        for idx, rsp_t_range in enumerate(rsp_time_ranges):
            counter = count_rsp_time_by_rsp_time_ranges(rsp_time_data=rsp_list, rsp_range=rsp_t_range)

            percentile = get_percentile_value(rsp_counter=counter, rsp_time_list=rsp_list)
            percentile_rages_dict[str(rsp_time_ranges[idx])] = percentile
        write_rsp_time_percentile_ranges(percentile_rages_dict, file_name)


@events.request.add_listener
def hook_request_success(request_type, name, response_time, response_length, response, **kw):
    stat_file.write(str(response) + ";" + request_type + ";" + name + ";" + str(response_time) + ";" + str(
        response_length) + "\n")


@events.quitting.add_listener
def hook_quitting(environment, **kw):
    stat_file.close()
