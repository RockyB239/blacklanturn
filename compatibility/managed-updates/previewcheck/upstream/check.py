"""Read-only check of the exact tested YouTube preview configuration."""
import hashlib

TESTED_SHA256 = 'cec04fc03b713ba5d0f25dee3b060fec8e0448b2a54696965bd1bcfd09213d38'

def inspect(version, code, isa, dash):
    if version != '7.4.4':
        return 'review'
    if hashlib.sha256(code).hexdigest() != TESTED_SHA256:
        return 'replaced'
    if not isa or not dash:
        return 'settings'
    return 'verified'
