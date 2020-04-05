# Connectbox Prometheus
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A [Prometheus](https://prometheus.io/) exporter for the modem connection status of UPC Connect Boxes (used by Unitymedia in Germany, Irish Virgin Media, Ziggo in the Netherlands, and probably several others).

Makes thorough use of [python-connect-box](https://github.com/fabaff/python-connect-box) by [@fabaff](https://github.com/fabaff) (thanks!).

## Installation
You need python3.6 or higher. Run:

`$ pip3 install connectbox-prometheus`

## Usage
`./connectbox_exporter --pw YOUR_CONNECTBOX_PASSWORD`

To see all options, run `./connectbox_exporter --help`

## Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'connectbox'
    static_configs:
      - targets:
        - 192.168.0.1                 # IP address of your Connect Box
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 127.0.0.1:9705   # The exporter's real hostname:port.
```

## Exported Metrics
| Metric name                                  | Description                                              |
|:---------------------------------------------|:---------------------------------------------------------|
| `connectbox_up`                              | Connect Box reachable yes/no                             |
| `connectbox_num_devices`                     | Number of connected devices                              |
| `connectbox_downstream_frequency_hz`         | Downstream channel frequency                             |
| `connectbox_downstream_power_level_dbmv`     | Downstream channel power level                           |
| `connectbox_downstream_modulation_qam`       | Downstream channel modulation                            |
| `connectbox_downstream_signal_to_noise_db`   | Downstream channel signal-to-noise                       |
| `connectbox_downstream_errors_pre_rs_total`  | Downstream channel errors before Reed-Solomon correction |
| `connectbox_downstream_errors_post_rs_total` | Downstream channel errors after Reed-Solomon correction  |
| `connectbox_downstream_qam_locked`           | Downstream channel QAM lock status                       |
| `connectbox_downstream_freq_locked`          | Downstream channel frequency lock status                 |
| `connectbox_downstream_mpeg_locked`          | Downstream channel MPEG lock status                      |
| `connectbox_upstream_frequency_hz`           | Upstream channel frequency                               |
| `connectbox_upstream_power_level_dbmv`       | Upstream channel power level                             |
| `connectbox_upstream_symbol_rate_ksps`       | Upstream channel symbol rate                             |
| `connectbox_upstream_modulation_qam`         | Upstream channel modulation                              |
| `connectbox_upstream_timeouts_total`         | Upstream channel timeouts                                |