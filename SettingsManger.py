import json
import logging
import time


class SettingsManager:
    def __init__(self, settings_path):
        try:
            with open(settings_path) as setting_file:
                self.settings = json.load(setting_file)
            self.is_valid = True
        except FileNotFoundError:
            self.init_log_when_error()
            logging.error("The settings file %s not found. Please Check your spelling." % settings_path)
            self.is_valid = False

    def get_log_settings(self):
        try:
            log_settings = {"logLevel": self.settings["logSettings"]["logLevel"],
                            "logFileName": self.settings["logSettings"]["logFileName"]}
        except IndexError as e:
            self.init_log_when_error()
            logging.error("Logging settings corrupted or missing: %s" % e)
            self.is_valid = False
        return log_settings

    def get_ip_url(self):
        logging.debug("Read get ip url...")
        try:
            ip_urls = {"A": self.settings["getIPUrls"]["IPv4"],
                       "AAAA": self.settings["getIPUrls"]["IPv6"]}
        except IndexError as e:
            logging.error("Get_ip_url settings corrupted or missing: %s" % e)
            ip_urls = None
            self.is_valid = False
        logging.debug("Read get ip url success.")
        return ip_urls

    def get_domain_settings(self):
        logging.debug("Read domain settings...")
        try:
            domains = self.settings["domainSettings"]
        except IndexError as e:
            logging.error("Domain settings corrupted or missing: %s" % e)
            domains = None
            self.is_valid = False
        logging.debug("Read domain settings success.")
        return domains

    def init_log_when_error(self):
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        log_file_name = "aliddns_error_log_%s.log" % time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime(time.time()))
        logging.basicConfig(filename=log_file_name, level=logging.INFO, format=log_format)
