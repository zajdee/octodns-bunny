"""Main BunnyDNS provider."""

# pylint: disable=invalid-name
# pylint: disable=protected-access
# pylint: disable=redefined-builtin
import logging
from collections import defaultdict

from octodns.provider import ProviderException
from octodns.provider.base import BaseProvider
from octodns.record import Record, Update

from .client import BunnyDNSClient
from .client_exceptions import BunnyDNSClientAPIExceptionDomainNotFound

OCTODNS_MONITOR_NONE = 'none'
ALLOWED_MONITORS = {OCTODNS_MONITOR_NONE: 0, "ping": 1, "http": 2}
ALLOWED_MONITORS_REVERSE = {0: "none", 1: "ping", 2: "http"}
DEFAULT_SMART_WEIGHT = 100
SMART_ROUTING_NONE = 0
SMART_ROUTING_LATENCY = 1
SMART_ROUTING_GEO = 2
OCTODNS_ROUTING_NONE = 'none'
OCTODNS_ROUTING_LATENCY = 'latency'
OCTODNS_ROUTING_GEO = 'geo'
OCTODNS_FIELD_ACCELERATED = 'accelerated'
OCTODNS_FIELD_ADVANCED = 'advanced'
OCTODNS_FIELD_BUNNYDNS = 'bunnydns'
OCTODNS_FIELD_DISABLED = 'disabled'
OCTODNS_FIELD_LATENCY_ZONE = 'latency_zone'
OCTODNS_FIELD_LATITUDE = 'latitude'
OCTODNS_FIELD_LONGITUDE = 'longitude'
OCTODNS_FIELD_MONITOR = 'monitor'
OCTODNS_FIELD_WEIGHT = 'weight'
OCTODNS_FIELD_SMART_ROUTING = 'smart_routing'
SMART_ROUTING_MAP = {
    OCTODNS_ROUTING_NONE: SMART_ROUTING_NONE,
    OCTODNS_ROUTING_LATENCY: SMART_ROUTING_LATENCY,
    OCTODNS_ROUTING_GEO: SMART_ROUTING_GEO,
}


class BunnyDNSProviderException(ProviderException):
    """BunnyDNS Provider Exception class."""


class BunnyDNSProvider(BaseProvider):
    """Main OctoDNS provider for BunnyDNS."""

    SUPPORTS_GEO = False
    SUPPORTS_DYNAMIC = False
    SUPPORTS_ROOT_NS = False
    SUPPORTS = {
        "A",
        "AAAA",
        "ALIAS",
        "CNAME",
        "TXT",
        "MX",
        "SRV",
        "CAA",
        "PTR",
        "NS",
        "BunnyDNSProvider/PULLZONE",
        "BunnyDNSProvider/SCRIPT",
        "BunnyDNSProvider/REDIRECT",
    }

    def __init__(self, id, token, *args, **kwargs):
        self.log = logging.getLogger(f"BunnyDNSProvider[{id}]")
        self.log.debug("__init__: id=%s, token=***", id)
        super().__init__(id, *args, **kwargs)
        self._client = BunnyDNSClient(token=token)

        self._zone_records = {}

    def _merge(self, source, destination):
        """
        run me with nosetests --with-doctest file.py

        >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
        >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
        >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
        True
        """
        for key, value in source.items():
            if isinstance(value, dict):
                # get node or create one
                node = destination.setdefault(key, {})
                self._merge(value, node)
            else:
                destination[key] = value

        return destination

    def _monitor_to_octodns(self, monitor):
        if monitor in ALLOWED_MONITORS_REVERSE:
            return ALLOWED_MONITORS_REVERSE[monitor]
        raise BunnyDNSProviderException(f"Unknown monitor: {monitor}")

    def _build_advanced_data(self, records):
        advanced = defaultdict(list)
        smart_routing = None
        # TODO(rzajic): maybe sort the records by fields we know, to get
        # predictible list ordering? or sort the resulting lists?
        for record in records:
            record_data = {}
            if record['Disabled']:
                record_data[OCTODNS_FIELD_DISABLED] = record['Disabled']
            if record['SmartRoutingType'] == SMART_ROUTING_GEO:
                smart_routing = OCTODNS_ROUTING_GEO
                record_data[OCTODNS_FIELD_LATITUDE] = record[
                    'GeolocationLatitude'
                ]
                record_data[OCTODNS_FIELD_LONGITUDE] = record[
                    'GeolocationLongitude'
                ]
                record_data[OCTODNS_FIELD_MONITOR] = self._monitor_to_octodns(
                    record['MonitorType']
                )
            elif record['SmartRoutingType'] == SMART_ROUTING_LATENCY:
                smart_routing = OCTODNS_ROUTING_LATENCY
                record_data[OCTODNS_FIELD_LATENCY_ZONE] = record['LatencyZone']
                record_data[OCTODNS_FIELD_MONITOR] = self._monitor_to_octodns(
                    record['MonitorType']
                )
            if record['Weight']:
                record_data[OCTODNS_FIELD_WEIGHT] = record['Weight']
            if not record_data:
                continue
            advanced[record['Value']].append(record_data)
        return smart_routing, dict(advanced)

    def _is_accelerated(self, records):
        return bool([r['Value'] for r in records if r['Accelerated']])

    def _data_for_A(self, _type, records):
        bunnydns = {}
        accelerated = self._is_accelerated(records)
        if accelerated:
            bunnydns[OCTODNS_FIELD_ACCELERATED] = accelerated
        smart_routing, advanced = self._build_advanced_data(records)
        if advanced:
            bunnydns[OCTODNS_FIELD_ADVANCED] = advanced
        if smart_routing:
            bunnydns[OCTODNS_FIELD_SMART_ROUTING] = smart_routing
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "values": [r["Value"] for r in records],
            "octodns": {OCTODNS_FIELD_BUNNYDNS: bunnydns},
        }

    def _data_for_AAAA(self, _type, records):
        bunnydns = {}
        smart_routing, advanced = self._build_advanced_data(records)
        if advanced:
            bunnydns[OCTODNS_FIELD_ADVANCED] = advanced
        if smart_routing:
            bunnydns[OCTODNS_FIELD_SMART_ROUTING] = smart_routing
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "values": [r["Value"] for r in records],
            "octodns": {OCTODNS_FIELD_BUNNYDNS: bunnydns},
        }

    def _data_for_ALIAS(self, _type, records):
        # Bunny DNS supports CNAME on root label, so let's fall through
        # We should probably check if this is the root label (`@`)
        return self._data_for_CNAME(_type=_type, records=records)

    def _data_for_CNAME(self, _type, records):
        # We can only have one value for CNAME
        record = records[0]
        bunnydns = {}
        accelerated = self._is_accelerated(records)
        if accelerated:
            bunnydns[OCTODNS_FIELD_ACCELERATED] = accelerated
        smart_routing, advanced = self._build_advanced_data(records)
        if advanced:
            bunnydns[OCTODNS_FIELD_ADVANCED] = advanced
        if smart_routing:
            bunnydns[OCTODNS_FIELD_SMART_ROUTING] = smart_routing
        return {
            "ttl": records[0]["Ttl"],
            "type": _type,
            "value": f'{record["Value"]}.',
            "octodns": {OCTODNS_FIELD_BUNNYDNS: bunnydns},
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

    def _data_for_PULLZONE(self, _type, records):
        values = []
        for record in records:
            values.append(int(record['LinkName']))
        return {"ttl": records[0]["Ttl"], "type": _type, "values": values}

    def _data_for_SCRIPT(self, _type, records):
        values = []
        for record in records:
            values.append(int(record['Value']))
        return {"ttl": 0, "type": _type, "values": values}

    def _data_for_REDIRECT(self, _type, records):
        values = []
        for record in records:
            values.append(record['Value'])
        return {"ttl": 0, "type": _type, "values": values}

    def _to_accelerated(self, record):
        return record.octodns.get(OCTODNS_FIELD_BUNNYDNS, {}).get(
            OCTODNS_FIELD_ACCELERATED, False
        )

    def _to_smart_routing_type(self, record):
        smart_routing = record.octodns.get(OCTODNS_FIELD_BUNNYDNS, {}).get(
            OCTODNS_FIELD_SMART_ROUTING, OCTODNS_ROUTING_NONE
        )
        if smart_routing not in SMART_ROUTING_MAP:
            raise BunnyDNSProviderException(
                f"Invalid smart_routing type: {smart_routing}"
            )
        return SMART_ROUTING_MAP[smart_routing]

    def _get_from_advanced_setting(self, setting, name, default, allowed=None):
        if self._is_dict(allowed):
            true_default = allowed[default]
        else:
            true_default = default
        if not self._is_dict(setting):
            return true_default
        value = setting.get(name, default)
        if allowed and value not in allowed:
            return true_default
        if self._is_dict(allowed):
            return allowed[value]
        return value

    def get_weight_default_by_smart_routing(self, record):
        """Try to figure out what the default weight should be."""
        smart_routing = self._to_smart_routing_type(record)
        # default weight is 0, unless smart_routing is enabled, then it's 100
        return 100 if smart_routing else 0

    def _params_for_A(self, record):
        # We may have the same IP repeated multiple times, with different values,
        # let's try to work around that
        advanced_settings = record.octodns.get(OCTODNS_FIELD_BUNNYDNS, {}).get(
            OCTODNS_FIELD_ADVANCED, {}
        )
        for value in record.values:
            values_advanced_setting = advanced_settings.get(value, [])
            if values_advanced_setting:
                value_advanced_setting = values_advanced_setting[0]
                advanced_settings.get(value, []).remove(value_advanced_setting)
            else:
                value_advanced_setting = {}
            yield {
                "Value": value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
                "Disabled": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_DISABLED, False
                ),
                "Accelerated": self._to_accelerated(record),
                "SmartRoutingType": self._to_smart_routing_type(record),
                "Weight": self._get_from_advanced_setting(
                    value_advanced_setting,
                    OCTODNS_FIELD_WEIGHT,
                    self.get_weight_default_by_smart_routing(record),
                ),
                "MonitorType": self._get_from_advanced_setting(
                    value_advanced_setting,
                    OCTODNS_FIELD_MONITOR,
                    OCTODNS_MONITOR_NONE,
                    ALLOWED_MONITORS,
                ),
                "LatencyZone": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LATENCY_ZONE, ''
                ),
                "GeolocationLatitude": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LATITUDE, 0
                ),
                "GeolocationLongitude": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LONGITUDE, 0
                ),
            }

    def _params_for_AAAA(self, record):
        # We may have the same IP repeated multiple times, with different values,
        # let's try to work around that
        advanced_settings = record.octodns.get(OCTODNS_FIELD_BUNNYDNS, {}).get(
            OCTODNS_FIELD_ADVANCED, {}
        )
        for value in record.values:
            values_advanced_setting = advanced_settings.get(value, [])
            if values_advanced_setting:
                value_advanced_setting = values_advanced_setting[0]
                advanced_settings.get(value, []).remove(value_advanced_setting)
            else:
                value_advanced_setting = {}
            yield {
                "Value": value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
                "Disabled": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_DISABLED, False
                ),
                "SmartRoutingType": self._to_smart_routing_type(record),
                "Weight": self._get_from_advanced_setting(
                    value_advanced_setting,
                    OCTODNS_FIELD_WEIGHT,
                    self.get_weight_default_by_smart_routing(record),
                ),
                "MonitorType": self._get_from_advanced_setting(
                    value_advanced_setting,
                    OCTODNS_FIELD_MONITOR,
                    OCTODNS_MONITOR_NONE,
                    ALLOWED_MONITORS,
                ),
                "LatencyZone": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LATENCY_ZONE, ''
                ),
                "GeolocationLatitude": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LATITUDE, 0
                ),
                "GeolocationLongitude": self._get_from_advanced_setting(
                    value_advanced_setting, OCTODNS_FIELD_LONGITUDE, 0
                ),
            }

    def _params_for_ALIAS(self, record):
        # Fall through to CNAME
        return self._params_for_CNAME(record=record)

    def _params_for_CNAME(self, record):
        # We should NOT have the same IP repeated multiple times, with different values,
        # although BunnyDNS allows that, so let's try to work around that
        advanced_settings = record.octodns.get(OCTODNS_FIELD_BUNNYDNS, {}).get(
            OCTODNS_FIELD_ADVANCED, {}
        )
        value = record.value
        values_advanced_setting = advanced_settings.get(value, [])
        if values_advanced_setting:
            value_advanced_setting = values_advanced_setting[0]
            advanced_settings.get(value, []).remove(value_advanced_setting)
        else:
            value_advanced_setting = {}
        yield {
            "Value": record.value,
            "Name": record.name,
            "Ttl": record.ttl,
            "Type": record._type,
            "Disabled": self._get_from_advanced_setting(
                value_advanced_setting, OCTODNS_FIELD_DISABLED, False
            ),
            "Accelerated": self._to_accelerated(record),
            "SmartRoutingType": self._to_smart_routing_type(record),
            "Weight": self._get_from_advanced_setting(
                value_advanced_setting,
                OCTODNS_FIELD_WEIGHT,
                self.get_weight_default_by_smart_routing(record),
            ),
            "MonitorType": self._get_from_advanced_setting(
                value_advanced_setting,
                OCTODNS_FIELD_MONITOR,
                OCTODNS_MONITOR_NONE,
                ALLOWED_MONITORS,
            ),
            "LatencyZone": self._get_from_advanced_setting(
                value_advanced_setting, OCTODNS_FIELD_LATENCY_ZONE, ''
            ),
            "GeolocationLatitude": self._get_from_advanced_setting(
                value_advanced_setting, OCTODNS_FIELD_LATITUDE, 0
            ),
            "GeolocationLongitude": self._get_from_advanced_setting(
                value_advanced_setting, OCTODNS_FIELD_LONGITUDE, 0
            ),
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

    def _params_for_PULLZONE(self, record):
        if len(record.values) != 1:
            raise BunnyDNSProviderException(
                f"Incorrect PULLZONE data, only one target is supported ({record.name})."
            )
        for value in record.values:
            yield {
                "Value": str(
                    value.value
                ),  # This string field must be present, but it's ignored by the API.
                "PullZoneId": value.value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_SCRIPT(self, record):
        if len(record.values) != 1:
            raise BunnyDNSProviderException(
                f"Incorrect SCRIPT data, only one target is supported ({record.name})."
            )
        for value in record.values:
            yield {
                "ScriptId": value.value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _params_for_REDIRECT(self, record):
        if len(record.values) != 1:
            raise BunnyDNSProviderException(
                f"Incorrect REDIRECT data, only one target is supported ({record.name})."
            )
        for value in record.values:
            yield {
                "Value": value.value,
                "Name": record.name,
                "Ttl": record.ttl,
                "Type": record._type,
            }

    def _transform_records(self, records):
        """
        Transform Bunny-specific records to SCRIPT/REDIRECT/PULLZONE
        :param records:
        :return: transformed records
        """
        result = []
        for record in records:
            record_type = record['Type']
            if record_type in ['PULLZONE', 'SCRIPT', 'REDIRECT']:
                record['Type'] = f'BunnyDNSProvider/{record_type}'
            result.append(record)
        return result

    def zone_records(self, zone):
        """Return zone records."""
        if zone.name not in self._zone_records:
            try:
                self._zone_records[zone.name] = self._transform_records(
                    self._client.lookup_domain_records(zone.name[:-1])
                )
            except BunnyDNSClientAPIExceptionDomainNotFound:
                return []

        return self._zone_records[zone.name]

    def list_zones(self):
        """List zones."""
        self.log.debug("list_zones:")
        domains = [f'{domain["Name"]}.' for domain in self._client.list_zones()]
        return sorted(domains)

    def populate(self, zone, target=False, lenient=False):
        """Populate the zone with data."""
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
                _class_method = _type.replace('BunnyDNSProvider/', '')
                data_for = getattr(self, f"_data_for_{_class_method}")
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

    def _extra_changes(self, existing, desired, changes):
        extra_changes = []
        existing_records = {r: r for r in existing.records}
        changed_records = {c.record for c in changes}
        for desired_record in desired.records:
            existing_record = existing_records.get(desired_record, None)
            if not existing_record:  # Will be created
                continue
            if desired_record in changed_records:  # Already being updated
                continue
            existing_bunnydns = existing_record.octodns.get(
                OCTODNS_FIELD_BUNNYDNS, {}
            )
            desired_bunnydns = desired_record.octodns.get(
                OCTODNS_FIELD_BUNNYDNS, {}
            )
            if (
                self._disabled_has_changed(existing_bunnydns, desired_bunnydns)
                or self._accelerated_has_changed(
                    existing_bunnydns, desired_bunnydns
                )
                or self._smart_routing_has_changed(
                    existing_bunnydns, desired_bunnydns
                )
            ):
                # something has changed in the bunnydns attributes, let's update the record
                extra_changes.append(Update(existing_record, desired_record))

        return extra_changes

    def _is_dict(self, potential_dict):
        # octodns uses the `octodns.context.ContextDict` data type,
        # which we can't easily check if it's a dict
        # so let's check if it has a `get` method
        return callable(getattr(potential_dict, "get", None))

    def _field_has_changed(self, existing, desired, fieldname, defaultvalue):
        existing_advanced = existing.get(OCTODNS_FIELD_ADVANCED, {})
        desired_advanced = desired.get(OCTODNS_FIELD_ADVANCED, {})
        existing_disabled = []
        desired_disabled = []
        for item in existing_advanced:
            for entry in existing_advanced[item]:
                existing_disabled.append(
                    (item, entry.get(fieldname, defaultvalue))
                )
        for item in desired_advanced:
            for entry in desired_advanced[item]:
                desired_disabled.append(
                    (item, entry.get(fieldname, defaultvalue))
                )
        return existing_disabled != desired_disabled

    def _disabled_has_changed(self, existing, desired):
        return self._field_has_changed(
            existing, desired, OCTODNS_FIELD_DISABLED, False
        )

    def _weight_has_changed(self, existing, desired):
        return self._field_has_changed(
            existing, desired, OCTODNS_FIELD_WEIGHT, 0
        )

    def _monitor_has_changed(self, existing, desired):
        return self._field_has_changed(
            existing, desired, OCTODNS_FIELD_MONITOR, OCTODNS_MONITOR_NONE
        )

    def _smart_routing_has_changed(self, existing, desired):
        existing_smart_routing = existing.get(
            OCTODNS_FIELD_SMART_ROUTING, OCTODNS_ROUTING_NONE
        )
        desired_smart_routing = desired.get(
            OCTODNS_FIELD_SMART_ROUTING, OCTODNS_ROUTING_NONE
        )
        if existing_smart_routing != desired_smart_routing:
            return True
        if desired_smart_routing == OCTODNS_ROUTING_NONE:
            return False
        # now we know that smart routing is enabled, weight should not be 0
        # (if you want to set weight 0, disable the record instead)
        # check for any occurences of weight == 0 and replace it with weight == 100
        for item in desired.get(OCTODNS_FIELD_ADVANCED, {}):
            for entry in desired.get(OCTODNS_FIELD_ADVANCED, {})[item]:
                if not entry.get(OCTODNS_FIELD_WEIGHT):
                    entry[OCTODNS_FIELD_WEIGHT] = DEFAULT_SMART_WEIGHT
        if self._weight_has_changed(
            existing, desired
        ) or self._monitor_has_changed(existing, desired):
            return True
        if existing_smart_routing == OCTODNS_ROUTING_LATENCY:  # latency
            # compare LatencyZone
            return self._field_has_changed(
                existing, desired, OCTODNS_FIELD_LATENCY_ZONE, False
            )
        if existing_smart_routing == OCTODNS_ROUTING_GEO:  # geo
            # compare lat/lng
            return self._field_has_changed(
                existing, desired, OCTODNS_FIELD_LATITUDE, False
            ) or self._field_has_changed(
                existing, desired, OCTODNS_FIELD_LONGITUDE, False
            )
        return False

    def _accelerated_has_changed(self, existing, desired):
        existing_accelerated = existing.get(OCTODNS_FIELD_ACCELERATED, False)
        desired_accelerated = desired.get(OCTODNS_FIELD_ACCELERATED, False)
        return existing_accelerated != desired_accelerated

    def _apply_Create(self, change):
        """Apply the create operations."""
        new = change.new
        _class_method = new._type.replace('BunnyDNSProvider/', '')
        params_for = getattr(self, f"_params_for_{_class_method}")
        for params in params_for(new):
            params['Type'] = params['Type'].replace('BunnyDNSProvider/', '')
            self._client.add_record(domain=new.zone.name[:-1], params=params)

    def _apply_Update(self, change):
        """Apply the update operations."""
        # TODO(rzajic): Replace with a proper Update logic
        # for example, the "Accelerated" value cannot be switched off by this delete/create sequence
        # that is probably a BunnyDNS bug, but whatever
        self._apply_Delete(change)
        self._apply_Create(change)

    def _apply_Delete(self, change):
        """Apply the delete operations."""
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

    def _change_keyer(self, change):
        return (change.CLASS_ORDERING, change.record.name, change.record._type)

    def _apply(self, plan):
        """Apply the changes."""
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

        # Force the operation order to be Delete() -> Create() -> Update()
        # This will help avoid problems in updating a CNAME record into an
        # A record and vice-versa
        changes.sort(key=self._change_keyer)

        for change in changes:
            class_name = change.__class__.__name__
            getattr(self, f"_apply_{class_name}")(change)

        # Clear out the cache if any
        self._zone_records.pop(desired.name, None)
