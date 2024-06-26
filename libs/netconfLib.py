import logging

from datetime import datetime

import libs.envLib as envLib
import libs.commsLib as commsLib
import libs.influxLib as influxLib
import libs.fileLib as fileLib
import libs.parseLib as parseLib

env = envLib.read_config_file()
log = logging.getLogger("wifininja.wlcLib")


class Ninja2():

    def __init__(self):

        self.netconf_lastrun = datetime.now()
        self.netconf_firstrun = True
        self.wlc_data = {}
        self.ap_data = {}


init = Ninja2()


def netconf_loop():

    idle_period = datetime.now() - init.netconf_lastrun
    
    if init.netconf_firstrun or idle_period.seconds >= int(env["NETCONF_CYCLE"]):

        init.netconf_firstrun = False
        init.netconf_lastrun = datetime.now()

        get_netconf_interfaces_oper()
        get_netconf_wireless_client_global_oper()
        get_netconf_wireless_client_oper()
       
        if env["SEND_TO_INFLUX"] == "True":
            influxLib.send_to_influx_wlc(env, init.wlc_data)
        if env["SAVE_CSV"] == "True":
            fileLib.send_to_csv_wlc(init.wlc_data)

        get_netconf_wireless_access_point_oper()
        #get_netconf_wireless_ap_cfg() #site/rf tag data is collected from ops, not cfg
        get_netconf_wireless_rrm_oper()

        if env["SEND_TO_INFLUX"] == "True":
            influxLib.send_to_influx_ap(env, init.ap_data)
        if env["SAVE_CSV"] == "True":
            fileLib.send_to_csv_ap(init.ap_data)
        
        log.info(f"Waiting for next NETCONF cycle")


def get_netconf_wireless_client_oper():

    filter = '''
        <client-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-client-oper">
            <dot11-oper-data>
                <ewlc-ms-phy-type/>
            </dot11-oper-data>
        </client-oper-data>
    '''
    old_filter = '''
        <client-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-client-oper">
            <dot11-oper-data>
                <ewlc-ms-phy-type/>
            </dot11-oper-data>
            <dc-info>
                <device-type/>
                <device-os/>
            </dc-info>
        </client-oper-data>
    '''
    netconf_data = commsLib.netconf_get(env, filter)

    if "top-os" in init.wlc_data: del init.wlc_data["top-os"]
    if "per-phy" in init.wlc_data: del init.wlc_data["per-phy"]

    init.wlc_data = {**init.wlc_data, **parseLib.parse_wireless_clients(netconf_data)}
    init.wlc_data = {**init.wlc_data, **parseLib.parse_wireless_devices(netconf_data)}


def get_netconf_interfaces_oper():

    filter = f'''
        <interfaces xmlns='http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper'>
            <interface>
                <name>{env["WLC_MONITOR_INTERFACE"]}</name>
                <statistics>
                    <in-octets/>
                    <in-discards/>
                    <in-discards-64/>
                    <in-unknown-protos/>
                    <in-unknown-protos-64/>
                    <out-octets-64/>
                    <out-discards/>
                </statistics>
            </interface>
        </interfaces>
    '''             
    netconf_data = commsLib.netconf_get_x(env, filter)

    init.wlc_data = {**init.wlc_data, **parseLib.parse_interfaces_oper(netconf_data, env["WLC_MONITOR_INTERFACE"])}


def get_netconf_wireless_client_global_oper():

    filter = '''
        <client-global-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-client-global-oper">
            <client-live-stats/>
        </client-global-oper-data>
    '''
    netconf_data = commsLib.netconf_get(env, filter)

    init.wlc_data = {**init.wlc_data, **parseLib.parse_wireless_client_states(netconf_data)}


def get_netconf_wireless_access_point_oper():

    filter = '''
        <access-point-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-access-point-oper">
            <ap-name-mac-map/>
            <radio-oper-data>
                <wtp-mac/>
                <radio-slot-id/>
                <slot-id/>
                <oper-state/>
                <radio-mode/>
                <current-active-band/>
                <phy-ht-cfg>
                    <cfg-data>
                        <curr-freq/>
                        <chan-width/>
                    </cfg-data>
                </phy-ht-cfg>
            </radio-oper-data>
            <capwap-data>
                <wtp-mac/>
                <tag-info>
                    <site-tag>
                        <site-tag-name/>
                    </site-tag>
                    <rf-tag>
                        <rf-tag-name/>
                    </rf-tag>
                </tag-info>
            </capwap-data>
        </access-point-oper-data>
    '''
    netconf_data = commsLib.netconf_get(env, filter)

    init.ap_data = parseLib.parse_ap_name(netconf_data)
    init.ap_data = parseLib.parse_ap_ops_radio(netconf_data, init.ap_data)
    init.ap_data = parseLib.parse_ap_ops_capwap(netconf_data, init.ap_data)


def get_netconf_wireless_ap_cfg():

    filter = '''
        <ap-cfg-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-ap-cfg">
            <ap-tags/>
        </ap-cfg-data>
    '''
    netconf_data = commsLib.netconf_get_config(env, filter)

    init.ap_data = parseLib.parse_ap_cfg(netconf_data, init.ap_data)


def get_netconf_wireless_rrm_oper():

    filter = '''
        <rrm-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-rrm-oper">
            <rrm-measurement>
                <wtp-mac/>
                <radio-slot-id/>
                    <load>
                        <stations/>
                        <rx-noise-channel-utilization/>
                    </load>
            </rrm-measurement>
            <radio-slot>
                <wtp-mac/>
                <radio-slot-id/>
                <radio-data>
                    <dca-stats>
                        <chan-changes/>
                    </dca-stats>
                </radio-data>
            </radio-slot>
        </rrm-oper-data>
    '''
    netconf_data = commsLib.netconf_get(env, filter)

    init.ap_data = parseLib.parse_ap_rrm(netconf_data, init.ap_data)

