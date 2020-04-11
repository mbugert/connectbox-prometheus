from pathlib import Path
import deepmerge
from typing import Union, Dict

from ruamel.yaml import YAML

IP_ADDRESS = "ip_address"
PASSWORD = "password"
EXPORTER = "exporter"
PORT = "port"
TIMEOUT_SECONDS = "timeout_seconds"

# pick default timeout one second less than the default prometheus timeout of 10s
DEFAULT_CONFIG = {EXPORTER: {PORT: 9705, TIMEOUT_SECONDS: 9}}


def load_config(config_file: Union[str, Path]) -> Dict:
    """
    Loads and validates YAML config for this exporter and fills in default values
    :param config_file:
    :return: config as dictionary
    """
    yaml = YAML()
    with open(config_file) as f:
        config = yaml.load(f)

    # merge with defaults
    config = deepmerge.always_merger.merge(DEFAULT_CONFIG, config)

    for param in [IP_ADDRESS, PASSWORD]:
        if not param in config:
            raise ValueError(
                f"'{param}' is a mandatory config parameter, but it is missing in the YAML configuration file. Please see README.md for an example."
            )
    if config[EXPORTER][TIMEOUT_SECONDS] <= 0:
        raise ValueError(f"'{TIMEOUT_SECONDS} must be positive.")
    if config[EXPORTER][PORT] < 0 or config[EXPORTER][PORT] > 65535:
        raise ValueError(f"Invalid exporter port.")

    return config
