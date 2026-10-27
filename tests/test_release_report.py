import json,tempfile,unittest,zipfile
from pathlib import Path
from tools.release_report import report
class ReleaseReport(unittest.TestCase):
 def test_packaged_identity_and_review_delta_without_userdata_export(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'release.zip'
   with zipfile.ZipFile(p,'w') as z:
    z.writestr('userdata/blacklanturn-build.json',json.dumps({'build_version':'1.2.3','edition':'general'}))
    z.writestr('addons/plugin.video.example/addon.xml','<addon id="plugin.video.example" version="1:6.7.97+blacklanturn.1"/>')
    z.writestr('userdata/addon_data/plugin.video.example/settings.xml','private fixture - must not appear in report')
   same=report(p,{'plugin.video.example':'6.7.97'});self.assertEqual(same['upstream_review'],[])
   new=report(p,{'plugin.video.example':'6.7.98'});self.assertEqual(new['build'],'1.2.3');self.assertEqual(len(new['upstream_review']),1)
   self.assertNotIn('private fixture',json.dumps(new));self.assertEqual(new['addons'],{'plugin.video.example':'1:6.7.97+blacklanturn.1'})
