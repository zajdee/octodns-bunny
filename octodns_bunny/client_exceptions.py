"""BunnyDNS Client Exceptions."""

from octodns.provider import ProviderException


class BunnyDNSClientAPIException(ProviderException):
    """Basic BunnyDNS exception."""


class BunnyDNSClientAPIException400(BunnyDNSClientAPIException):
    """API exception - server side issue."""

    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__("Unknown Server Side issue")
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException401(BunnyDNSClientAPIException):
    """API exception - unauthorized."""

    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__("Unauthorized")
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException404(BunnyDNSClientAPIException):
    """API exception - not found."""

    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__("Not Found")
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException500(BunnyDNSClientAPIException):
    """API exception - server error."""

    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__("Server Error")
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIExceptionDomainNotFound(BunnyDNSClientAPIException):
    """API exception - domain not found."""

    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__("Domain Not Found")
        else:
            super().__init__(error_message)
