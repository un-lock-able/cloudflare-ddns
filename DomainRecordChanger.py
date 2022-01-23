import logging
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeSubDomainRecordsRequest import DescribeSubDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
import json
from urllib.request import urlopen


class DomainRecordChanger:
    def __init__(self, ali_cli, ip_url, domain_config):
        self.ali_client = ali_cli
        self.enabled = domain_config.get("enabled", False)
        self.sub_domains = domain_config.get("subdomains", [])
        self.domain_name = domain_config.get("domainName", None)
        self.record_type = domain_config.get("recordType", "A")
        self.ip_value = str(urlopen(ip_url[self.record_type]).read(), encoding='utf-8').strip()
        self.allow_new = domain_config.get("createNewRecord", False)

    def do_aliyun_request(self, request):
        return json.loads(self.ali_client.do_action(request))

    def describe_record(self, subdomain_name):
        request = DescribeSubDomainRecordsRequest()
        request.set_accept_format("json")
        request.set_DomainName(self.domain_name)
        request.set_SubDomain(subdomain_name + "." + self.domain_name)
        request.set_Type(self.record_type)
        domain_list = self.do_aliyun_request(request)
        error_code = domain_list.get('Code', None)
        if error_code is None:
            return domain_list["TotalCount"], domain_list["DomainRecords"]["Record"]
        else:
            logging.error("Describe domain record for %s error. Recommended actions from aliyun: %s" %
                          (self.domain_name, domain_list.get("Recommend", "None")))
            return -1, None

    def create_record(self, subdomain_name):
        full_domain_name = subdomain_name + "." + self.domain_name
        request = AddDomainRecordRequest()
        request.set_accept_format("json")
        request.set_DomainName(self.domain_name)
        request.set_RR(subdomain_name)
        request.set_Type(self.record_type)
        request.set_Value(self.ip_value)
        response = self.do_aliyun_request(request)
        error_code = response.get('Code', None)
        if error_code is None:
            logging.info(
                "Successfully created an %s record for %s." % (self.record_type, full_domain_name))
        else:
            logging.warning("Failed to create an %s record for %s. Recommended actions from aliyun: %s." %
                            (self.record_type, full_domain_name, response.get("Recommend", "None")))

    def update_record(self, subdomain_name, record_id):
        full_domain_name = subdomain_name + "." + self.domain_name
        request = UpdateDomainRecordRequest()
        request.set_accept_format("json")
        request.set_RecordId(record_id)
        request.set_RR(subdomain_name)
        request.set_Type(self.record_type)
        request.set_Value(self.ip_value)
        response = self.do_aliyun_request(request)
        error_code = response.get('Code', None)
        if error_code is None:
            logging.info("Successfully updated the %s record for %s." % (self.record_type, full_domain_name))
        else:
            logging.warning("Failed to update the %s record for %s. Recommended actions from aliyun: %s." %
                            (self.record_type, full_domain_name, response.get("Recommend", "None")))

    def change_single_domain(self, subdomain_name):
        full_domain_name = subdomain_name + "." + self.domain_name
        record_count, record_content = self.describe_record(subdomain_name)
        if record_count == -1:
            logging.error("Describe record error.")
        elif record_count == 0:
            if self.allow_new:
                logging.info("The Domain %s doesn't have a %s record. Will create a new record for it." %
                             (full_domain_name, self.record_type))
                self.create_record(subdomain_name)
            else:
                logging.info("The Domain %s doesn't have a %s record. Creating new record is disabled." %
                             (full_domain_name, self.record_type))
        elif record_count == 1:
            if record_content[0]["Value"].strip() != self.ip_value:
                self.update_record(subdomain_name, record_content[0]['RecordId'])
            else:
                logging.info("%s record for %s did not change since it is same as the machine." %
                             (self.record_type, full_domain_name))
        else:
            logging.error("There are more than 1 %s record for %s. Record for it was left unchanged." %
                          (self.record_type, full_domain_name))

    def start_ddns(self):
        if self.enabled:
            logging.info("Start DDNS for %s record under %s." % (self.record_type, self.domain_name))
            if self.domain_name is None:
                logging.error("Corrupted configuration, missing domainName. DDNS ended.")
            else:
                for single_subdomain in self.sub_domains:
                    self.change_single_domain(single_subdomain)
                logging.info("DDNS for %s ended." % self.domain_name)
        else:
            logging.info("DDNS for %s is disabled." % self.domain_name)