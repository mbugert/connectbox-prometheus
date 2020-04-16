from enum import Enum
from typing import Iterable, Union, List
import re
from datetime import timedelta

# use lxml if available (should be present as a dependency of the compal library)
from prometheus_client.metrics_core import (
    InfoMetricFamily,
    CounterMetricFamily,
    GaugeMetricFamily,
    StateSetMetricFamily,
)

try:
    from lxml import etree
except ImportError:
    import elementtree.ElementTree as etree

from prometheus_client import Metric
from compal.functions import GetFunction as GET


class XmlMetricsExtractor:
    def __init__(self, functions: Union[int, List[int]]):
        if type(functions) is list:
            self._functions = functions
        else:
            self._functions = [functions]
        self.parser = etree.XMLParser()

    @property
    def functions(self) -> List[int]:
        """
        Connect Box getter.xml function(s) this metrics extractor is working on
        :return:
        """
        return self._functions

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        """
        Returns metrics given raw XML responses corresponding to the functions returned in the `functions` property.
        :param raw_xmls:
        :return:
        """
        raise NotImplementedError


class DownstreamStatusExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(DownstreamStatusExtractor, self).__init__(
            [GET.DOWNSTREAM_TABLE, GET.SIGNAL_TABLE]
        )

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 2
        downstream_table_xml = raw_xmls[0]
        signal_table_xml = raw_xmls[1]

        # DOWNSTREAM_TABLE gives us frequency, power level, SNR and RxMER per channel
        root = etree.fromstring(downstream_table_xml, parser=self.parser)
        assert root.tag == "downstream_table"

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
        root = etree.fromstring(signal_table_xml, parser=self.parser)
        assert root.tag == "signal_table"

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
        super(UpstreamStatusExtractor, self).__init__(GET.UPSTREAM_TABLE)

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1
        upstream_table_xml = raw_xmls[0]

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
        root = etree.fromstring(upstream_table_xml, parser=self.parser)
        assert root.tag == "upstream_table"
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
        super(LanUserExtractor, self).__init__(GET.LANUSERTABLE)

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1
        lan_user_xml = raw_xmls[0]

        MAC_ADDRESS = "mac_address"
        HOSTNAME = "hostname"
        IPV4_ADDRESS = "ipv4_address"
        IPV6_ADDRESS = "ipv6_address"
        lan_user_speed = GaugeMetricFamily(
            "connectbox_lan_user_speed",
            "LAN user network speed",
            labels=[MAC_ADDRESS, IPV4_ADDRESS, IPV6_ADDRESS, HOSTNAME],
            unit="mbit",
        )
        root = etree.fromstring(lan_user_xml, parser=self.parser)
        assert root.tag == "LanUserTable"

        for client in root.find("Ethernet").findall("clientinfo"):
            mac_address = client.find("MACAddr").text
            ipv4_address = client.find("IPv4Addr").text
            ipv6_address = client.find("IPv6Addr").text
            hostname = client.find("hostname").text
            speed = int(client.find("speed").text)
            lan_user_speed.add_metric(
                [mac_address, ipv4_address, ipv6_address, hostname], speed
            )

        # TODO there could be more things to be reported about wifi devices here

        yield lan_user_speed


class CmStateExtractor(XmlMetricsExtractor):
    def __init__(self):
        super(CmStateExtractor, self).__init__(GET.CMSTATE)

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 1
        cmstate_xml = raw_xmls[0]

        root = etree.fromstring(cmstate_xml, parser=self.parser)
        assert root.tag == "cmstate"

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
            [GET.GLOBALSETTINGS, GET.CM_SYSTEM_INFO, GET.CMSTATUS]
        )

    def extract(self, raw_xmls: List[bytes]) -> Iterable[Metric]:
        assert len(raw_xmls) == 3
        global_settings_xml = raw_xmls[0]
        cm_system_info_xml = raw_xmls[1]
        cm_status_xml = raw_xmls[2]

        # parse GlobalSettings
        root = etree.fromstring(global_settings_xml, parser=self.parser)
        assert root.tag == "GlobalSettings"
        firmware_version = root.find("SwVersion").text
        cm_provision_mode = root.find("CmProvisionMode").text
        gw_provision_mode = root.find("GwProvisionMode").text
        operator_id = root.find("OperatorId").text

        # parse cm_system_info
        root = etree.fromstring(cm_system_info_xml, parser=self.parser)
        assert root.tag == "cm_system_info"
        docsis_mode = root.find("cm_docsis_mode").text
        hardware_version = root.find("cm_hardware_version").text
        uptime_as_str = root.find("cm_system_uptime").text

        # parse cmstatus
        root = etree.fromstring(cm_status_xml, parser=self.parser)
        assert root.tag == "cmstatus"
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
