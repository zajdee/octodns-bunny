### octodns-bunny

An WIP OctoDNS Provider that allows for [Bunny.net DNS](https://bunny.net/dns/) to be used with [OctoDNS](https://github.com/octodns/octodns).

### TL;DR

Put this to `conf/managedzone.org.yaml`:

```yaml
processors:
  bunnydns:
    class: octodns_bunny.filter.BunnyDNSFilter
providers:
  bunnydns:
    class: octodns_bunny.provider.BunnyDNSProvider
    token: env/BUNNY_TOKEN
  yaml_data:
    class: octodns.provider.yaml.YamlProvider
    default_ttl: 300
    directory: ./data
    enforce_order: false
zones:
  managedzone.org.:
    processors:
    - bunnydns
    sources:
    - yaml_data
    targets:
    - bunnydns
```

Put your zone data to `data/managedzone.org.yaml` and run

```bash
export BUNNY_TOKEN=<your-bunny-api-token>
octodns-validate --config conf/managedzone.org.yaml
octodns-sync --config conf/managedzone.org.yaml
```

When you are ready with the output, run this (destructive!):

```python
octodns-sync --config conf/managedzone.org.yaml --doit
```

### Support status

| Record type    | Supported
|----------------|---
| A              | Yes
| AAAA           | Yes
| CNAME          | Yes (see below)
| TXT            | Yes
| MX             | Yes
| REDIRECT (RDR) | Yes (see below)
| Flatten        | No
| PULLZONE (PZ)  | Yes (see below)
| SRV            | Yes
| CAA            | Yes
| PTR            | Yes
| SCRIPT (SCR)   | Yes (see below)
| NS             | Yes

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

Only the `PULLZONE` record supports TTL. `REDIRECT` and `SCRIPT` records do not support TTL, which must therefore be set to `0`.
There's a supporting filter (`octodns_bunny.filter.BunnyDNSFilter`) to adjust the TTLs for you, but it's not mandatory. You can always set the `ttl` value directly in the zone data.

### CNAME quirks

This provider doesn't support multiple CNAME targets, which Bunny supports (and serves in a round-robin fashion).
NOTE: Support might be possible via "extra data".

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

Note that before you enable the CDN acceleration, there's no pullzone created for it. Once you enable it, the pullzone
gets created. If you disable the acceleration again, the pullzone stays.
In the Bunny admin panel, CDN acceleration can therefore have three values: `Disabled` (PZ doesn't exist), `Enabled`,
and `Inactive` (PZ exists, but it's not enabled).
From the `octodns-bunny` provider's point of view, `accelerated: false` covers both the `Disabled` and `Inactive` states.

There's also another BunnyDNS bug:
If you create `A` and `AAAA` records with the same label (name), then enable DNS acceleration on the `A` record, then attempt to delete/create that `AAAA` record again, you will get a `validation_error`, complaining about the `OriginUrl` field: `The origin URL is not a valid URL`.
This cannot be solved in any other way than by removing the AAAA record, as DNS acceleration is not supported for AAAA records.

### Advanced settings support

Advanced settings is supported for the following records:
- `A`
- `AAAA`

BunnyDNS also supports advanced settings for `CNAME`
(however only the Latency smart record is supported),
however OctoDNS doesn't support multiple CNAME values.
Therefore this provider doesn't support the multi-value
CNAMEs of BunnyDNS, and the smart settings do not make much sense.

Advanced setting is also supported for multiple cases of the same resource/value,
e.g. if you want to add A record with the same IP address to a single label (DNS name)
multiple times, with different georouting values.
The provider tries to match the respective records for you.

The advanced setting includes:
- Is the record enabled? (Default: `True`)
- Routing weight (default: `100` if smart routing enabled, otherwise `0`)
- Monitoring (default: `none`, possible other values: `ping` and `http`)
- Smart record type (default: `none`, possible other values: `latency`, `geo`)
  - Latency smart record: `latency_zone` must be specified (defaults to an empty string)
  - Geographic smart record: `latitude` and `longitude` must be specified (default to 0)

Please use the following syntax (per record):

```
test_latency:
- type: A
  values:
  - 1.2.3.4
  - 1.2.3.4
  octodns:
    bunnydns:
      advanced:
        1.2.3.4:
        - latency_zone: SYD
          monitor: ping
          weight: 42
          disabled: True
        - latency_zone: DE
          monitor: ping
          weight: 42
      smart_routing: latency
test_geo:
fe-geo:
- octodns:
    bunnydns:
      advanced:
        192.0.2.1:
        - latitude: -33.865143
          longitude: 151.2099
          monitor: http
          weight: 42
        - latitude: 50.110924
          longitude: 8.682127
          monitor: http
          weight: 17
        212.0.212.1:
        - latitude: 37.5326
          longitude: 127.024612
          monitor: http
      smart_routing: geo
  type: A
  values:
  - 192.0.2.1
  - 192.0.2.1
  - 212.0.212.1
```

### Getting the list of valid `latency_zone` values

There's an API call for that.
```bash
curl https://api.bunny.net/region -H 'accept: application/json' -s | \
  jq -r 'sort_by(.Name) | map(.Name + " -> " +  .RegionCode)[]'
```

The region code is the string after `->`, e.g. in this case:
```
EU: Vienna, AT -> AT
EU: Vienna, AT2 -> AT2
```
The region codes are `AT` and `AT2.