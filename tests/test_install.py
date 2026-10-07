import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"tools"))
import importlib.util, json, os, pathlib, subprocess, tempfile, unittest
from safety import operation_lock
root=pathlib.Path(__file__).resolve().parents[1]
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

class HardeningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.tmp.name);self.p=self.base/'profile';self.p.mkdir();(self.p/'prefs.js').write_text('// synthetic');self.childenv={**os.environ,'PYTHONPATH':str(root/'tools')}
 def tearDown(self):self.tmp.cleanup()
 def child(self,code):
  return subprocess.run([sys.executable,'-c',code,str(self.p)],env=self.childenv,capture_output=True,text=True,timeout=8)
 def test_concurrent_apply_and_preview_refused(self):
  with operation_lock(self.p/'.aurora-firefox.lock',True):
   for apply in ['True','False']:
    r=self.child('import install,pathlib,sys;install.install(pathlib.Path(sys.argv[1]),'+apply+',False)');self.assertNotEqual(r.returncode,0);self.assertIn('Another Aurora operation',r.stderr)
  self.assertFalse((self.p/i.STATE).exists())
 def test_lock_symlink_and_hardlink_refused(self):
  target=self.base/'original';target.write_text('keep');lock=self.p/'.aurora-firefox.lock';lock.symlink_to(target)
  with self.assertRaises(OSError):i.install(self.p,True,False)
  lock.unlink();os.link(target,lock)
  with self.assertRaises(ValueError):i.install(self.p,True,False)
  self.assertEqual(target.read_text(),'keep')
 def test_dryrun_creates_no_files(self):
  before=set(self.p.iterdir());i.install(self.p,False,False);self.assertEqual(set(self.p.iterdir()),before)
 def test_update_staging_failure_keeps_installed_tree(self):
  i.install(self.p,True,False);state=i.load(self.p);original=i.write_theme
  def fail(c,*args):
   original(c,*args);raise OSError('staged build failure')
  with mock.patch.object(i,'write_theme',side_effect=fail):
   with self.assertRaises(OSError):i.install(self.p,True,False,True)
  i.validate(self.p,state);self.assertEqual(i.load(self.p),state)
 def test_update_after_manifest_replace_rolls_back(self):
  i.install(self.p,True,False);before=(self.p/i.STATE/'state.json').read_bytes();atomic=i.atomic;failed=False
  def fail(path,data):
   nonlocal failed
   atomic(path,data)
   if path==self.p/i.STATE/'state.json' and not failed:failed=True;raise OSError('post-replace fsync failure')
  with mock.patch.object(i,'atomic',side_effect=fail):
   with self.assertRaises(OSError):i.install(self.p,True,False,True)
  self.assertEqual((self.p/i.STATE/'state.json').read_bytes(),before);i.validate(self.p,i.load(self.p))
 def test_initial_userjs_post_replace_failure_restores_original(self):
  user=self.p/'user.js';user.write_text('// full original');atomic=i.atomic;failed=False
  def fail(path,data):
   nonlocal failed
   atomic(path,data)
   if path==user and not failed:failed=True;raise OSError('post-replace failure')
  with mock.patch.object(i,'atomic',side_effect=fail):
   with self.assertRaises(OSError):i.install(self.p,True,False)
  self.assertEqual(user.read_text(),'// full original');self.assertFalse((self.p/i.STATE).exists())
 def test_interrupt_during_initial_install_preserves_original(self):
  (self.p/'chrome').mkdir();(self.p/'chrome/userChrome.css').write_text('original')
  r=self.child("import install,pathlib,sys,os;install.write_theme=lambda *args:os._exit(73);install.install(pathlib.Path(sys.argv[1]),True,False)")
  self.assertEqual(r.returncode,73);self.assertEqual((self.p/i.STATE/'original-chrome/userChrome.css').read_text(),'original')
  with self.assertRaisesRegex(ValueError,'Interrupted'):i.install(self.p,True,False)
 def test_interrupt_during_update_preserves_previous_tree(self):
  i.install(self.p,True,False)
  r=self.child("""import install,pathlib,sys,os
p=pathlib.Path(sys.argv[1]);rename=install.os.rename
def stop(src,dst):
 rename(src,dst)
 if pathlib.Path(dst).name=='previous-chrome':os._exit(74)
install.os.rename=stop
install.install(p,True,False,True)
""")
  self.assertEqual(r.returncode,74);d=self.p/i.STATE;journal=json.loads((d/'operation.json').read_text());self.assertTrue((d/journal['transaction']/'previous-chrome/userChrome.css').is_file())
  with self.assertRaisesRegex(ValueError,'Interrupted'):i.uninstall(self.p,True)
 def test_interrupt_during_uninstall_retains_user_edit_snapshot(self):
  i.install(self.p,True,False);u=self.p/'user.js';u.write_bytes(u.read_bytes()+b'// later edit\n');raw=u.read_bytes()
  r=self.child("""import install,pathlib,sys,os
p=pathlib.Path(sys.argv[1]);rename=install.os.rename
def stop(src,dst):
 rename(src,dst)
 if pathlib.Path(dst).name=='removed-chrome':os._exit(75)
install.os.rename=stop
install.uninstall(p,True)
""")
  self.assertEqual(r.returncode,75);self.assertEqual((self.p/i.STATE/'uninstall-user.js').read_bytes(),raw)
  with self.assertRaisesRegex(ValueError,'Interrupted'):i.load(self.p)
 def test_sigterm_rolls_back_synthetic_install(self):
  (self.p/'chrome').mkdir();(self.p/'chrome/userChrome.css').write_text('original')
  r=self.child("import install,pathlib,sys,signal;install.write_theme=lambda *args:signal.raise_signal(signal.SIGTERM);install.install(pathlib.Path(sys.argv[1]),True,False)")
  self.assertNotEqual(r.returncode,0);self.assertEqual((self.p/'chrome/userChrome.css').read_text(),'original');self.assertFalse((self.p/i.STATE).exists())
 def test_nested_theme_symlink_refused_before_digest(self):
  i.install(self.p,True,False);c=self.p/'chrome/aurora';(c/'modules').rename(c/'saved');(c/'modules').symlink_to(c/'saved')
  with mock.patch.object(i,'digest',side_effect=AssertionError('Must not read outside managed tree')):
   with self.assertRaisesRegex(ValueError,'symlink'):i.validate(self.p,i.load(self.p))
 def test_added_empty_directory_is_preserved_and_refused(self):
  i.install(self.p,True,False);personal=self.p/'chrome/aurora/personal';personal.mkdir()
  with self.assertRaisesRegex(ValueError,'directories'):i.install(self.p,True,False,True)
  with self.assertRaises(ValueError):i.uninstall(self.p,True)
  self.assertTrue(personal.is_dir())
 def test_noncanonical_manifest_and_missing_wrapper_refused(self):
  i.install(self.p,True,False);s=i.load(self.p)
  for bad in ['aurora//modules/colors.css','aurora/./modules/colors.css','../elsewhere','/tmp/file']:
   t=json.loads(json.dumps(s));t['hashes'][bad]='0'*64
   with self.assertRaises(ValueError):i.validate(self.p,t)
  del s['hashes']['userChrome.css']
  with self.assertRaises(ValueError):i.validate(self.p,s)
 def test_symlink_state_and_original_userjs_refused(self):
  (self.p/'user.js').write_text('original');i.install(self.p,True,False);d=self.p/i.STATE
  for name in ['state.json','original-user.js']:
   f=d/name;copy=d/('saved-'+name);f.rename(copy);f.symlink_to(copy)
   with self.assertRaises(ValueError):i.uninstall(self.p,True)
   f.unlink();copy.rename(f)
 def test_missing_original_and_wrong_profile_refused(self):
  (self.p/'chrome').mkdir();i.install(self.p,True,False);s=i.load(self.p);s['profile']=str(self.base/'other')
  with self.assertRaises(ValueError):i.validate(self.p,s)
  s=i.load(self.p);(self.p/i.STATE/'original-chrome').rmdir()
  with self.assertRaises(ValueError):i.uninstall(self.p,True)
 def test_original_absolute_link_target_edit_is_preserved_and_refused(self):
  a=self.base/'theme-a';a.mkdir();b=self.base/'theme-b';b.mkdir();(self.p/'chrome').symlink_to(a);i.install(self.p,True,False)
  link=self.p/i.STATE/'original-chrome';link.unlink();link.symlink_to(b)
  with self.assertRaisesRegex(ValueError,'Original absolute'):i.uninstall(self.p,True)
  self.assertEqual(link.resolve(),b);self.assertTrue(a.is_dir())
 def test_source_symlink_refused_before_copy(self):
  source=self.base/'source';(source/'theme').mkdir(parents=True);outside=self.base/'outside';outside.write_text('private');(source/'theme/userChrome.css').symlink_to(outside)
  with mock.patch.object(i,'ROOT',source):
   with self.assertRaisesRegex(ValueError,'Source theme symlink'):i.install(self.p,True,False)
  self.assertFalse((self.p/i.STATE).exists());self.assertEqual(outside.read_text(),'private')
 def test_update_avoids_copying_installed_theme(self):
  i.install(self.p,True,False);original=i.shutil.copytree;calls=[]
  def copy(src,dst,*args,**kwargs):
   calls.append(pathlib.Path(src));return original(src,dst,*args,**kwargs)
  with mock.patch.object(i.shutil,'copytree',side_effect=copy):i.install(self.p,True,False,True)
  self.assertTrue(calls);self.assertTrue(all((root/'theme')==p or (root/'theme') in p.parents for p in calls));i.validate(self.p,i.load(self.p))
 def test_apply_rejects_invalid_mode_and_pref_symlink(self):
  with self.assertRaises(ValueError):i.install(self.p,True,True,True)
  target=self.base/'prefs';target.write_text('// synthetic');(self.p/'prefs.js').unlink();(self.p/'prefs.js').symlink_to(target)
  with self.assertRaises(ValueError):i.profile_path(str(self.p))

if __name__=='__main__': unittest.main()
