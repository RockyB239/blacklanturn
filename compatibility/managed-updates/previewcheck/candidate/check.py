"""Read-only check of the exact tested YouTube preview configuration."""
import hashlib

_LEGACY_CLIENT_SHA256 = 'cec04fc03b713ba5d0f25dee3b060fec8e0448b2a54696965bd1bcfd09213d38'
TESTED_VERSIONS = {
    '7.4.4': _LEGACY_CLIENT_SHA256,
    '1:7.4.4+blacklanturn.1': _LEGACY_CLIENT_SHA256,
    '1:7.4.4+blacklanturn.2': '8944eb98c12770372ac358e1230b9964e68b2f64973a206d3626c05fb6554b68',
}

def inspect(version, code, isa, dash):
    expected = TESTED_VERSIONS.get(version)
    if expected is None:
        return 'review'
    if hashlib.sha256(code).hexdigest() != expected:
        return 'replaced'
    if not isa or not dash:
        return 'settings'
    return 'verified'
