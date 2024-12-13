import logging
from collections import defaultdict

from octodns.provider.base import BaseProvider
from octodns.record import Record

from .BunnyDNSClient import BunnyDNSClient
from .BunnyDNSClientAPIException import BunnyDNSClientAPIExceptionDomainNotFound

__version__ = '0.0.1'


class BunnyDNSProvider(BaseProvider):
    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS_ROOT_NS = True
    SUPPORTS = {"A", "AAAA", "CNAME", "TXT", "MX", "SRV", "CAA", "PTR", "NS"}

    def __init__(self, id, token, *args, **kwargs):
        self.log = logging.getLogger(f"BunnyDNSProvider[{id}]")
        self.log.debug("__init__: id=%s, token=***", id)
        super().__init__(id, *args, **kwargs)
        self._client = BunnyDNSClient(token=token)

        self._zone_records = {}

    def _data_for_A(self, _type, records):
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "values": [r["Value"] for r in records],
        }

    def _data_for_AAAA(self, _type, records):
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "values": [r["Value"] for r in records],
        }

    def _data_for_CNAME(self, _type, records):
        # We can only have one value for CNAME
        record = records[0]
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "value": f'{record["Value"]}.',
        }

    def _data_for_TXT(self, _type, records):
        values = [value["Value"].replace(";", "\\;") for value in records]
        return {"ttl": records[0]["Ttl"], "type": _type, "values": values}

    def _data_for_MX(self, _type, records):
        values = []
        for record in records:
            values.append(
                {
                    "preference": record["Priority"],
                    "exchange": f'{record["Value"]}.',
                }
            )
        return {"ttl": records[0]["Ttl"], "type": _type, "values": values}

    def _data_for_SRV(self, _type, records):
        values = []
        for record in records:
            target = f'{record["Value"]}.' if record["Value"] != "." else "."
            values.append(
                {
                    "port": record["Port"],
                    "priority": record["Priority"],
                    "target": target,
                    "weight": record["Weight"],
                }
            )
        return {"type": _type, "ttl": records[0]["Ttl"], "values": values}

    def _data_for_CAA(self, _type, records):
        values = []
        for record in records:
            values.append(
                {
                    "flags": record["Flags"],
                    "tag": record["Tag"],
                    "value": record["Value"],
                }
            )
        return {"ttl": records[0]["Ttl"], "type": _type, "values": values}

    def _data_for_PTR(self, _type, records):
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "values": [r["Value"] for r in records],
        }

    def _data_for_NS(self, _type, records):
        values = []
        for record in records:
            values.append(f'{record["Value"]}.')
        return {"ttl": records[0]["Ttl"], "type": _type, "values": values}

    def _params_for_A(self, record):
        for value in record.values:
            yield {
                "Value": value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_AAAA(self, record):
        for value in record.values:
            yield {
                "Value": value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_CNAME(self, record):
        yield {
            "Value": record.value,
            "Name": record.name,
            "Ttl": record.ttl,
            "Type": record._type,
        }

    def _params_for_TXT(self, record):
        # DigitalOcean doesn't want things escaped in values, so we
        # have to strip them here and add them when going the other way
        for value in record.values:
            yield {
                "Value": value.replace("\\;", ";"),
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_MX(self, record):
        for value in record.values:
            yield {
                "Value": value.exchange,
                "Name": record.name,
                "Priority": value.preference,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_SRV(self, record):
        for value in record.values:
            yield {
                "Value": value.target,
                "Name": record.name,
                "Port": value.port,
                "Priority": value.priority,
                "Ttl": record.ttl,
                "Type": record._type,
                "Weight": value.weight,
            }

    def _params_for_CAA(self, record):
        for value in record.values:
            yield {
                "Value": value.value,
                "Flags": value.flags,
                "Name": record.name,
                "Tag": value.tag,
                "Ttl": record.ttl,
                "RecordType": record._type,
            }

    def _params_for_PTR(self, record):
        yield {
            "Value": record.value,
            "Name": record.name,
            "Ttl": record.ttl,
            "Type": record._type,
        }

    def _params_for_NS(self, record):
        for value in record.values:
            yield {
                "Value": value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def zone_records(self, zone):
        if zone.name not in self._zone_records:
            try:
                self._zone_records[zone.name] = (
                    self._client.lookup_domain_records(zone.name[:-1])
                )
            except BunnyDNSClientAPIExceptionDomainNotFound:
                return []

        return self._zone_records[zone.name]

    def list_zones(self):
        self.log.debug("list_zones:")
        domains = [f'{domain["Name"]}.' for domain in self._client.list_zones()]
        return sorted(domains)

    def populate(self, zone, target=False, lenient=False):
        self.log.debug(
            "populate: name=%s, target=%s, lenient=%s",
            zone.name,
            target,
            lenient,
        )

        values = defaultdict(lambda: defaultdict(list))
        for record in self.zone_records(zone):
            _type = record["Type"]
            if _type not in self.SUPPORTS:
                self.log.warning(
                    "populate: skipping unsupported %s record", _type
                )
                continue
            values[record["Name"]][record["Type"]].append(record)

        before = len(zone.records)
        for name, types in values.items():
            for _type, records in types.items():
                data_for = getattr(self, f"_data_for_{_type}")
                record = Record.new(
                    zone,
                    name,
                    data_for(_type, records),
                    source=self,
                    lenient=lenient,
                )
                zone.add_record(record, lenient=lenient)

        exists = zone.name in self._zone_records
        self.log.info(
            "populate:   found %s records, exists=%s",
            len(zone.records) - before,
            exists,
        )
        return exists

    def _apply_Create(self, change):
        new = change.new
        params_for = getattr(self, f"_params_for_{new._type}")
        for params in params_for(new):
            self._client.add_record(domain=new.zone.name[:-1], params=params)

    def _apply_Update(self, change):
        self._apply_Delete(change)
        self._apply_Create(change)

    def _apply_Delete(self, change):
        existing = change.existing
        zone = existing.zone
        for record in self.zone_records(zone):
            if (
                existing.name == record["Name"]
                and existing._type == record["Type"]
            ):
                self._client.delete_record(
                    domain=zone.name[:-1], record_id=record["Id"]
                )

    def _apply(self, plan):
        desired = plan.desired
        changes = plan.changes
        self.log.debug(
            "_apply: zone=%s, len(changes)=%d", desired.name, len(changes)
        )

        domain_name = desired.name[:-1]
        try:
            self._client.get_domain(domain=domain_name)
        except BunnyDNSClientAPIExceptionDomainNotFound:
            self.log.debug("_apply:   no matching zone, creating domain")
            self._client.add_zone(domain_name)

        for change in changes:
            class_name = change.__class__.__name__
            getattr(self, f"_apply_{class_name}")(change)

        # Clear out the cache if any
        self._zone_records.pop(desired.name, None)
