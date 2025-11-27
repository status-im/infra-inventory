import requests
import json
import logging
from typing import List, Dict, Optional
from .config import Config

class ConsulClient:
    def __init__(self):
        self.config = Config()
        self.base_url = f"{self.config.CONSUL_SCHEME}://{self.config.CONSUL_HOST}:{self.config.CONSUL_PORT}/v1"
        self.headers = {}
        if self.config.CONSUL_TOKEN:
            self.headers['X-Consul-Token'] = self.config.CONSUL_TOKEN

        self.logger = logging.getLogger(__name__)

    def get_datacenters(self) -> List[str]:
        """Get all data centers from Consul catalog"""
        url = f"{self.base_url}/catalog/datacenters"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching services from Consul: {e}")
            return None

    def get_services(self, dc: str) -> Optional[Dict]:
        """Get all services from Consul catalog"""
        url = f"{self.base_url}/catalog/services"
        try:
            response = requests.get(url, headers=self.headers, params={'dc': dc, 'filter': 'ServiceTags contains "ssl-proxy-backend"'})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching services from Consul: {e}")
            return None

    def get_service_instances(self, service_name: str, dc: str) -> Optional[List[Dict]]:
        """Get all instances of a specific service from Consul catalog"""
        url = f"{self.base_url}/catalog/service/{service_name}"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={
                    'dc': dc,
                    'tag': 'ssl-proxy-backend'
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching instances for service {service_name} from Consul: {e}")
            return None

    def get_websites_from_consul(self) -> List[Dict]:
        """
        Get websites information from Consul catalog
        Returns a list of website dictionaries with name, environment, stage, url, description, and tags
        """
        websites = []
        dcs = self.get_datacenters()
        if not dcs:
            self.logger.error("No datacenter returned, verify Consul connection")
            return websites
        for dc in dcs:
            services = self.get_services(dc)
            self.logger.info("%s services founds in data center %s", len(services), dc)
            if not services:
                return websites

            for service_name in services:
                self.logger.info("Services : %s", service_name)
                if service_name == 'consul':  # Skip Consul itself
                    continue

                instances = self.get_service_instances(service_name, dc)
                if not instances:
                    continue

                for instance in instances:
                    self.logger.info(instances)
                    name = instance.get('Service', service_name)
                    if name == 'caddy-git':
                        name = instance.get('ServiceMeta').get('proxy_fqdn')
                    # Create website entry
                    website = {
                        'name': name,
                        'environment': instance.get('NodeMeta').get('env'),
                        'stage': instance.get('NodeMeta').get('stage'),
                        'url': f"https://{instance.get('ServiceMeta').get('proxy_fqdn')}",
                        'description': instance.get('description', ''),
                        'tags': instance.get('ServiceTags')
                    }
                    website.get('tags').remove('ssl-proxy-backend')
                    self.logger.debug(website)
                    websites.append(website)

        return websites
