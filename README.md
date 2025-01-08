### octodns-bunny

An WIP OctoDNS Provider that allows for [Bunny.net DNS](https://bunny.net/dns/) to be used with [OctoDNS](https://github.com/octodns/octodns).

### Support status

| Record type | Supported
|---|---
| A | Yes
| AAAA | Yes
| CNAME | Yes
| TXT | Yes
| MX | Yes
| REDIRECT (RDR) | Yes (see below)
| Flatten | No
| PULLZONE (PZ) | Yes (see below)
| SRV | Yes
| CAA | Yes
| PTR | Yes
| SCRIPT (SCR) | Yes (see below)
| NS | Yes

### Redirect, PullZone, and Script records

These records are implemented using custom records.
This record must have only one value with either the numeric ID
(for `script` and `pullzone`) or the HTTP(S) destination
(for `redirect`).

```
scriptexample:
- type: BunnyDNSProvider/SCRIPT
  value: scriptid
redirectexample:
- type: BunnyDNSProvider/REDIRECT
  value: https://www.bunny.net/
pzexample:
- type: BunnyDNSProvider/PULLZONE
  value: pullzoneid
```

The script and pullzone IDs are the respective numeric IDs, as names can change, but IDs cannot.

Only the `PULLZONE` record supports TTL. `REDIRECT` and `SCRIPT` records do not support TTL, which must therefore be set to 0.
There's a supporting filter (`octodns_bunny.filter.BunnyDNSFilter`) to adjust the TTLs for you.

### CNAME at the root of the zone
OctoDNS expects you to use the `ALIAS` record for `CNAME` at the root of the DNS zone. BunnyDNS supports this, but the record type is `CNAME` (internally).
Therefore, if you create the `ALIAS` record in OctoDNS, it will be represented as `CNAME` in the BunnyDNS API and UI.
The `octodns-bunny` provider automatically maps between the `ALIAS` and `CNAME` records on both sides.

### CDN acceleration

Acceleration can be turned on for `A` and `CNAME` records. Please use the following syntax (per record):

```
testA:
- type: A
  value: 192.0.2.1
  octodns:
    bunnydns:
      accelerated: true
```

Note that before you enable the CDN acceleration, there's no pullzone created for it. Once you enable it, pullzone gets created. If you disable the acceleration again, the pullzone stays.
In the Bunny admin panel, CDN acceleration can therefore have three values: Disabled (PZ doesn't exist), Enabled, and Inactive (PZ exists, but it's not enabled).
From octodns-bunny point of view, `accelerated: false` covers both the Disabled and Inactive states.

### Advanced settings support

Advanced settings is supported for the following records:
- `A`
- `AAAA`
- `CNAME` (only the Latency smart record is supported)

The advanced setting includes:
- Is the record enabled? (Default: True)
- Routing weight (default: 100)
- Monitoring (default: None, possible other values: Ping and HTTP)
- Smart record type (default: None, possible other values: Latency, Geographic)
  - Latency smart record: Latency zone must be specified (TBD: where to get the list of latency zones?)
  - Geographic smart record: Latitude and Longitude must be specified

Please use the following syntax (per record):

```
test_latency:
- type: A
  value: 192.0.2.1
  octodns:
    bunnydns:
      enabled: false
      weight: 42
      monitor: ping # or: http
      smart_record:
        type: latency # or geo
        # region code, as returned in the
        # RegionCode field of the /region API call
        zone: SYD
test_geo:
- type: A
  value: 192.0.2.1
  octodns:
    bunnydns:
      enabled: false
      weight: 42
      monitor: ping # or: http
      smart_record:
        type: geo
        lat: 46.0826569
        lng: 14.5129233
```
