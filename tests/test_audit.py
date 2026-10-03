import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"tools"))
import importlib.util,pathlib,tempfile,unittest,os,json
from unittest import mock
root=pathlib.Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
i=module('audit_installer',root/'tools/install.py')
class InstallerAuditTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.temp.name);self.p=self.base/'profile';self.p.mkdir();(self.p/'prefs.js').write_text('// synthetic prefs')
 def tearDown(self):self.temp.cleanup()
 def relative_theme(self):
  old=self.base/'theme';old.mkdir();(old/'userChrome.css').write_text('/* old UI */');(old/'userContent.css').write_text('/* old content */');(self.p/'chrome').symlink_to('../theme');return old
 def test_relative_chrome_install_update_remove(self):
  old=self.relative_theme();i.install(self.p,True,False);self.assertEqual((self.p/'chrome/userContent.css').read_text(),'/* old content */');i.install(self.p,True,False,True);i.uninstall(self.p,True);self.assertEqual(os.readlink(self.p/'chrome'),'../theme');self.assertEqual((old/'userChrome.css').read_text(),'/* old UI */')
 def test_relative_chrome_failed_install_restore(self):
  self.relative_theme()
  with mock.patch.object(i,'write_theme',side_effect=OSError('injected write failure')):
   with self.assertRaises(OSError):i.install(self.p,True,False)
  self.assertEqual(os.readlink(self.p/'chrome'),'../theme');self.assertFalse((self.p/i.STATE).exists())
 def test_relative_chrome_failed_uninstall_rollback(self):
  self.relative_theme();i.install(self.p,True,False);original=i.atomic
  def fail(p,data):
   if p.name=='state.json' and b'"uninstalled"' in data:raise OSError('injected metadata failure')
   return original(p,data)
  with mock.patch.object(i,'atomic',side_effect=fail):
   with self.assertRaises(OSError):i.uninstall(self.p,True)
  i.validate(self.p,i.load(self.p));self.assertEqual((self.p/'chrome/userContent.css').read_text(),'/* old content */');i.uninstall(self.p,True);self.assertEqual(os.readlink(self.p/'chrome'),'../theme')
 def test_partial_userjs_backup_does_not_overwrite_original(self):
  original=b'// original complete user preferences\n';(self.p/'user.js').write_bytes(original);copy=i.shutil.copy2
  def fail(src,dst,*args,**kwargs):
   if pathlib.Path(src)==self.p/'user.js':pathlib.Path(dst).write_bytes(b'partial');raise OSError('injected backup failure')
   return copy(src,dst,*args,**kwargs)
  with mock.patch.object(i.shutil,'copy2',side_effect=fail):
   with self.assertRaises(OSError):i.install(self.p,True,False)
  self.assertEqual((self.p/'user.js').read_bytes(),original);self.assertFalse((self.p/i.STATE).exists())
 def test_update_failure_restores_old_files_and_manifest(self):
  i.install(self.p,True,False);before=(self.p/i.STATE/'state.json').read_bytes();wrapper=(self.p/'chrome/userChrome.css').read_bytes()
  def fail(c,*args):
   (c/'aurora/modules/colors.css').unlink();raise OSError('injected update write failure')
  with mock.patch.object(i,'write_theme',side_effect=fail):
   with self.assertRaises(OSError):i.install(self.p,True,False,True)
  self.assertEqual((self.p/i.STATE/'state.json').read_bytes(),before);self.assertEqual((self.p/'chrome/userChrome.css').read_bytes(),wrapper);i.validate(self.p,i.load(self.p))
 def test_duplicate_pref_marker_and_path_escape_refused(self):
  i.install(self.p,True,False);u=self.p/'user.js';u.write_bytes(u.read_bytes()+i.BLOCK.encode())
  with self.assertRaises(ValueError):i.install(self.p,True,False)
  state=i.load(self.p);state['hashes']['../../outside']='0'*64
  with self.assertRaises(ValueError):i.validate(self.p,state)

g=module('audit_glass',root/'tools/gnome_glass.py')
class GlassAuditTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.temp.name)/'backup.json';self.applied=g.desired(['firefox']);self.original={**self.applied,'opacity':'215','blur':'false','whitelist':'[]','dynamic-opacity':'true'};self.state={'schema':g.SCHEMA,'classes':['firefox'],'restored':False,'applied':self.applied,'original':self.original};self.p.write_text(json.dumps(self.state))
 def tearDown(self):self.temp.cleanup()
 def test_incomplete_backup_is_not_already_applied(self):
  self.state['applied']={};self.p.write_text(json.dumps(self.state))
  with mock.patch.object(g,'setkey') as setter:
   with self.assertRaises(ValueError):g.apply(self.p,['firefox'],True)
   with self.assertRaises(ValueError):g.restore(self.p,True)
   setter.assert_not_called()
 def test_restore_failure_rolls_back_to_applied(self):
  actual=self.applied.copy();failed=False
  def setkey(key,value):
   nonlocal failed
   if key=='opacity' and value=='215' and not failed:failed=True;raise OSError('injected settings failure')
   actual[key]=value
  with mock.patch.object(g,'get',side_effect=lambda k:actual[k]),mock.patch.object(g,'setkey',side_effect=setkey):
   with self.assertRaises(OSError):g.restore(self.p,True)
  self.assertEqual(actual,self.applied);self.assertFalse(json.loads(self.p.read_text())['restored'])
 def test_restore_full_original_settings(self):
  actual=self.applied.copy()
  with mock.patch.object(g,'get',side_effect=lambda k:actual[k]),mock.patch.object(g,'setkey',side_effect=lambda k,v:actual.__setitem__(k,v)):g.restore(self.p,True)
  self.assertEqual(actual,self.original);self.assertTrue(json.loads(self.p.read_text())['restored'])
 def test_wrong_scope_and_symlink_backup_refused(self):
  with self.assertRaises(ValueError):g.apply(self.p,['firefox_firefox'],True)
  link=self.p.parent/'alias.json';link.symlink_to(self.p)
  with self.assertRaises(ValueError):g.restore(link,True)

if __name__=='__main__':unittest.main()
