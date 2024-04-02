from octodns.provider import ProviderException


class BunnyDNSClientAPIException(ProviderException):
    pass


class BunnyDNSClientAPIException400(BunnyDNSClientAPIException):
    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__('Unknown Server Side issue')
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException401(BunnyDNSClientAPIException):
    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__('Unauthorized')
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException404(BunnyDNSClientAPIException):
    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__('Not Found')
        else:
            super().__init__(error_message)


class BunnyDNSClientAPIException500(BunnyDNSClientAPIException):
    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__('Server Error')
        else:
            super().__init__(error_message)

class BunnyDNSClientAPIExceptionDomainNotFound(BunnyDNSClientAPIException):
    def __init__(self, error_message=None):
        if error_message is None:
            super().__init__('Domain Not Found')
        else:
            super().__init__(error_message)

class BunnyDNSClientAPIExceptionType(BunnyDNSClientAPIException):
    def __init__(self, error_message):
        super().__init__(error_message)