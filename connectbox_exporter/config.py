from pathlib import Path
from typing import Union, Dict

from deepmerge import Merger
from ruamel.yaml import YAML

from connectbox_exporter.xml2metric import (
    DEVICE_STATUS,
    DOWNSTREAM,
    UPSTREAM,
    LAN_USERS,
    TEMPERATURE,
)

IP_ADDRESS = "ip_address"
PASSWORD = "password"
EXPORTER = "exporter"
PORT = "port"
TIMEOUT_SECONDS = "timeout_seconds"
EXTRACTORS = "metrics"

# pick default timeout one second less than the default prometheus timeout of 10s
DEFAULT_CONFIG = {
    EXPORTER: {
        PORT: 9705,
        TIMEOUT_SECONDS: 9,
        EXTRACTORS: {DEVICE_STATUS, DOWNSTREAM, UPSTREAM, LAN_USERS, TEMPERATURE},
    }
}


def load_config(config_file: Union[str, Path]) -> Dict:
    """
    Loads and validates YAML config for this exporter and fills in default values
    :param config_file:
    :return: config as dictionary
    """
    yaml = YAML()
    with open(config_file) as f:
        config = yaml.load(f)

    # merge with default config: use 'override' for lists to let users replace extractor setting entirely
    merger = Merger([(list, "override"), (dict, "merge")], ["override"], ["override"])
    config = merger.merge(DEFAULT_CONFIG, config)

    for param in [IP_ADDRESS, PASSWORD]:
        if not param in config:
            raise ValueError(
                f"'{param}' is a mandatory config parameter, but it is missing in the YAML configuration file. Please see README.md for an example."
            )
    if config[EXPORTER][TIMEOUT_SECONDS] <= 0:
        raise ValueError(f"'{TIMEOUT_SECONDS} must be positive.")
    if config[EXPORTER][PORT] < 0 or config[EXPORTER][PORT] > 65535:
        raise ValueError(f"Invalid exporter port.")

    if not config[EXPORTER][EXTRACTORS]:
        raise ValueError(
            "The config file needs to specify at least one family of metrics."
        )
    config[EXPORTER][EXTRACTORS] = sorted(set(config[EXPORTER][EXTRACTORS]))

    return config
