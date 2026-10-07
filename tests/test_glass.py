import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"tools"))
import importlib.util,pathlib,unittest,tempfile,json,os
from safety import operation_lock
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
