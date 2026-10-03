import contextlib,importlib.util,io,json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
from unittest import mock
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'))
spec=importlib.util.spec_from_file_location('setup_ux',root/'tools/setup.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class Tty(io.StringIO):
 def isatty(self):return True
class SetupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.tmp.name)/'home';self.home.mkdir();self.p=self.make_profile(self.home/'선택 프로필 공백')
 def tearDown(self):self.tmp.cleanup()
 def make_profile(self,p):p.mkdir(parents=True);(p/'prefs.js').write_text('// synthetic preferences');return p
 def ini(self,kind,rows):
  base=self.home/u.DISTRIBUTIONS[kind][0];base.mkdir(parents=True,exist_ok=True)
  lines=[]
  for n,(name,path,relative) in enumerate(rows):lines.extend([f'[Profile{n}]',f'Name={name}',f'Path={path}',f'IsRelative={relative}','Default=1',''])
  (base/'profiles.ini').write_text('\n'.join(lines));return base
 def tty(self,answers):
  stack=contextlib.ExitStack();stack.enter_context(mock.patch('sys.stdin',Tty()));stack.enter_context(mock.patch('sys.stdout',Tty()));stack.enter_context(mock.patch('builtins.input',side_effect=answers));return stack
 def notty(self):
  stack=contextlib.ExitStack();stack.enter_context(mock.patch('sys.stdin',io.StringIO()));stack.enter_context(mock.patch('sys.stdout',io.StringIO()));return stack
 def command(self,args,project=root,env=None):
  return subprocess.run(['/bin/bash',str(project/'install.sh'),*args],capture_output=True,text=True,env={**os.environ,'HOME':str(self.home),**(env or {})},cwd=project,timeout=20)
 def test_three_distribution_paths_and_multiple_profiles(self):
  for kind in u.DISTRIBUTIONS:
   base=self.home/u.DISTRIBUTIONS[kind][0];self.make_profile(base/'한글 profile');self.make_profile(base/'other');self.ini(kind,[('한국어 % 이름','한글 profile','1'),('other','other','1')])
  profiles,warnings=u.discover(self.home);self.assertEqual(len(profiles),6);self.assertFalse(warnings);self.assertEqual({p['distribution'] for p in profiles},set(u.DISTRIBUTIONS))
 def test_absolute_duplicate_registered_profiles_are_one_target(self):
  for kind in ['regular','snap']:self.ini(kind,[('same',str(self.p),'0'),('again',str(self.p),'0')])
  entries,warnings=u.discover(self.home);self.assertEqual(len(entries),1);self.assertFalse(warnings);self.assertEqual(entries[0]['distribution'],'regular,snap')
 def test_discovery_reads_only_profiles_ini(self):
  self.ini('regular',[('entry',str(self.p),'0')]);read=pathlib.Path.read_text;seen=[]
  def tracked(path,*args,**kwargs):
   self.assertEqual(path.name,'profiles.ini');seen.append(path.name);return read(path,*args,**kwargs)
  with mock.patch.object(pathlib.Path,'read_text',tracked):entries,warnings=u.discover(self.home)
  self.assertEqual(len(entries),1);self.assertEqual(seen,['profiles.ini'])
 def test_symlink_profile_index_and_parent_are_excluded(self):
  base=self.ini('regular',[('alias','alias','1')]);(base/'alias').symlink_to(self.p);self.assertEqual(u.discover(self.home)[0],[])
  index=base/'profiles.ini';saved=base/'saved.ini';index.rename(saved);index.symlink_to(saved);entries,warnings=u.discover(self.home);self.assertFalse(entries);self.assertTrue(warnings)
 def test_invalid_relative_absolute_and_missing_prefs_are_excluded(self):
  base=self.ini('regular',[('escape','../../profile','1'),('abs',str(self.p),'1'),('notabs','relative','0'),('badflag',str(self.p),'yes'),('missing','not-created','1')]);entries,warnings=u.discover(self.home);self.assertEqual(entries,[]);self.assertEqual(len(warnings),5)
 def test_malformed_ini_and_control_characters_refused(self):
  base=self.ini('regular',[]);(base/'profiles.ini').write_text('invalid contents');entries,warnings=u.discover(self.home);self.assertFalse(entries);self.assertTrue(warnings)
  for value in ['', 'bad\x1b[31m', 'bad\nname']:
   with self.assertRaises(ValueError):u.safe_text(value)
 def test_non_tty_without_args_refuses_before_discovery(self):
  with self.notty(),mock.patch.object(u,'discover') as discovery:
   with self.assertRaises(SystemExit) as e:u.main([])
   self.assertEqual(e.exception.code,2);discovery.assert_not_called()
 def test_non_tty_missing_profile_or_mode_refuses(self):
  for args in [['install'],['install','--profile',str(self.p),'--apply'],['restore-blur']]:
   with self.notty():
    with self.assertRaises(SystemExit):u.main(args)
  self.assertFalse((self.p/u.engine.STATE).exists())
 def test_list_profiles_json_readonly(self):
  self.ini('snap',[('select',str(self.p),'0')]);r=self.command(['--list-profiles','--json']);self.assertEqual(r.returncode,0,r.stderr);data=json.loads(r.stdout);self.assertEqual(data['profiles'][0]['path'],str(self.p));self.assertFalse((self.p/u.engine.STATE).exists())
 def test_explicit_preview_has_no_mutation(self):
  before=set(self.p.iterdir());r=self.command(['install','--profile',str(self.p),'--mode','opaque']);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(set(self.p.iterdir()),before);self.assertIn('미리보기 완료',r.stdout)
 def test_explicit_apply_changes_only_selected_profile(self):
  other=self.make_profile(self.home/'other');self.ini('regular',[('selected',str(self.p),'0'),('other',str(other),'0')]);r=self.command(['install','--profile',str(self.p),'--mode','opaque','--apply']);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue((self.p/u.engine.STATE/'state.json').is_file());self.assertEqual(set(x.name for x in other.iterdir()),{'prefs.js'})
 def test_space_unicode_and_shell_metacharacters_are_literal(self):
  profile=self.make_profile(self.home/'공백 $(touch PWNED) `printf BAD` profile');r=self.command(['install','--profile',str(profile),'--mode','opaque','--apply']);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue((profile/'chrome/userChrome.css').is_file());self.assertFalse((root/'PWNED').exists());self.assertFalse((self.home/'PWNED').exists())
 def test_launch_from_project_path_with_unicode_spaces(self):
  project=pathlib.Path(self.tmp.name)/'프로젝트 공백';project.mkdir();shutil.copy2(root/'install.sh',project/'install.sh');shutil.copytree(root/'tools',project/'tools',ignore=shutil.ignore_patterns('__pycache__'));shutil.copytree(root/'theme',project/'theme')
  r=self.command(['install','--profile',str(self.p),'--mode','opaque','--apply'],project=project);self.assertEqual(r.returncode,0,r.stderr)
  r=subprocess.run(['/bin/bash','install.sh','status','--profile',str(self.p)],cwd=project,capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr)
 def test_missing_python_and_unsupported_python_refused(self):
  r=self.command(['--help'],env={'PATH':''});self.assertNotEqual(r.returncode,0);self.assertIn('Python',r.stderr)
  binpath=pathlib.Path(self.tmp.name)/'bin';binpath.mkdir();stub=binpath/'python3';stub.write_text('#!/bin/sh\nexit 1\n');stub.chmod(0o700)
  r=self.command(['--help'],env={'PATH':str(binpath)});self.assertNotEqual(r.returncode,0);self.assertIn('Linux',r.stderr)
 def test_interactive_cancel_at_menu_and_eof_are_unchanged(self):
  for answers in [['9','invalid','0'],[EOFError()]]:
   with self.tty(answers):
    with self.assertRaises(u.Cancelled):u.main([])
   self.assertEqual(set(x.name for x in self.p.iterdir()),{'prefs.js'})
 def test_interactive_multiple_profile_selection_then_cancel(self):
  other=self.make_profile(self.home/'other');self.ini('regular',[('selected',str(self.p),'0'),('other',str(other),'0')])
  entries=u.discover(self.home)[0]
  with self.tty(['1','4','garbage','2','1','cancel']),mock.patch.object(u,'discover',return_value=(entries,[])),mock.patch.object(u,'run_engine') as runner:
   with self.assertRaises(u.Cancelled):u.main([])
   self.assertEqual(runner.call_args.args,('install',pathlib.Path(entries[1]['path']),'opaque',False))
  for p in [self.p,other]:self.assertFalse((p/u.engine.STATE).exists())
 def test_interactive_manual_invalid_path_and_cancel(self):
  with self.tty(['1','1','M','relative','0']),mock.patch.object(u,'discover',return_value=([],[])):
   with self.assertRaises(u.Cancelled):u.main([])
 def test_interactive_explicit_target_requires_apply_confirmation(self):
  args=['install','--profile',str(self.p),'--mode','opaque']
  with self.tty(['no']):
   with self.assertRaises(u.Cancelled):u.main(args)
  self.assertFalse((self.p/u.engine.STATE).exists())
  with self.tty(['APPLY']):self.assertEqual(u.main(args),0)
  self.assertTrue((self.p/u.engine.STATE).exists())
 def test_update_missing_install_refused(self):
  with self.notty():
   with self.assertRaises(ValueError):u.main(['update','--profile',str(self.p),'--mode','opaque','--apply'])
  self.assertFalse((self.p/u.engine.STATE).exists())
 def test_update_remove_and_later_user_edit_preserved(self):
  for args in [['install','--mode','opaque'],['update','--mode','glass']]:
   r=self.command([*args,'--profile',str(self.p),'--apply']);self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('glass.css',(self.p/'chrome/userChrome.css').read_text());user=self.p/'user.js';user.write_bytes(user.read_bytes()+b'// later user edit\n')
  r=self.command(['uninstall','--profile',str(self.p),'--apply']);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(user.read_text(),'// later user edit\n')
 def test_status_and_invalid_option_combinations_readonly(self):
  self.assertEqual(self.command(['status','--profile',str(self.p)]).returncode,0)
  for args in [['status','--apply'],['uninstall','--mode','glass'],['install','--mode','opaque','--gnome-blur'],['install','--mode','glass','--wm-class','firefox']]:
   r=self.command([*args,'--profile',str(self.p)]);self.assertNotEqual(r.returncode,0)
  self.assertFalse((self.p/u.engine.STATE).exists())
 def blur_args(self):return ['install','--profile',str(self.p),'--mode','glass','--gnome-blur','--wm-class','firefox','--blur-backup',str(self.p/u.engine.STATE/'backup.json'),'--apply']
 def test_blur_requires_explicit_classes_and_backup_in_non_tty(self):
  for args in [self.blur_args()[:-3],['install','--profile',str(self.p),'--mode','glass','--gnome-blur','--apply']]:
   with self.notty():
    with self.assertRaises(SystemExit):u.main(args)
  self.assertFalse((self.p/u.engine.STATE).exists())
 def test_unsupported_blur_stops_before_mutation(self):
  with self.notty(),mock.patch.object(u.shutil,'which',return_value='/existing'),mock.patch.object(u.glass,'preflight',side_effect=ValueError('unsupported')):
   with self.assertRaisesRegex(ValueError,'unsupported'):u.main(self.blur_args())
  self.assertFalse((self.p/u.engine.STATE).exists())
 def test_failed_engine_rollback_does_not_invoke_blur(self):
  (self.p/'chrome').mkdir();(self.p/'chrome/userChrome.css').write_text('original')
  def runner(action,profile,mode,commit):u.engine.install(profile,commit,False,mode=='glass')
  with self.notty(),mock.patch.object(u,'run_engine',side_effect=runner),mock.patch.object(u,'blur_plan'),mock.patch.object(u,'run_blur') as blur,mock.patch.object(u.engine,'write_theme',side_effect=OSError('failure')):
   with self.assertRaises(OSError):u.main(self.blur_args())
   blur.assert_not_called()
  self.assertEqual((self.p/'chrome/userChrome.css').read_text(),'original');self.assertFalse((self.p/u.engine.STATE).exists())
 def test_blur_failure_reports_partial_result_preserves_theme(self):
  with self.notty(),mock.patch.object(u,'blur_plan'),mock.patch.object(u,'run_blur',side_effect=subprocess.CalledProcessError(1,['blur'])):
   self.assertEqual(u.main(self.blur_args()),1)
  u.engine.validate(self.p,u.engine.load(self.p))
 def test_restore_blur_independent_and_preview_default(self):
  backup=self.home/'private.json'
  with self.notty(),mock.patch.object(u.shutil,'which',return_value='/existing'),mock.patch.object(u,'run_blur') as blur:
   self.assertEqual(u.main(['restore-blur','--blur-backup',str(backup)]),0);blur.assert_called_once_with('restore',backup,[],False)
  self.assertFalse((self.p/u.engine.STATE).exists())
 def test_profile_lock_running_hint_is_readonly(self):
  lock=self.p/'.parentlock';lock.symlink_to('host:+12345');self.assertTrue(u.running_hint(self.p));self.assertEqual(os.readlink(lock),'host:+12345')
if __name__=='__main__':unittest.main()
