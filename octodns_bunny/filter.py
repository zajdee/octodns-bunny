"""The BunnyDNS filters."""

# pylint: disable=protected-access

from octodns.processor.base import BaseProcessor


class BunnyDNSFilter(BaseProcessor):
    '''
    BunnyDNS uses zero TTL for the script and redirect records.
    This processor cleans up these records to match the standard.

    Use in your config as:
    processors:
      bunnydns:
        class: octodns_bunny.filter.BunnyDNSFilter
    providers:
      bunnydns:
        class: octodns_bunny.BunnyDNSProvider
        token: env/BUNNY_TOKEN
      yaml_data:
        class: octodns.provider.yaml.YamlProvider
        default_ttl: 300
        directory: ./data
        enforce_order: false
    zones:
      zone.org.:
        sources:
        - yaml_data
        processors:
        - bunnydns
        targets:
        - bunnydns
    '''

    # pylint: disable=arguments-differ
    def process_source_zone(self, zone, *args, **kwargs):
        # pylint: disable=unused-argument
        for record in zone.records:
            if record.lenient:
                continue
            if record._type in [
                'BunnyDNSProvider/SCRIPT',
                'BunnyDNSProvider/REDIRECT',
            ]:
                record.ttl = 0
        return zone
