import logging
import threading
import time
from typing import Dict

import click
import compal
from lxml.etree import XMLSyntaxError
from prometheus_client import CollectorRegistry, MetricsHandler
from prometheus_client.exposition import _ThreadingSimpleServer
from prometheus_client.metrics_core import GaugeMetricFamily
from requests import Timeout

from connectbox_exporter.config import (
    load_config,
    IP_ADDRESS,
    PASSWORD,
    EXPORTER,
    PORT,
    TIMEOUT_SECONDS,
)
from connectbox_exporter.logger import get_logger, VerboseLogger
from connectbox_exporter.xml2metric import (
    TemperatureExtractor,
    LanUserExtractor,
    UpstreamStatusExtractor,
    DownstreamStatusExtractor,
    DeviceStatusExtractor,
)


class ConnectBoxCollector(object):
    def __init__(
        self, logger: VerboseLogger, ip_address: str, password: str, timeout: float
    ):
        self.logger = logger
        self.ip_address = ip_address
        self.password = password
        self.timeout = timeout
        self.metric_extractors = [
            DeviceStatusExtractor(),
            TemperatureExtractor(),
            LanUserExtractor(),
            DownstreamStatusExtractor(),
            UpstreamStatusExtractor(),
        ]

    def collect(self):
        # Collect scrape duration and scrape success for each extractor. Scrape success is initialized with False for
        # all extractors so that we can report a value for each extractor even in cases where we abort midway through
        # because we lost connection to the modem.
        scrape_duration = {}  # type: Dict[str, float]
        scrape_success = {e.name: False for e in self.metric_extractors}

        # attempt login
        login_logout_success = True
        try:
            self.logger.debug("Logging in at " + self.ip_address)
            connectbox = compal.Compal(
                self.ip_address, key=self.password, timeout=self.timeout
            )
            connectbox.login()
        except (ConnectionError, Timeout, ValueError) as e:
            self.logger.error(repr(e))
            connectbox = None
            login_logout_success = False

        # skip extracting further metrics if login failed
        if connectbox is not None:
            for extractor in self.metric_extractors:
                try:
                    pre_scrape_time = time.time()

                    # obtain all raw XML responses for an extractor, then extract metrics
                    raw_xmls = {}
                    for fun in extractor.functions:
                        self.logger.debug(f"Querying fun={fun}...")
                        raw_xml = connectbox.xml_getter(fun, {}).content
                        self.logger.verbose(
                            f"Raw XML response for fun={fun}:\n{raw_xml.decode()}"
                        )
                        raw_xmls[fun] = raw_xml
                    yield from extractor.extract(raw_xmls)
                    post_scrape_time = time.time()

                    scrape_duration[extractor.name] = post_scrape_time - pre_scrape_time
                    scrape_success[extractor.name] = True
                except XMLSyntaxError as e:
                    # in case of a less serious error, log and continue scraping the next extractor
                    self.logger.error(repr(e))
                except (ConnectionError, Timeout) as e:
                    # in case of serious connection issues, abort and do not try the next extractor
                    self.logger.error(repr(e))
                    break

            # attempt logout once done
            try:
                self.logger.debug("Logging out.")
                connectbox.logout()
            except Exception as e:
                self.logger.error(e)
                login_logout_success = False
        scrape_success["login_logout"] = int(login_logout_success)

        # create metrics from previously durations and successes collected
        EXTRACTOR = "extractor"
        scrape_duration_metric = GaugeMetricFamily(
            "connectbox_scrape_duration",
            documentation="Scrape duration by extractor",
            unit="seconds",
            labels=[EXTRACTOR],
        )
        for name, duration in scrape_duration.items():
            scrape_duration_metric.add_metric([name], duration)
        yield scrape_duration_metric

        scrape_success_metric = GaugeMetricFamily(
            "connectbox_up",
            documentation="Connect Box exporter scrape success by extractor",
            labels=[EXTRACTOR],
        )
        for name, success in scrape_success.items():
            scrape_success_metric.add_metric([name], int(success))
        yield scrape_success_metric


@click.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-v",
    "--verbose",
    help="Log more messages. Multiple -v increase verbosity.",
    count=True,
)
def main(config_file, verbose):
    """
    Launch the exporter using a YAML config file.
    """

    # hush the logger from the compal library and use our own custom logger
    compal.LOGGER.setLevel(logging.WARNING)
    logger = get_logger(verbose)

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
