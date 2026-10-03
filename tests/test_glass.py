import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"tools"))
import importlib.util,pathlib,unittest,tempfile,json
from unittest import mock
root=pathlib.Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
g=module('glass',root/'tools/gnome_glass.py');i=module('installer_glass',root/'tools/install.py')
class GlassTests(unittest.TestCase):
 def test_no_global_opacity_and_exact_scope(self):
  d=g.desired(['firefox_firefox','firefox']);self.assertEqual(d['opacity'],'255');self.assertEqual(d['enable-all'],'false');self.assertEqual(d['dynamic-opacity'],'false')
  with self.assertRaises(ValueError):g.desired(['*firefox*'])
  with self.assertRaises(ValueError):g.scope_ok({'enable-all':'true','whitelist':'[]'},['firefox'])
  with self.assertRaises(ValueError):g.scope_ok({'enable-all':'false','whitelist':"['other-app']"},['firefox'])
 def test_glass_install_and_return_to_opaque(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'prefs.js').write_text('// prefs');i.install(p,True,False,True);self.assertIn('glass.css',(p/'chrome/userChrome.css').read_text());self.assertTrue(i.load(p)['glass']);i.install(p,True,False,False);self.assertNotIn('glass.css',(p/'chrome/userChrome.css').read_text())
 def test_restore_refuses_user_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'backup.json';values=g.desired(['firefox']);p.write_text(json.dumps({'schema':g.SCHEMA,'classes':['firefox'],'restored':False,'applied':values,'original':{**values,'opacity':'215','blur':'false','whitelist':'[]'}}))
   with mock.patch.object(g,'get',side_effect=lambda k:'220' if k=='opacity' else values[k]),mock.patch.object(g,'setkey') as setter:
    with self.assertRaises(ValueError):g.restore(p,True)
    setter.assert_not_called()
if __name__=='__main__':unittest.main()
