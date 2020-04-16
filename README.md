# Connectbox Prometheus
[![PyPI - License](https://img.shields.io/pypi/l/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![PyPI](https://img.shields.io/pypi/v/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A [Prometheus](https://prometheus.io/) exporter for monitoring Compal CH7465LG cable modems. These are sold under the name "Connect Box" by Unitymedia in Germany, Ziggo in the Netherlands and UPC in Switzerland/Austria/Poland. Or as "Virgin Media Super Hub 3" by Virgin Media.

Makes thorough use of [compal_CH7465LG_py](https://github.com/ties/compal_CH7465LG_py) by [@ties](https://github.com/ties/) (thanks!).

## Installation
On your Prometheus server host:

1. [Create a virtual environment](https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments) using python3.7 or higher
2. Install the exporter via `pip install connectbox-prometheus`

## Usage
This exporter queries exactly one Connect Box as a remote target.
To get started, modify `config.yml` from this repository or start out with the following content:
```yaml
# Connect Box IP address
ip_address: 192.168.0.1

# Connect Box web interface password
password: WhatEverYourPasswordIs
```

Then run `connectbox_exporter path/to/your/config.yml` .

## Prometheus Configuration
Add the following to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'connectbox'
    static_configs:
      - targets:
        - localhost:9705
```
One scrape takes roughly 6 seconds.

## Exported Metrics
| Metric name                                           | Description                                               |
|:------------------------------------------------------|:----------------------------------------------------------|
| `connectbox_device_info`                              | Assorted device information                               |
| `connectbox_uptime_seconds_total`                     | Device uptime in seconds                                  |
| `connectbox_tuner_temperature_celsius`                | Tuner temperature                                         |
| `connectbox_temperature_celsius`                      | Temperature                                               |
| `connectbox_lan_user_speed_mbit`                      | LAN user network speed                                    |
| `connectbox_downstream_frequency_hz`                  | Downstream channel frequency                              |
| `connectbox_downstream_power_level_dbmv`              | Downstream channel power level                            |
| `connectbox_downstream_snr_db`                        | Downstream channel signal-to-noise ratio (SNR)            |
| `connectbox_downstream_rxmer_db`                      | Downstream channel receive modulation error ratio (RxMER) |
| `connectbox_downstream_codewords_unerrored_total`     | Unerrored downstream codewords                            |
| `connectbox_downstream_codewords_corrected_total`     | Corrected downstream codewords                            |
| `connectbox_downstream_codewords_uncorrectable_total` | Uncorrectable downstream codewords                        |
| `connectbox_upstream_frequency_hz`                    | Upstream channel frequency                                |
| `connectbox_upstream_power_level_dbmv`                | Upstream channel power level                              |
| `connectbox_upstream_symbol_rate_ksps`                | Upstream channel symbol rate                              |
| `connectbox_upstream_timeouts_total`                  | Upstream channel timeout occurrences                      |
| `connectbox_scrape_duration_seconds`                  | Connect Box exporter scrape duration                      |
| `connectbox_scrape_success`                           | Connect Box exporter scrape success                       |

## Grafana Dashboard

The above metrics can be monitored nicely in [Grafana](https://github.com/grafana/grafana) using [this dashboard](https://grafana.com/grafana/dashboards/12078/):

![Grafana Dashboard](docs/grafana_dashboard_screenshot.png)

## Contributing / Development
Pull requests are welcome. 😊
In particular, metrics on connected Wifi devices are unchartered territory since I'm not using the Wifi functionality of my device. 

To install development dependencies, run:

`pip install -r requirements/development.txt`