import asyncio
import logging
import sys
from typing import Tuple, Optional

import aiohttp
import click
from connect_box import ConnectBox
from connect_box.exceptions import (
    ConnectBoxConnectionError,
    ConnectBoxLoginError,
    ConnectBoxNoDataAvailable,
)
from prometheus_client import start_http_server, CollectorRegistry
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily


class ConnectBoxCollector(object):
    def __init__(self, logger: logging.Logger, host: str, password: str):
        self.logger = logger
        self.host = host
        self.password = password

    def collect(self):
        PREFIX = "connectbox"
        CHANNEL_ID = "channel_id"
        TIMEOUT_TYPE = "timeout_type"

        self.logger.debug("Retrieving measurements from Connect Box...")
        retrieved = self._retrieve_values()

        connectbox_is_up = retrieved is not None
        yield GaugeMetricFamily(
            PREFIX + "_up",
            documentation="Connect Box reachable yes/no",
            value=int(connectbox_is_up),
        )

        if connectbox_is_up:
            ds_channels, us_channels, devices = retrieved
            self.logger.debug("Success.")

            yield GaugeMetricFamily(
                PREFIX + "_num_devices",
                "Number of connected devices",
                value=len(devices),
            )

            # collect downstream metrics
            ds_frequency = GaugeMetricFamily(
                PREFIX + "_downstream_frequency",
                "Downstream channel frequency",
                unit="hz",
                labels=[CHANNEL_ID],
            )
            ds_power_level = GaugeMetricFamily(
                PREFIX + "_downstream_power_level",
                "Downstream channel power level",
                unit="dbmv",
                labels=[CHANNEL_ID],
            )
            ds_modulation = GaugeMetricFamily(
                PREFIX + "_downstream_modulation",
                "Downstream channel modulation",
                unit="qam",
                labels=[CHANNEL_ID],
            )
            ds_snr = GaugeMetricFamily(
                PREFIX + "_downstream_signal_to_noise",
                "Downstream channel signal-to-noise",
                unit="db",
                labels=[CHANNEL_ID],
            )
            ds_pre_rs = CounterMetricFamily(
                PREFIX + "_downstream_errors_pre_rs",
                "Downstream channel errors before Reed-Solomon correction",
                labels=[CHANNEL_ID],
            )
            ds_post_rs = CounterMetricFamily(
                PREFIX + "_downstream_errors_post_rs",
                "Downstream channel errors after Reed-Solomon correction",
                labels=[CHANNEL_ID],
            )
            ds_qam_locked = GaugeMetricFamily(
                PREFIX + "_downstream_qam_locked",
                "Downstream channel QAM lock status",
                labels=[CHANNEL_ID],
            )
            ds_freq_locked = GaugeMetricFamily(
                PREFIX + "_downstream_freq_locked",
                "Downstream channel frequency lock status",
                labels=[CHANNEL_ID],
            )
            ds_mpeg_locked = GaugeMetricFamily(
                PREFIX + "_downstream_mpeg_locked",
                "Downstream channel MPEG lock status",
                labels=[CHANNEL_ID],
            )
            for ds_ch in ds_channels:
                modulation = int(ds_ch.modulation[:-3])  # trim the trailing "qam"
                labels = [ds_ch.id]

                ds_frequency.add_metric(labels, ds_ch.frequency)
                ds_power_level.add_metric(labels, ds_ch.powerLevel)
                ds_modulation.add_metric(labels, modulation)
                ds_snr.add_metric(labels, ds_ch.snr)
                ds_pre_rs.add_metric(labels, ds_ch.preRs)
                ds_post_rs.add_metric(labels, ds_ch.postRs)
                ds_qam_locked.add_metric(labels, int(ds_ch.qamLocked))
                ds_freq_locked.add_metric(labels, int(ds_ch.fecLocked))
                ds_mpeg_locked.add_metric(labels, int(ds_ch.mpegLocked))
            for metric in [
                ds_frequency,
                ds_power_level,
                ds_modulation,
                ds_snr,
                ds_pre_rs,
                ds_post_rs,
                ds_qam_locked,
                ds_freq_locked,
                ds_mpeg_locked,
            ]:
                yield metric

            # collect upstream metrics
            us_frequency = GaugeMetricFamily(
                PREFIX + "_upstream_frequency",
                "Upstream channel frequency",
                unit="hz",
                labels=[CHANNEL_ID],
            )
            us_power_level = GaugeMetricFamily(
                PREFIX + "_upstream_power_level",
                "Upstream channel power level",
                unit="dbmv",
                labels=[CHANNEL_ID],
            )
            us_symbol_rate = GaugeMetricFamily(
                PREFIX + "_upstream_symbol_rate",
                "Upstream channel symbol rate",
                unit="ksps",
                labels=[CHANNEL_ID],
            )
            us_modulation = GaugeMetricFamily(
                PREFIX + "_upstream_modulation",
                "Upstream channel modulation",
                unit="qam",
                labels=[CHANNEL_ID],
            )
            us_timeouts = CounterMetricFamily(
                PREFIX + "_upstream_timeouts",
                "Upstream channel timeout occurrences",
                labels=[CHANNEL_ID, TIMEOUT_TYPE],
            )
            for us_ch in us_channels:
                modulation = int(us_ch.modulation[:-3])  # trim the trailing "qam"
                labels = [us_ch.id]

                us_frequency.add_metric(labels, us_ch.frequency)
                us_power_level.add_metric(labels, us_ch.powerLevel)
                us_symbol_rate.add_metric(labels, us_ch.symbolRate)
                us_modulation.add_metric(labels, modulation)
                us_timeouts.add_metric(labels + ["T1"], us_ch.t1Timeouts)
                us_timeouts.add_metric(labels + ["T2"], us_ch.t2Timeouts)
                us_timeouts.add_metric(labels + ["T3"], us_ch.t3Timeouts)
                us_timeouts.add_metric(labels + ["T4"], us_ch.t4Timeouts)
            for metric in [
                us_frequency,
                us_power_level,
                us_symbol_rate,
                us_modulation,
                us_timeouts,
            ]:
                yield metric

    def _retrieve_values(self) -> Optional[Tuple]:
        async def retrieve():
            async with aiohttp.ClientSession() as session:
                client = ConnectBox(session, self.password, host=self.host)
                try:
                    await client.async_get_downstream()
                    await client.async_get_upstream()
                    await client.async_get_devices()
                    await client.async_close_session()
                    return client.ds_channels, client.us_channels, client.devices
                except ConnectBoxLoginError:
                    self.logger.warning(
                        "Login error: Incorrect password or concurrent login session."
                    )
                    return None
                except (ConnectBoxConnectionError, ConnectBoxNoDataAvailable):
                    self.logger.warning("Connection error or not data available.")
                    return None

        return asyncio.run(retrieve())


@click.command()
@click.option(
    "--port",
    default=9705,
    help="Port where this exporter serves metrics",
    type=int,
    show_default=True,
)
@click.option("--host", default="192.168.0.1", help="Connect Box IP address", type=str)
@click.option(
    "--pw", help="Connect Box web interface password", required=True, type=str
)
@click.option("-v", "--verbose", help="Print more log messages", is_flag=True)
def main(port, host, pw, verbose):
    log_level = logging.DEBUG if verbose else logging.INFO

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # log to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # fire up collector
    reg = CollectorRegistry()
    reg.register(ConnectBoxCollector(logger, host=host, password=pw))
    start_http_server(port, registry=reg)

    logger.info("Exporter started.")

    # stall the main thread indefinitely
    while True:
        input()
