"""Operational notice proofs; immutable archive provenance is unchanged.

The in-place updater deliberately keeps newer ordinary dependencies. Skin
Variables is unmodified stock code, so its metadata version cannot be a proof
that BlackLanturn-owned code/patches were installed. No managed patch is exempt.
"""
import copy
STOCK_METADATA='addons/script.skinvariables/addon.xml'
def curate(entry):
 result=copy.deepcopy(entry)
 if result.get('version')=='1.1.58':result['files'].pop(STOCK_METADATA,None)
 return result
