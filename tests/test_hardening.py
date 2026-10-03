import importlib.util,json,os,pathlib,subprocess,sys,tempfile,unittest
from unittest import mock
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'))
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
i=module('hardening_install',root/'tools/install.py');g=module('hardening_glass',root/'tools/gnome_glass.py')
from safety import operation_lock
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

class AdapterHardeningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.tmp.name);self.p=self.base/'backup.json';self.target=g.desired(['firefox']);self.original={**self.target,'whitelist':'[]','blur':'false','sigma':'12'};self.actual=self.original.copy()
 def tearDown(self):self.tmp.cleanup()
 def patches(self,setter):
  return mock.patch.multiple(g,preflight=mock.Mock(),get=mock.Mock(side_effect=lambda k:self.actual[k]),setkey=mock.Mock(side_effect=setter))
 def test_apply_readback_failure_rolls_back(self):
  def ignored(key,value):
   if key!='sigma' or value!='18':self.actual[key]=value
  with self.patches(ignored):
   with self.assertRaisesRegex(ValueError,'readback'):g.apply(self.p,['firefox'],True)
  self.assertEqual(self.actual,self.original);self.assertTrue(json.loads(self.p.read_text())['restored'])
 def test_apply_blur_is_enabled_last_and_restore_full(self):
  calls=[]
  def setter(k,v):calls.append((k,v));self.actual[k]=v
  with self.patches(setter):g.apply(self.p,['firefox'],True);g.restore(self.p,True)
  self.assertEqual(calls[0],('blur','false'));self.assertEqual(calls[9],('blur','true'));self.assertEqual(self.actual,self.original)
 def test_silent_rollback_failure_marks_incomplete(self):
  def ignored(key,value):
   if key!='sigma':self.actual[key]=value
   else:self.actual[key]='17'
  with self.patches(ignored):
   with self.assertRaisesRegex(ValueError,'rollback'):g.apply(self.p,['firefox'],True)
  self.assertEqual(json.loads(self.p.read_text())['phase'],'incomplete')
 def test_apply_and_rollback_failure_preserves_original(self):
  def failed(k,v):raise OSError('persistent failure')
  with self.patches(failed):
   with self.assertRaisesRegex(ValueError,'rollback'):g.apply(self.p,['firefox'],True)
  saved=json.loads(self.p.read_text());self.assertEqual(saved['original'],self.original);self.assertEqual(saved['phase'],'incomplete')
  with self.assertRaises(ValueError):g.restore(self.p,True)
 def test_invalid_snapshots_and_scope_refused(self):
  state={'schema':g.SCHEMA,'classes':['firefox'],'restored':False,'phase':'applied','applied':self.target,'original':self.original}
  for key,value in [('opacity','128'),('enable-all','true'),('sigma','999999'),('brightness','nan'),('whitelist',"['unrelated-app']")]:
   s=json.loads(json.dumps(state));s['applied'][key]=value;self.p.write_text(json.dumps(s))
   with mock.patch.object(g,'setkey') as setter:
    with self.assertRaises(ValueError):g.restore(self.p,True)
    setter.assert_not_called()
  for invalid in [None,{},[],['FIREFOX'],[1]]:
   with self.assertRaises(ValueError):g.desired(invalid)
 def test_preflight_refuses_unsupported_without_settings(self):
  schema=self.base/'schemas';schema.mkdir();(self.base/'metadata.json').write_text('{"version":72}')
  with mock.patch.dict(os.environ,{'XDG_SESSION_TYPE':'wayland'}),mock.patch.object(g,'schema_dir',return_value=schema),mock.patch.object(g,'call',return_value='GNOME Shell 47.0'),mock.patch.object(g,'setkey') as setter:
   with self.assertRaisesRegex(ValueError,'matrix'):g.preflight()
   setter.assert_not_called()
 def test_backup_permissions_required(self):
  self.base.chmod(0o755)
  with mock.patch.object(g,'setkey') as setter:
   with self.assertRaisesRegex(ValueError,'private directory'):g.apply(self.p,['firefox'],True)
   setter.assert_not_called()
 def test_global_adapter_lock_blocks_different_backup_names(self):
  with operation_lock(pathlib.Path('/tmp')/('aurora-gnome-glass-'+str(os.getuid())+'.lock'),True):
   with self.assertRaisesRegex(ValueError,'Another'):g.apply(self.p,['firefox'],True)
if __name__=='__main__':unittest.main()
