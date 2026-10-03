import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"tools"))
import importlib.util, pathlib, tempfile, unittest
from unittest import mock
spec=importlib.util.spec_from_file_location('installer',pathlib.Path(__file__).resolve().parents[1]/'tools/install.py')
i=importlib.util.module_from_spec(spec); spec.loader.exec_module(i)
class InstallTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name); self.p=self.root/'profile'; self.p.mkdir(); (self.p/'prefs.js').write_text('user_pref("example", true);\n')
 def tearDown(self): self.tmp.cleanup()
 def test_symlink_original_and_update_and_restore(self):
  original=self.root/'old-theme'; original.mkdir(); (original/'userChrome.css').write_text('@import "module.css";\n'); (original/'module.css').write_text('/* untouched */'); (original/'userContent.css').write_text('/* original */'); (self.p/'chrome').symlink_to(original)
  user=b'// custom\nuser_pref("example", true);'; (self.p/'user.js').write_bytes(user)
  prefs=(self.p/'prefs.js').read_bytes(); i.install(self.p,True,False)
  self.assertEqual((self.p/'chrome/userContent.css').read_text(),'/* original */'); self.assertEqual((original/'userChrome.css').read_text(),'@import "module.css";\n')
  self.assertEqual((self.p/'prefs.js').read_bytes(),prefs); i.install(self.p,True,True); self.assertIn('transparency.css',(self.p/'chrome/userChrome.css').read_text())
  i.uninstall(self.p,True); self.assertTrue((self.p/'chrome').is_symlink()); self.assertEqual((self.p/'chrome').resolve(),original); self.assertEqual((self.p/'user.js').read_bytes(),user)
 def test_absent_chrome_and_userjs_and_later_user_edit(self):
  i.install(self.p,True,False); u=self.p/'user.js'; u.write_bytes(u.read_bytes()+b'// later user edit\n'); i.uninstall(self.p,True)
  self.assertFalse((self.p/'chrome').exists()); self.assertEqual(u.read_text(),'// later user edit\n')
 def test_dryrun_and_geometry_drift_refusal(self):
  i.install(self.p,False,False); self.assertFalse((self.p/i.STATE).exists()); i.install(self.p,True,False)
  (self.p/'chrome/aurora/modules/buttons.css').write_text('edited')
  with self.assertRaises(ValueError): i.uninstall(self.p,True)
  self.assertTrue((self.p/i.STATE/'state.json').exists())
 def test_explicit_profile_and_collision_refusal(self):
  with self.assertRaises(ValueError): i.profile_path('relative')
  q=self.root/'alias'; q.symlink_to(self.p)
  with self.assertRaises(ValueError): i.profile_path(str(q))
  (self.p/'chrome').mkdir(); (self.p/'chrome/aurora').mkdir()
  with self.assertRaises(ValueError): i.install(self.p,True,False)
 def test_original_directory_preserved(self):
  c=self.p/'chrome'; c.mkdir(); (c/'unrelated.css').write_text('original'); i.install(self.p,True,False); i.uninstall(self.p,True)
  self.assertFalse(c.is_symlink()); self.assertEqual((c/'unrelated.css').read_text(),'original'); self.assertFalse((self.p/'user.js').exists())
 def test_failed_install_restores_original(self):
  c=self.p/'chrome'; c.mkdir(); (c/'userChrome.css').write_text('original'); (self.p/'user.js').write_text('original prefs')
  with mock.patch.object(i,'write_theme',side_effect=OSError('injected failure')):
   with self.assertRaises(OSError): i.install(self.p,True,False)
  self.assertEqual((c/'userChrome.css').read_text(),'original'); self.assertEqual((self.p/'user.js').read_text(),'original prefs'); self.assertFalse((self.p/i.STATE).exists())
 def test_added_file_and_theme_symlink_are_refused(self):
  i.install(self.p,True,False); c=self.p/'chrome'; (c/'personal.css').write_text('keep')
  with self.assertRaises(ValueError): i.uninstall(self.p,True)
  self.assertEqual((c/'personal.css').read_text(),'keep'); (c/'personal.css').unlink()
  (c/'aurora').rename(c/'saved'); (c/'aurora').symlink_to(c/'saved')
  with self.assertRaises(ValueError): i.install(self.p,True,False)
 def test_failed_uninstall_restores_installed_state(self):
  i.install(self.p,True,False); before=(self.p/'user.js').read_bytes()
  original_atomic=i.atomic
  def fail_user(p,data):
   if p.name=='state.json' and b'"uninstalled"' in data: raise OSError('injected failure')
   return original_atomic(p,data)
  with mock.patch.object(i,'atomic',side_effect=fail_user):
   with self.assertRaises(OSError): i.uninstall(self.p,True)
  self.assertEqual((self.p/'user.js').read_bytes(),before); i.validate(self.p,i.load(self.p))
if __name__=='__main__': unittest.main()
