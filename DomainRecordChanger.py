import logging
import json
from urllib.request import urlopen, Request


class DomainRecordChanger:
    def __init__(self, ip_url, domain_config):
        self.enabled = domain_config.get("enabled", False)
        self.zoneID = domain_config.get("zoneID", None)
        self.apiToken = domain_config.get("apiToken", None)
        self.sub_domains = domain_config.get("subdomains", [])
        self.domain_name = domain_config.get("domainName", None)
        self.record_type = domain_config.get("recordType", "A")
        self.ip_value = str(urlopen(ip_url[self.record_type]).read(), encoding='utf-8').strip()
        self.allow_new = domain_config.get("createNewRecord", False)
        self.request_header = {
            "Authorization": "Bearer %s" % self.apiToken,
            "Content-Type": "application/json"
        }

    def describe_record(self, full_domain_name):
        request_url = "https://api.cloudflare.com/client/v4/zones/%s/dns_records?type=%s&name=%s" % \
                      (self.zoneID, self.record_type, full_domain_name)
        describe_record_request = Request(request_url, headers=self.request_header)
        response = urlopen(describe_record_request)
        response_dict = json.loads(response.read())
        if response_dict["success"]:
            return response_dict["result_info"]["total_count"], response_dict["result"]
        else:
            for error_part in response_dict["errors"]:
                logging.error("Describe domain record for %s error. Error code: %d, %s" %
                              (full_domain_name, error_part["code"], error_part["message"]))
            return -1, None

    def create_record(self, full_domain_name, ttl, is_proxied):
        request_url = "https://api.cloudflare.com/client/v4/zones/%s/dns_records" % self.zoneID
        request_data = {
            "type": self.record_type,
            "name": full_domain_name,
            "content": self.ip_value,
            "ttl": ttl,
            "proxied": is_proxied
        }
        create_record_request = Request(request_url, data=bytes(json.dumps(request_data), encoding="utf-8"),
                                        headers=self.request_header, method='POST')
        response = urlopen(create_record_request)
        response_dict = json.loads(response.read())
        if response_dict["success"]:
            logging.info(
                "Successfully created an %s record for %s." % (self.record_type, full_domain_name))
        else:
            for error_part in response_dict["errors"]:
                logging.error("Failed to create and %s record for %s. Error code: %d, %s" %
                              (self.record_type, full_domain_name, error_part["code"], error_part["message"]))

    def update_record(self, full_domain_name, record_id, ttl, is_proxied):
        request_url = "https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s" % (self.zoneID, record_id)
        request_data = {
            "type": self.record_type,
            "name": full_domain_name,
            "content": self.ip_value,
            "ttl": ttl,
            "proxied": is_proxied
        }
        update_record_request = Request(request_url, data=bytes(json.dumps(request_data), encoding="utf-8"),
                                        headers=self.request_header, method='PUT')
        response = urlopen(update_record_request)
        response_dict = json.loads(response.read())
        if response_dict["success"]:
            logging.info("Successfully updated the %s record for %s." % (self.record_type, full_domain_name))
        else:
            for error_part in response_dict["errors"]:
                logging.error("Update domain record for %s error. Error code: %d, %s" %
                              (full_domain_name, error_part["code"], error_part["message"]))

    def change_single_domain(self, subdomain_settings):
        subdomain_name = subdomain_settings.get("name", None)
        subdomain_ttl = subdomain_settings.get("ttl", 1)
        subdomain_proxied = subdomain_settings.get("proxied", True)
        if subdomain_name is None:
            logging.error('Subdomain missing "name" field, skipped.')
            return

        full_domain_name = subdomain_name + "." + self.domain_name
        record_count, record_content = self.describe_record(full_domain_name)
        if record_count == -1:
            logging.error("Describe record error.")
        elif record_count == 0:
            if self.allow_new:
                logging.info("The Domain %s doesn't have a %s record. Will create a new record for it." %
                             (full_domain_name, self.record_type))
                self.create_record(full_domain_name, subdomain_ttl, subdomain_proxied)
            else:
                logging.info("The Domain %s doesn't have a %s record. Creating new record is disabled." %
                             (full_domain_name, self.record_type))
        elif record_count == 1:
            if (record_content[0]["content"] != self.ip_value) or (record_content[0]["proxied"] != subdomain_proxied) \
                    or (record_content[0]["ttl"] != subdomain_ttl):
                self.update_record(full_domain_name, record_content[0]['id'], subdomain_ttl, subdomain_proxied)
            else:
                logging.info("%s record for %s did not change since it is same as the machine." %
                             (self.record_type, full_domain_name))
        else:
            logging.error("There are more than 1 %s record for %s. Record for it was left unchanged." %
                          (self.record_type, full_domain_name))

    def start_ddns(self):
        if self.enabled:
            logging.info("Start DDNS for %s record under %s." % (self.record_type, self.domain_name))
            logging.info("Got ip address %s" % self.ip_value)
            if self.domain_name is None:
                logging.error("Corrupted configuration, missing domainName. DDNS ended.")
                return
            elif self.zoneID is None:
                logging.error("Corrupted configuration, missing ZoneID. DDNS ended.")
                return
            elif self.apiToken is None:
                return
                logging.error("Corrupted configuration, missing ApiToken. DDNS ended.")
            else:
                for single_subdomain in self.sub_domains:
                    self.change_single_domain(single_subdomain)
                logging.info("DDNS for %s ended." % self.domain_name)
        else:
            logging.info("DDNS for %s is disabled." % self.domain_name)