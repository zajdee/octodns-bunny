"""Custom BunnyDNSProvider records."""

from octodns.equality import EqualityTupleMixin
from octodns.record import Record, ValuesMixin


class _BunnyDNSPullZoneValue(EqualityTupleMixin, dict):
    """Class covering the PULLZONE record value."""

    @classmethod
    def validate(cls, data, _type):
        """Basic validation."""
        reasons = []
        if len(data) != 1:
            reasons.append('Only one value is allowed')
        return reasons

    @classmethod
    def process(cls, values):
        """Process multiple values."""
        return [_BunnyDNSPullZoneValue(v) for v in values]

    def __init__(self, value):
        """Initialize the class."""
        self.value = value
        self._type = 'PULLZONE'

    def __hash__(self):
        """Return a hash of the class."""
        return hash((self._type, self.value))

    def _equality_tuple(self):
        """Return a tuple to check for equality."""
        return (self._type, self.value)

    def __repr__(self):
        return f'{self.value}'


class _BunnyDNSScriptValue(EqualityTupleMixin, dict):
    """Class covering the SCRIPT record value."""

    @classmethod
    def validate(cls, data, _type):
        """Basic validation."""
        reasons = []
        if len(data) != 1:
            reasons.append('Only one value is allowed')
        return reasons

    @classmethod
    def process(cls, values):
        """Process multiple values."""
        return [_BunnyDNSScriptValue(v) for v in values]

    def __init__(self, value):
        """Initialize the class."""
        self.value = value
        self._type = 'SCRIPT'

    def __hash__(self):
        """Return a hash of the class."""
        return hash((self._type, self.value))

    def _equality_tuple(self):
        """Return a tuple to check for equality."""
        return (self._type, self.value)

    def __repr__(self):
        return f'{self.value}'


class _BunnyDNSRedirectValue(EqualityTupleMixin, dict):
    """Class covering the REDIRECT record value."""

    @classmethod
    def validate(cls, data, _type):
        """Basic validation."""
        reasons = []
        if len(data) != 1:
            reasons.append('Only one value is allowed')
        return reasons

    @classmethod
    def process(cls, values):
        """Process multiple values."""
        return [_BunnyDNSRedirectValue(v) for v in values]

    def __init__(self, value):
        """Initialize the class."""
        self.value = value
        self._type = 'REDIRECT'

    def __hash__(self):
        """Return a hash of the class."""
        return hash((self._type, self.value))

    def _equality_tuple(self):
        """Return a tuple to check for equality."""
        return (self._type, self.value)

    def __repr__(self):
        return f'{self.value}'


class BunnyDNSPullZoneRecord(ValuesMixin, Record):
    """Class covering the PULLZONE record."""

    _type = 'BunnyDNSProvider/PULLZONE'
    _value_type = _BunnyDNSPullZoneValue


class BunnyDNSRedirectRecord(ValuesMixin, Record):
    """Class covering the REDIRECT record."""

    _type = 'BunnyDNSProvider/REDIRECT'
    _value_type = _BunnyDNSRedirectValue


class BunnyDNSScriptRecord(ValuesMixin, Record):
    """Class covering the SCRIPT record."""

    _type = 'BunnyDNSProvider/SCRIPT'
    _value_type = _BunnyDNSScriptValue


Record.register_type(BunnyDNSPullZoneRecord)
Record.register_type(BunnyDNSRedirectRecord)
Record.register_type(BunnyDNSScriptRecord)
