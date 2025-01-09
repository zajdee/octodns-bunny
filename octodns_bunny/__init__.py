"""Init the BunnyDNSProvider"""

# pylint: disable=pointless-statement
from .provider import BunnyDNSProvider, BunnyDNSProviderException
from .record import (
    BunnyDNSPullZoneRecord,
    BunnyDNSRedirectRecord,
    BunnyDNSScriptRecord,
)

__version__ = '0.0.2'

# quell warnings
BunnyDNSPullZoneRecord
BunnyDNSScriptRecord
BunnyDNSRedirectRecord
BunnyDNSProvider
BunnyDNSProviderException
