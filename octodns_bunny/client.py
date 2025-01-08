"""A client to access BunnyDNS API."""

from requests import Request, Session

from .client_exceptions import (
    BunnyDNSClientAPIException400,
    BunnyDNSClientAPIException401,
    BunnyDNSClientAPIException404,
    BunnyDNSClientAPIException500,
    BunnyDNSClientAPIExceptionDomainNotFound,
)


class BunnyDNSClient:
    """Main client class."""

    def __init__(self, token):
        # Set API URL
        self._api_url = "https://api.bunny.net"
        # Init Requests session
        self._api_session = Session()
        self._api_session.headers.update(
            {
                "AccessKey": f"{token}",
                "User-Agent": "octodns-bunny",
                "Accept": "application/json",
            }
        )

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def _request(
        self,
        method,
        path,
        headers,
        data,
        exception_messages,
        valid_status_codes,
        params,
    ):
        """Fire a BunnyDNS API request."""
        prepared_api_call = self._api_session.prepare_request(
            Request(
                method,
                self._api_url + path,
                json=data,
                headers=headers,
                params=params,
            )
        )
        api_call = self._api_session.send(prepared_api_call, timeout=10)
        if api_call.status_code in exception_messages.keys():
            # error_message = exception_messages[api_call.status_code]
            error_message = f"{exception_messages[api_call.status_code]} Data: {api_call.text}"
        else:
            error_message = None
        if api_call.status_code in valid_status_codes:
            # Bunny API returns HTTP 204 No Content for deletions
            if api_call.status_code == 204:
                return {}
            return api_call.json()
        if api_call.status_code == 400:
            raise BunnyDNSClientAPIException400(error_message=error_message)
        if api_call.status_code == 401:
            raise BunnyDNSClientAPIException401(error_message=error_message)
        if api_call.status_code == 404:
            raise BunnyDNSClientAPIException404(error_message=error_message)
        if api_call.status_code == 500:
            raise BunnyDNSClientAPIException500(error_message=api_call.text)

        return api_call.json()

    def list_zones(self):
        """List zones."""
        zones = []
        exception_messages = {
            401: "The request authorization failed",
            500: "Internal Server Error",
        }
        page = 1
        zone_api_call = {}
        while page == 1 or zone_api_call["HasMoreItems"] is True:
            zone_api_call = self._request(
                method="GET",
                path="/dnszone",
                headers=None,
                data=None,
                exception_messages=exception_messages,
                valid_status_codes=[200],
                params={"page": page, "per_page": 1000},
            )
            zones.extend(zone_api_call["Items"])
            page += 1

        return zones

    def add_zone(self, domain):
        """Add a zone."""
        exception_messages = {
            400: "Failed adding the DNS Zone. Model validation failed",
            401: "The request authorization failed",
            500: "Internal Server Error",
        }
        add_zone_api_call = self._request(
            method="POST",
            path="/dnszone",
            headers={"content-type": "application/json"},
            data={"Domain": domain},
            exception_messages=exception_messages,
            valid_status_codes=[201],
            params=None,
        )
        return add_zone_api_call

    def add_record(self, domain, params):
        """Add a record."""
        exception_messages = {
            400: "Failed adding the DNS record. Model validation failed.",
            401: "The request authorization failed",
            404: "The DNS Zone with the requested ID does not exist.",
            500: "Internal Server Error",
        }

        # Get Domain ID from list
        try:
            domain_id = self._map_domain_name_to_id(domain)
        except BunnyDNSClientAPIException404 as exc:
            raise BunnyDNSClientAPIExceptionDomainNotFound from exc
        # Map Record Type to integer
        params["Type"] = self._map_record_type_to_string(params["Type"])
        add_record_api_call = self._request(
            method="PUT",
            path=f"/dnszone/{domain_id}/records",
            headers={"Content-Type": "application/json"},
            data=params,
            exception_messages=exception_messages,
            valid_status_codes=[201],
            params=None,
        )
        return add_record_api_call

    def delete_record(self, domain, record_id):
        """Delete an existing record."""
        exception_messages = {
            400: "Failed deleting the DNS Record. See error response.",
            401: "The request authorization failed",
            404: "The DNS Zone or DNS Record with the requested ID does not exist.",
            500: "Internal Server Error",
        }

        # Get Domain ID from list
        domain_id = self._map_domain_name_to_id(domain)
        delete_record_api_call = self._request(
            method="DELETE",
            path=f"/dnszone/{domain_id}/records/{record_id}",
            exception_messages=exception_messages,
            valid_status_codes=[204],
            params=None,
            data=None,
            headers=None,
        )
        return delete_record_api_call

    def get_domain(self, domain):
        """Get details about a domain."""
        exception_messages = {
            401: "The request authorization failed",
            404: "The DNS Zone with the requested ID does not exist.",
            500: "Internal Server Error",
        }
        # Get Domain ID from list
        try:
            domain_id = self._map_domain_name_to_id(domain)
        except BunnyDNSClientAPIException404 as exc:
            raise BunnyDNSClientAPIExceptionDomainNotFound from exc
        get_domain_record_api_call = self._request(
            method="GET",
            path="/dnszone/" + str(domain_id),
            exception_messages=exception_messages,
            valid_status_codes=[200],
            params=None,
            data=None,
            headers=None,
        )
        return get_domain_record_api_call

    def _map_domain_name_to_id(self, domain_name):
        """Map domain name to its BunnyDNS ID."""
        # List Domains
        domains = self.list_zones()
        # Get Domain ID from list
        domain_id = None
        for domain in domains:
            if domain["Domain"] == domain_name:
                domain_id = domain["Id"]
        if domain_id is None:
            raise BunnyDNSClientAPIException404

        return domain_id

    def _map_record_type_to_string(self, _type, reverse=False, name=None):
        """Map a record type to a string."""
        type_map = {
            "A": 0,
            "AAAA": 1,
            "CNAME": 2,
            "TXT": 3,
            "MX": 4,
            "REDIRECT": 5,
            "Flatten": 6,  # This type is unused.
            "PULLZONE": 7,
            "SRV": 8,
            "CAA": 9,
            "PTR": 10,
            "SCRIPT": 11,
            "NS": 12,
        }
        if reverse:
            type_map = {v: k for k, v in type_map.items()}
            # Mapping back Bunny's CNAME to OctoDNS ALIAS record,
            # but only for the root label (name is an empty string)
            if isinstance(name, str) and not name:
                type_map[2] = "ALIAS"
        else:
            # ALIAS record on root label is supported,
            # but called CNAME in BunnyDNS
            type_map["ALIAS"] = type_map["CNAME"]
        type_mapped = type_map[_type]
        return type_mapped

    def lookup_domain_records(self, domain):
        """Lookup domain records from domain data."""
        domain_contents = self.get_domain(domain)

        # Abstract away the type IDs
        fixed_records = []
        for record in domain_contents["Records"]:
            record["Type"] = self._map_record_type_to_string(
                record["Type"], reverse=True, name=record["Name"]
            )
            fixed_records.append(record)

        return fixed_records
