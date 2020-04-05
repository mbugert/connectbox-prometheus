# Connectbox Prometheus
[![PyPI - License](https://img.shields.io/pypi/l/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![PyPI](https://img.shields.io/pypi/v/connectbox-prometheus.svg)](https://pypi.org/project/connectbox-prometheus/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A [Prometheus](https://prometheus.io/) exporter for the modem connection status of UPC Connect Boxes (used by Unitymedia in Germany, Irish Virgin Media, Ziggo in the Netherlands, and probably several others).

Makes thorough use of [python-connect-box](https://github.com/fabaff/python-connect-box) by [@fabaff](https://github.com/fabaff) (thanks!).

## Installation
You need python3.6 or higher. On your Prometheus server host, install the exporter via

`pip3 install connectbox-prometheus`

## Usage
This exporter queries exactly one Connect Box as a remote target.
To get started, modify `config.yml` from this repository or create your own with the following content:
```yaml
# Connect Box IP address
ip_address: 192.168.0.1

# Connect Box web interface password
password: WhatEverYourPasswordIs

# port on which this exporter exposes metrics
exporter_port: 9705
```

Then run `connectbox_exporter path/to/your/config.yml`

## Prometheus Configuration
Add the following to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'connectbox'
    static_configs:
      - targets:
        - localhost:9705
```

## Exported Metrics
| Metric name                                  | Description                                              |
|:---------------------------------------------|:---------------------------------------------------------|
| `connectbox_up`                              | Connect Box reachable yes/no                             |
| `connectbox_num_devices`                     | Number of connected devices                              |
| `connectbox_downstream_frequency_hz`         | Downstream channel frequency                             |
| `connectbox_downstream_power_level_dbmv`     | Downstream channel power level in dBmV                   |
| `connectbox_downstream_modulation_qam`       | Downstream channel modulation                            |
| `connectbox_downstream_signal_to_noise_db`   | Downstream channel signal-to-noise in dB                 |
| `connectbox_downstream_errors_pre_rs_total`  | Downstream channel errors before Reed-Solomon correction |
| `connectbox_downstream_errors_post_rs_total` | Downstream channel errors after Reed-Solomon correction  |
| `connectbox_downstream_qam_locked`           | Downstream channel QAM lock status                       |
| `connectbox_downstream_freq_locked`          | Downstream channel frequency lock status                 |
| `connectbox_downstream_mpeg_locked`          | Downstream channel MPEG lock status                      |
| `connectbox_upstream_frequency_hz`           | Upstream channel frequency                               |
| `connectbox_upstream_power_level_dbmv`       | Upstream channel power level in dBmV                     |
| `connectbox_upstream_symbol_rate_ksps`       | Upstream channel symbol rate                             |
| `connectbox_upstream_modulation_qam`         | Upstream channel modulation                              |
| `connectbox_upstream_timeouts_total`         | Upstream channel timeouts                                |