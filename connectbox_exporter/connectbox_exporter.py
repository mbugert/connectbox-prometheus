import logging
import sys
import threading
import time

import click
from compal import Compal
from prometheus_client import CollectorRegistry, MetricsHandler
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import _ThreadingSimpleServer
from requests import Timeout

from connectbox_exporter.config import (
    load_config,
    IP_ADDRESS,
    PASSWORD,
    EXPORTER,
    PORT,
    TIMEOUT_SECONDS,
)
from connectbox_exporter.xml2metric import (
    CmStateExtractor,
    LanUserExtractor,
    UpstreamStatusExtractor,
    DownstreamStatusExtractor,
    DeviceStatusExtractor,
)


class ConnectBoxCollector(object):
    def __init__(
        self, logger: logging.Logger, ip_address: str, password: str, timeout: float
    ):
        self.logger = logger
        self.ip_address = ip_address
        self.password = password
        self.timeout = timeout
        self.metric_extractors = [
            DeviceStatusExtractor(),
            CmStateExtractor(),
            LanUserExtractor(),
            DownstreamStatusExtractor(),
            UpstreamStatusExtractor(),
        ]

    def collect(self):
        successful_scrape = True
        pre_scrape_time = time.time()

        # attempt login
        try:
            self.logger.debug("Logging in at " + self.ip_address)
            connectbox = Compal(
                self.ip_address, key=self.password, timeout=self.timeout
            )
            connectbox.login()
        except (ConnectionError, Timeout, ValueError) as e:
            self.logger.error(e)
            connectbox = None
            successful_scrape = False

        # skip extracting further metrics if login failed
        if connectbox is not None:
            try:
                for extractor in self.metric_extractors:
                    contents = []
                    for fun in extractor.functions:
                        self.logger.debug(f"Querying fun=" + str(fun) + "...")
                        contents.append(connectbox.xml_getter(fun, {}).content)
                    yield from extractor.extract(contents)
            except Exception as e:
                # bail out on any error
                self.logger.error(e)
                successful_scrape = False
            finally:
                # attempt logout in case of errors
                try:
                    self.logger.debug("Logging out.")
                    connectbox.logout()
                except Exception as e:
                    self.logger.error(e)
                    successful_scrape = False

        post_scrape_time = time.time()
        if successful_scrape:
            self.logger.debug("Scrape successful.")
            yield GaugeMetricFamily(
                "connectbox_scrape_duration",
                documentation="Connect Box exporter scrape duration",
                unit="seconds",
                value=post_scrape_time - pre_scrape_time,
            )

        yield GaugeMetricFamily(
            "connectbox_scrape_success",
            documentation="Connect Box exporter scrape success",
            value=int(successful_scrape),
        )


@click.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option("-v", "--verbose", help="Print more log messages", is_flag=True)
def main(config_file, verbose):
    """
    Launch the exporter using a YAML config file.
    """
    # logging setup
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("connectbox_exporter")
    logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # load user and merge with defaults
    config = load_config(config_file)
    exporter_config = config[EXPORTER]

    # fire up collector
    reg = CollectorRegistry()
    reg.register(
        ConnectBoxCollector(
            logger,
            ip_address=config[IP_ADDRESS],
            password=config[PASSWORD],
            timeout=exporter_config[TIMEOUT_SECONDS],
        )
    )

    # start http server
    CustomMetricsHandler = MetricsHandler.factory(reg)
    httpd = _ThreadingSimpleServer(("", exporter_config[PORT]), CustomMetricsHandler)
    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd_thread.start()

    logger.info(
        f"Exporter running at http://localhost:{exporter_config[PORT]}, querying {config[IP_ADDRESS]}"
    )

    # wait indefinitely
    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        httpd.shutdown()
        httpd_thread.join()
