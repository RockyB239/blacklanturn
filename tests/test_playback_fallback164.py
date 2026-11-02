"""Explain an existing selection fallback without changing source ranking."""
from pathlib import Path
import importlib.util,copy,unittest
P=Path(__file__).resolve().parents[1]/'compatibility/reliability164/umbrella/resources/lib/modules'
spec=importlib.util.spec_from_file_location('prefs164',P/'source_preferences.py');prefs=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefs)
class FallbackReasons(unittest.TestCase):
 def message(self,policy,matches):
  self.assertTrue(callable(getattr(prefs,'fallback_message',None)),'Reason-specific fallback text missing')
  return prefs.fallback_message(policy,matches)
 def test_no_size_provider_match_explains_limit_without_claiming_connection_failure(self):
  policy={'ceiling':2.3,'debrid':'TorBox'};before=copy.deepcopy(policy);text=self.message(policy,0)
  self.assertIn('size',text);self.assertIn('service',text);self.assertNotIn('connection',text.lower());self.assertEqual(policy,before)
 def test_resolver_failure_does_not_claim_no_matching_results(self):
  text=self.message({'ceiling':2.3,'debrid':'TorBox'},3);self.assertIn('could not be opened',text);self.assertNotIn('None fit',text)
 def test_normal_autoplay_and_manual_selection_remain_quiet(self):
  self.assertIsNone(self.message(None,0));self.assertIsNone(self.message(None,3))
 def test_messages_fit_a_brief_toast_and_do_not_echo_urls_or_credentials(self):
  for count in (0,3):
   text=self.message({'ceiling':2.3,'debrid':'https://private.invalid/token=secret'},count);self.assertLessEqual(len(text),32);self.assertNotIn('secret',text);self.assertNotIn('https',text)

class RealSelectionBoundary(unittest.TestCase):
 def test_actual_fallback_uses_the_existing_candidates_and_explains_resolve_failure(self):
  import ast,types
  tree=ast.parse((P/'sources.py').read_text())
  block=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='len(items) > 0' and any(isinstance(c,ast.Attribute) and c.attr=='session_candidates' for c in ast.walk(n)))
  fn=ast.FunctionDef(name='run',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[block],decorator_list=[]);module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
  candidates=[{'size':2,'debrid':'TorBox','source':'cached torrent'}];events=[]
  pref=types.SimpleNamespace(get=lambda meta:None,get_session=lambda meta:{'ceiling':2.3,'debrid':'TorBox'},session_candidates=prefs.session_candidates,fallback_message=prefs.fallback_message)
  s=types.SimpleNamespace(meta={},sourcesAutoPlay=lambda items:(events.append(('resolve',items)) or None),sourceSelect=lambda *args:events.append(('select',args[1])))
  ns=dict(items=candidates,uncached_items=[],source_preferences=pref,self=s,force_selection=False,select='1',control=types.SimpleNamespace(notification=lambda **kw:events.append(('notice',kw)),sleep=lambda n:None),title='Episode')
  exec(compile(module,str(P/'sources.py'),'exec'),ns);ns['run']()
  self.assertEqual(events[0],('resolve',candidates));self.assertEqual(events[-1],('select',candidates));self.assertEqual(events[1],('notice',{'title':'Play Next','message':prefs.fallback_message(pref.get_session({}),1)}))
