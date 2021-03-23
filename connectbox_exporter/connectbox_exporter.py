import json
import logging
import threading
import time
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from typing import Dict

import click
import compal
from lxml.etree import XMLSyntaxError
from prometheus_client import CollectorRegistry, MetricsHandler
from prometheus_client.metrics_core import GaugeMetricFamily
from requests import Timeout

from connectbox_exporter.config import (
    load_config,
    IP_ADDRESS,
    PASSWORD,
    EXPORTER,
    PORT,
    TIMEOUT_SECONDS,
    EXTRACTORS,
)
from connectbox_exporter.logger import get_logger, VerboseLogger
from connectbox_exporter.xml2metric import get_metrics_extractor


# Taken 1:1 from prometheus-client==0.7.1, see https://github.com/prometheus/client_python/blob/3cb4c9247f3f08dfbe650b6bdf1f53aa5f6683c1/prometheus_client/exposition.py
class _ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    """Thread per request HTTP server."""

    # Make worker threads "fire and forget". Beginning with Python 3.7 this
    # prevents a memory leak because ``ThreadingMixIn`` starts to gather all
    # non-daemon threads in a list in order to join on them at server close.
    # Enabling daemon threads virtually makes ``_ThreadingSimpleServer`` the
    # same as Python 3.7's ``ThreadingHTTPServer``.
    daemon_threads = True


class ConnectBoxCollector(object):
    def __init__(
        self,
        logger: VerboseLogger,
        ip_address: str,
        password: str,
        exporter_config: Dict,
    ):
        self.logger = logger
        self.ip_address = ip_address
        self.password = password
        self.timeout = exporter_config[TIMEOUT_SECONDS]

        extractors = exporter_config[EXTRACTORS]
        self.metric_extractors = [get_metrics_extractor(e, logger) for e in extractors]

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
                raw_xmls = {}
                try:
                    pre_scrape_time = time.time()

                    # obtain all raw XML responses for an extractor, then extract metrics
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
                except (XMLSyntaxError, AttributeError) as e:
                    # in case of a less serious error, log and continue scraping the next extractor
                    jsonized = json.dumps(raw_xmls)
                    message = f"Failed to extract '{extractor.name}'. Please open an issue on Github and include the following:\n{repr(e)}\n{jsonized}"
                    self.logger.error(message)
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
            exporter_config=config[EXPORTER],
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
