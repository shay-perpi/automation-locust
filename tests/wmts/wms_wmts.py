from locust import task, FastHttpUser, tag, HttpUser, events, between
from locust_plugins.csvreader import CSVReader

from config.config import config_obj, WmtsConfig
from utils.percentile_calculation import calculate_times, generate_name

bbox = config_obj['wms'].BBOX
delta_x = bbox[3] - bbox[1]
delta_y = bbox[2] - bbox[0]
file_name = generate_name(__name__)
stat_file = open(f"{config_obj['wmts'].root_dir}/{file_name}", 'w')

wmts_csv_path = WmtsConfig.WMTS_CSV_PATH
wmts_csv_path_up_scale = WmtsConfig.WMTS_CSV_PATH_UPSCALE

ssn_reader = CSVReader(wmts_csv_path)
upscale_reader = CSVReader(wmts_csv_path_up_scale)

wmstileT = lambda l: f"api/raster/v1/service?LAYERS={config_obj['wms'].LAYER_TYPE}&FORMAT=image%2Fpng&SRS=EPSG%3A4326" \
                     f"&EXCEPTIONS=application%252Fvnd.ogc.se_inimage" \
                     f"&TRANSPARENT=TRUE&service=wms&VERSION=1.1.1&REQUEST=GetMap&STYLES=" \
                     f"&BBOX={l[0]}%2C{l[1]}%2C{l[2]}%2C{l[3]}&WIDTH={config_obj['wms'].WIDTH}" \
                     f"&HEIGHT={config_obj['wms'].HEIGHT}&token={config_obj['wms'].TOK}"

wmstileNoToken = lambda \
        l: f"api/raster/v1/service?LAYERS={config_obj['wms'].LAYER_TYPE}&FORMAT=image%2Fpng&SRS=EPSG%3A4326" \
           f"&EXCEPTIONS=application%252Fvnd.ogc.se_inimage" \
           f"&TRANSPARENT=TRUE&service=wms&VERSION=1.1.1&REQUEST=GetMap&STYLES=" \
           f"&BBOX={l[0]}%2C{l[1]}%2C{l[2]}%2C{l[3]}&WIDTH={config_obj['wms'].WIDTH}" \
           f"&HEIGHT={config_obj['wms'].HEIGHT}"


class User(FastHttpUser):
    host = config_obj['wms'].HOST
    between(1, 1)

    @task(1)
    @tag('regular')
    def zoom_level_up(self):
        bbox[0] += 0.00005
        bbox[1] += 0.00005
        bbox[2] += 0.00005
        bbox[3] += 0.00005
        if config_obj['wms'].TOKEN is True:
            resp = self.client.get(wmstileT(bbox))
        else:
            resp = self.client.get(wmstileNoToken(bbox))

    @task(1)
    @tag('zoom')
    def zoom_delta(self):
        zoom = bbox
        zoom[2] -= delta_y
        zoom[3] -= delta_x
        if config_obj['wms'].TOKEN is True:
            resp = self.client.get(wmstileT(zoom))
        else:
            resp = self.client.get(wmstileNoToken(zoom))

    @task(1)  # #WMTS - “HTTP_REQUEST_TYPE /SUB_DOMAIN/PROTOCOL/LAYER/TILE_MATRIX_SET/Z/X/Y.IMAGE_FORMAT HTTP_VERSION“
    @tag("wmts-loading")
    def index(self):
        if config_obj['wmts'].WMTS_FLAG:
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

    @task(1)
    @tag("Wmts-Upscale")
    def up_scale(self):
        points = next(upscale_reader)
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

    # host = 'https://mapproxy-raster-qa-route-raster-qa.apps.j1lk3njp.eastus.aroapp.io/' __name__ #'
    def on_stop(self):
        calculate_times(file_name, __name__)


@events.request.add_listener
def hook_request_success(request_type, name, response_time, response_length, **kwargs):
    stat_file.write(f"{request_type};{name} ; {response_time};{response_length}  \n")


@events.quitting.add_listener
def hook_quitting(environment, **kw):
    stat_file.close()
