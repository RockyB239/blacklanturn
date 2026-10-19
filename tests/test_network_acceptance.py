import copy
import unittest
from tools import verify_release


class NetworkAcceptance(unittest.TestCase):
    def setUp(self):
        self.manifest={'files':{'resources/modules/jurialmunkey/reqapi.py':'a'*64}}
        case={'passed':True,'source_sha256':'a'*64,'actual_module_loaded':True,
              'server_cooldown_seconds':120,'minimum_cooldown_seconds':60,
              'ordinary_http_error_logs_redacted':True,'successful_calls':10000,
              'successful_synthetic_calls_seconds':0.05,'extra_transport_calls':0,'new_background_thread':False}
        self.receipt={'passed':True,'runtime':'21.3 (21.3.0)','personal_profile_accessed':False,
                      'editions':{name:dict(case) for name in ('General','Apple-TV-Mac')}}

    def gate(self, receipt=None):
        method=getattr(verify_release,'verify_shared_network_acceptance',None)
        self.assertTrue(callable(method),'No source-bound shared network native acceptance gate')
        method(self.receipt if receipt is None else receipt,self.manifest)

    def test_exact_both_edition_native_sources_pass(self):self.gate()

    def test_missing_edition_or_old_unloaded_source_cannot_pass(self):
        for mode in ('missing','old','unloaded'):
            receipt=copy.deepcopy(self.receipt)
            if mode=='missing':del receipt['editions']['General']
            elif mode=='old':receipt['editions']['General']['source_sha256']='b'*64
            else:receipt['editions']['General']['actual_module_loaded']=False
            with self.subTest(mode=mode),self.assertRaises(AssertionError):self.gate(receipt)

    def test_missing_privacy_cooldown_or_success_preservation_blocks_release(self):
        for key,value in [('ordinary_http_error_logs_redacted',False),('server_cooldown_seconds',15),
                          ('minimum_cooldown_seconds',15),('extra_transport_calls',1),('new_background_thread',True),
                          ('successful_calls',1),('successful_synthetic_calls_seconds',float('nan'))]:
            receipt=copy.deepcopy(self.receipt);receipt['editions']['General'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):self.gate(receipt)


if __name__=='__main__':unittest.main()
