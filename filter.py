from octodns.processor.base import BaseProcessor


class BunnyDNSFilter(BaseProcessor):
    '''
    We use the URLFWD records to support Bunny's PullZone, Script,
    and Redirect records.
    BunnyDNS uses zero TTL for script and redirect records.
    This processor cleans up the URLFWD records to match the standard.

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

    def __init__(self, name):
        super().__init__(name)

    def cleanup_URLFWD(self, record):
        target = record.values[0].target
        if target.startswith('pz://'):
            return
        record.ttl = 0

    def process_source_zone(self, zone, *args, **kwargs):
        for record in zone.records:
            if record.lenient:
                continue
            if record._type == "URLFWD":
                self.cleanup_URLFWD(record)
        return zone
