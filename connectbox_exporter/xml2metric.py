import re
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable, Set, Dict

from compal.functions import GetFunction as GET
from lxml import etree
from prometheus_client import Metric
from prometheus_client.metrics_core import (
    InfoMetricFamily,
    CounterMetricFamily,
    GaugeMetricFamily,
    StateSetMetricFamily,
)


class XmlMetricsExtractor:

    PROJECT_ROOT = Path(__file__).parent.parent
    SCHEMA_ROOT = PROJECT_ROOT / "resources" / "schema"

    def __init__(self, name: str, functions: Set[int]):
        self._name = name

        # create one parser per function, use an XML schema if available
        self._parsers = {}
        for fun in functions:
            path = XmlMetricsExtractor.SCHEMA_ROOT / f"{fun}.xsd"
            if path.exists():
                schema = etree.XMLSchema(file=str(path))
            else:
                schema = None
            parser = etree.XMLParser(schema=schema)
            self._parsers[fun] = parser

    @property
    def name(self):
        """
        Descriptive name for this extractor, to be used in metric labels
        :return:
        """
        return self._name

    @property
    def functions(self) -> Iterable[int]:
        """
        Connect Box getter.xml function(s) this metrics extractor is working on
        :return:
        """
        return self._parsers.keys()

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        """
        Returns metrics given raw XML responses corresponding to the functions returned in the `functions` property.
        :param raw_xmls:
        :return: metrics iterable
        :raises: lxml.etree.XMLSyntaxError in case a raw XML does not match the expected schema
        """
        raise NotImplementedError


class DownstreamStatusExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(DownstreamStatusExtractor, self).__init__(
            "downstream", {GET.DOWNSTREAM_TABLE, GET.SIGNAL_TABLE}
        )

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 2

        # DOWNSTREAM_TABLE gives us frequency, power level, SNR and RxMER per channel
        root = etree.fromstring(
            raw_xmls[GET.DOWNSTREAM_TABLE], parser=self._parsers[GET.DOWNSTREAM_TABLE]
        )

        CHANNEL_ID = "channel_id"
        ds_frequency = GaugeMetricFamily(
            "connectbox_downstream_frequency",
            "Downstream channel frequency",
            unit="hz",
            labels=[CHANNEL_ID],
        )
        ds_power_level = GaugeMetricFamily(
            "connectbox_downstream_power_level",
            "Downstream channel power level",
            unit="dbmv",
            labels=[CHANNEL_ID],
        )
        ds_snr = GaugeMetricFamily(
            "connectbox_downstream_snr",
            "Downstream channel signal-to-noise ratio (SNR)",
            unit="db",
            labels=[CHANNEL_ID],
        )
        ds_rxmer = GaugeMetricFamily(
            "connectbox_downstream_rxmer",
            "Downstream channel receive modulation error ratio (RxMER)",
            unit="db",
            labels=[CHANNEL_ID],
        )
        for channel in root.findall("downstream"):
            channel_id = channel.find("chid").text
            frequency = int(channel.find("freq").text)
            power_level = int(channel.find("pow").text)
            snr = int(channel.find("snr").text)
            rxmer = float(channel.find("RxMER").text)

            labels = [channel_id.zfill(2)]
            ds_frequency.add_metric(labels, frequency)
            ds_power_level.add_metric(labels, power_level)
            ds_snr.add_metric(labels, snr)
            ds_rxmer.add_metric(labels, rxmer)
        yield from [ds_frequency, ds_power_level, ds_snr, ds_rxmer]

        # SIGNAL_TABLE gives us unerrored, corrected and uncorrectable errors per channel
        root = etree.fromstring(
            raw_xmls[GET.SIGNAL_TABLE], parser=self._parsers[GET.SIGNAL_TABLE]
        )

        ds_unerrored_codewords = CounterMetricFamily(
            "connectbox_downstream_codewords_unerrored",
            "Unerrored downstream codewords",
            labels=[CHANNEL_ID],
        )
        ds_correctable_codewords = CounterMetricFamily(
            "connectbox_downstream_codewords_corrected",
            "Corrected downstream codewords",
            labels=[CHANNEL_ID],
        )
        ds_uncorrectable_codewords = CounterMetricFamily(
            "connectbox_downstream_codewords_uncorrectable",
            "Uncorrectable downstream codewords",
            labels=[CHANNEL_ID],
        )
        for channel in root.findall("signal"):
            channel_id = channel.find("dsid").text
            unerrored = int(channel.find("unerrored").text)
            correctable = int(channel.find("correctable").text)
            uncorrectable = int(channel.find("uncorrectable").text)

            labels = [channel_id.zfill(2)]
            ds_unerrored_codewords.add_metric(labels, unerrored)
            ds_correctable_codewords.add_metric(labels, correctable)
            ds_uncorrectable_codewords.add_metric(labels, uncorrectable)
        yield from [
            ds_unerrored_codewords,
            ds_correctable_codewords,
            ds_uncorrectable_codewords,
        ]


class UpstreamStatusExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(UpstreamStatusExtractor, self).__init__("upstream", {GET.UPSTREAM_TABLE})

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1

        CHANNEL_ID = "channel_id"
        TIMEOUT_TYPE = "timeout_type"

        us_frequency = GaugeMetricFamily(
            "connectbox_upstream_frequency",
            "Upstream channel frequency",
            unit="hz",
            labels=[CHANNEL_ID],
        )
        us_power_level = GaugeMetricFamily(
            "connectbox_upstream_power_level",
            "Upstream channel power level",
            unit="dbmv",
            labels=[CHANNEL_ID],
        )
        us_symbol_rate = GaugeMetricFamily(
            "connectbox_upstream_symbol_rate",
            "Upstream channel symbol rate",
            unit="ksps",
            labels=[CHANNEL_ID],
        )
        us_timeouts = CounterMetricFamily(
            "connectbox_upstream_timeouts",
            "Upstream channel timeout occurrences",
            labels=[CHANNEL_ID, TIMEOUT_TYPE],
        )
        root = etree.fromstring(
            raw_xmls[GET.UPSTREAM_TABLE], parser=self._parsers[GET.UPSTREAM_TABLE]
        )
        for channel in root.findall("upstream"):
            channel_id = channel.find("usid").text

            frequency = int(channel.find("freq").text)
            power_level = float(channel.find("power").text)
            symbol_rate = float(channel.find("srate").text)
            t1_timeouts = int(channel.find("t1Timeouts").text)
            t2_timeouts = int(channel.find("t2Timeouts").text)
            t3_timeouts = int(channel.find("t3Timeouts").text)
            t4_timeouts = int(channel.find("t4Timeouts").text)

            labels = [channel_id.zfill(2)]
            us_frequency.add_metric(labels, frequency)
            us_power_level.add_metric(labels, power_level)
            us_symbol_rate.add_metric(labels, symbol_rate)
            us_timeouts.add_metric(labels + ["T1"], t1_timeouts)
            us_timeouts.add_metric(labels + ["T2"], t2_timeouts)
            us_timeouts.add_metric(labels + ["T3"], t3_timeouts)
            us_timeouts.add_metric(labels + ["T4"], t4_timeouts)
        yield from [us_frequency, us_power_level, us_symbol_rate, us_timeouts]


class LanUserExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(LanUserExtractor, self).__init__("lan_users", {GET.LANUSERTABLE})

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1

        root = etree.fromstring(
            raw_xmls[GET.LANUSERTABLE], parser=self._parsers[GET.LANUSERTABLE]
        )

        # LAN and Wi-Fi clients have the same XML format so we can reuse the code to extract their values
        def extract_client(client, target_metric: GaugeMetricFamily):
            mac_address = client.find("MACAddr").text

            # depending on the firmware, both IPv4/IPv6 addresses or only one of both are reported
            ipv4_address_elmt = client.find("IPv4Addr")
            ipv4_address = (
                ipv4_address_elmt.text if ipv4_address_elmt is not None else ""
            )
            ipv6_address_elmt = client.find("IPv6Addr")
            ipv6_address = (
                ipv6_address_elmt.text if ipv6_address_elmt is not None else ""
            )

            hostname = client.find("hostname").text
            speed = int(client.find("speed").text)
            target_metric.add_metric(
                [mac_address, ipv4_address, ipv6_address, hostname], speed
            )

        label_names = ["mac_address", "ipv4_address", "ipv6_address", "hostname"]

        # set up ethernet user speed metric
        ethernet_user_speed = GaugeMetricFamily(
            "connectbox_ethernet_client_speed",
            "Ethernet client network speed",
            labels=label_names,
            unit="mbit",
        )
        for client in root.find("Ethernet").findall("clientinfo"):
            extract_client(client, ethernet_user_speed)
        yield ethernet_user_speed

        # set up Wi-Fi user speed metric
        wifi_user_speed = GaugeMetricFamily(
            "connectbox_wifi_client_speed",
            "Wi-Fi client network speed",
            labels=label_names,
            unit="mbit",
        )
        for client in root.find("WIFI").findall("clientinfo"):
            extract_client(client, wifi_user_speed)
        yield wifi_user_speed


class TemperatureExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(TemperatureExtractor, self).__init__("temperature", {GET.CMSTATE})

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1

        root = etree.fromstring(
            raw_xmls[GET.CMSTATE], parser=self._parsers[GET.CMSTATE]
        )

        fahrenheit_to_celsius = lambda f: (f - 32) * 5.0 / 9
        tuner_temperature = fahrenheit_to_celsius(
            float(root.find("TunnerTemperature").text)
        )
        temperature = fahrenheit_to_celsius(float(root.find("Temperature").text))

        yield GaugeMetricFamily(
            "connectbox_tuner_temperature",
            "Tuner temperature",
            unit="celsius",
            value=tuner_temperature,
        )
        yield GaugeMetricFamily(
            "connectbox_temperature", "Temperature", unit="celsius", value=temperature,
        )


class ProvisioningStatus(Enum):
    ONLINE = "Online"
    PARTIAL_SERVICE_US = "Partial Service (US only)"
    PARTIAL_SERVICE_DS = "Partial Service (DS only)"
    PARTIAL_SERVICE_USDS = "Partial Service (US+DS)"


class DeviceStatusExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(DeviceStatusExtractor, self).__init__(
            "device_status", {GET.GLOBALSETTINGS, GET.CM_SYSTEM_INFO, GET.CMSTATUS}
        )

    def extract(self, raw_xmls: Dict[int, bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 3

        # parse GlobalSettings
        root = etree.fromstring(
            raw_xmls[GET.GLOBALSETTINGS], parser=self._parsers[GET.GLOBALSETTINGS]
        )
        firmware_version = root.find("SwVersion").text
        cm_provision_mode = root.find("CmProvisionMode").text
        gw_provision_mode = root.find("GwProvisionMode").text
        operator_id = root.find("OperatorId").text

        # parse cm_system_info
        root = etree.fromstring(
            raw_xmls[GET.CM_SYSTEM_INFO], parser=self._parsers[GET.CM_SYSTEM_INFO]
        )
        docsis_mode = root.find("cm_docsis_mode").text
        hardware_version = root.find("cm_hardware_version").text
        uptime_as_str = root.find("cm_system_uptime").text

        # parse cmstatus
        root = etree.fromstring(
            raw_xmls[GET.CMSTATUS], parser=self._parsers[GET.CMSTATUS]
        )
        cable_modem_status = root.find("cm_comment").text
        provisioning_status = root.find("provisioning_st").text

        yield InfoMetricFamily(
            "connectbox_device",
            "Assorted device information",
            value={
                "hardware_version": hardware_version,
                "firmware_version": firmware_version,
                "docsis_mode": docsis_mode,
                "cm_provision_mode": cm_provision_mode,
                "gw_provision_mode": gw_provision_mode,
                "cable_modem_status": cable_modem_status,
                "operator_id": operator_id,
            },
        )

        # return an enum-style metric for the provisioning status
        try:
            enum_provisioning_status = ProvisioningStatus(provisioning_status)
        except:
            raise ValueError(
                f"Unknown provisioning status '{provisioning_status}'. Please open an issue on Github."
            )
        yield StateSetMetricFamily(
            "connectbox_provisioning_status",
            "Provisioning status description",
            value={
                state.value: state == enum_provisioning_status
                for state in ProvisioningStatus
            },
        )

        # uptime is reported in a format like "36day(s)15h:24m:58s" which needs parsing
        uptime_pattern = r"(\d+)day\(s\)(\d+)h:(\d+)m:(\d+)s"
        m = re.fullmatch(uptime_pattern, uptime_as_str)
        if m is None:
            raise ValueError(
                f"Unexpected duration format '{uptime_as_str}', please open an issue on github."
            )
        uptime_timedelta = timedelta(
            days=int(m[1]), hours=int(m[2]), minutes=int(m[3]), seconds=int(m[4])
        )
        uptime_seconds = uptime_timedelta.total_seconds()

        yield GaugeMetricFamily(
            "connectbox_uptime",
            "Device uptime in seconds",
            unit="seconds",
            value=uptime_seconds,
        )
