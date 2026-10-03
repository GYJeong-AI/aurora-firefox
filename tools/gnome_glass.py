#!/usr/bin/env python3
"""Opt-in existing Blur my Shell configuration; explicit backup, no installation."""
import argparse,ast,functools,json,math,os,pathlib,subprocess,sys,tempfile
from safety import regular,sync_dir,operation_lock
SCHEMA='org.gnome.shell.extensions.blur-my-shell.applications'
UUID='blur-my-shell@aunetx'
ALLOWED={'firefox','firefox_firefox','org.mozilla.firefox'}

@functools.lru_cache(maxsize=1)
def schema_dir():
 for base in [pathlib.Path.home()/'.local/share/gnome-shell/extensions','/usr/share/gnome-shell/extensions']:
  p=pathlib.Path(base)/UUID/'schemas'
  if (p/'gschemas.compiled').is_file():return p
 raise ValueError('Existing Blur my Shell schema not found; this tool never installs extensions')
def call(args):
 return subprocess.check_output(args,text=True,stderr=subprocess.PIPE,env={**os.environ,'LC_ALL':'C'}).strip()
def get(key):return call(['gsettings','--schemadir',str(schema_dir()),'get',SCHEMA,key])
def setkey(key,value):
 subprocess.run(['gsettings','--schemadir',str(schema_dir()),'set',SCHEMA,key,value],check=True,stderr=subprocess.PIPE)
def desired(classes):
 if not isinstance(classes,list) or not classes or any(not isinstance(x,str) or x not in ALLOWED for x in classes):raise ValueError('Only exact Firefox class names are accepted; no wildcard/application expansion')
 return {'opacity':'255','enable-all':'false','whitelist':json.dumps(sorted(set(classes))),'dynamic-opacity':'false','static-blur':'false','customize':'true','sigma':'18','brightness':'1.0','blur':'true'}
def scope_ok(original,classes):
 import ast
 existing=original['whitelist'].removeprefix('@as ').strip()
 try:existing=ast.literal_eval(existing)
 except (ValueError,SyntaxError):raise ValueError('Invalid whitelist in backup')
 if not isinstance(existing,list) or any(not isinstance(x,str) for x in existing):raise ValueError('Invalid whitelist in backup')
 if original['enable-all']=='true' or any(x.lower() not in {v.lower() for v in classes} for x in existing):
  raise ValueError('Existing application blur includes other apps; refusing shared setting changes')
def preflight():
 if not sys.platform.startswith('linux') or os.environ.get('XDG_SESSION_TYPE')!='wayland':
  raise ValueError('Experimental adapter supports Linux GNOME Wayland only')
 version=call(['gnome-shell','--version'])
 metadata=json.loads((schema_dir().parent/'metadata.json').read_text())
 if not version.split() or not isinstance(metadata,dict) or version.split()[-1].split('.')[0]!='46' or metadata.get('version')!=72:
  raise ValueError('Supported adapter matrix: GNOME 46 / Blur my Shell 72; restore remains available after upgrades')
 if 'State: ACTIVE' not in call(['gnome-extensions','info',UUID]):raise ValueError('Blur my Shell must already be ACTIVE')

def typed(values):
 keys=set(desired(['firefox']))
 if not isinstance(values,dict) or set(values)!=keys or any(not isinstance(v,str) for v in values.values()):
  raise ValueError('Incomplete or invalid settings snapshot')
 result={}
 for k,v in values.items():
  if k in {'blur','customize','enable-all','dynamic-opacity','static-blur'}:
   if v not in {'true','false'}:raise ValueError('Invalid boolean setting in backup')
   result[k]=v=='true'
  elif k=='whitelist':
   try:x=ast.literal_eval(v.removeprefix('@as ').strip())
   except (ValueError,SyntaxError):raise ValueError('Invalid whitelist in backup')
   if not isinstance(x,list) or any(not isinstance(z,str) for z in x):raise ValueError('Invalid whitelist in backup')
   result[k]=sorted(set(x))
  else:
   try:x=float(v) if k=='brightness' else int(v)
   except ValueError:raise ValueError('Invalid numeric setting in backup')
   limit={'opacity':255,'sigma':100,'brightness':1}[k]
   if not math.isfinite(x) or not 0<=x<=limit:raise ValueError('Out-of-range setting in backup')
   result[k]=x
 return result

def save(p,value):
 fd,tmp=tempfile.mkstemp(prefix='.gnome-glass-',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,0o600);os.replace(tmp,p);sync_dir(p.parent)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def read_state(p):
 regular(p)
 state=json.loads(p.read_text())
 if not isinstance(state,dict):raise ValueError('Invalid backup object')
 if state.get('schema')!=SCHEMA or not isinstance(state.get('classes'),list):raise ValueError('Wrong backup schema/classes')
 keys=set(desired(state['classes']))
 typed(state.get('original'))
 scope_ok(state['original'],state['classes'])
 if not isinstance(state.get('restored'),bool):raise ValueError('Missing backup completion state')
 if not state['restored'] and (state.get('phase') in {'pending','incomplete'} or not isinstance(state.get('applied'),dict) or set(state['applied'])!=keys):
  raise ValueError('Incomplete application backup; no automatic changes. Preserve backup and compare current settings with original values.')
 if not state['restored'] and typed(state['applied'])!=typed(desired(state['classes'])):
  raise ValueError('Applied snapshot is outside the Firefox-only fixed blur preset')
 return state

def put_settings(values):
 # Disable first, restore the bounded keys, and enable only after all succeed.
 setkey('blur','false')
 for key,value in values.items():
  if key!='blur':setkey(key,value)
 setkey('blur',values['blur'])

def apply(p,classes,commit):
 with operation_lock(pathlib.Path('/tmp')/('aurora-gnome-glass-'+str(os.getuid())+'.lock'),commit):
  return _apply(p,classes,commit)

def _apply(p,classes,commit):
 regular(p,required=False)
 if not p.is_absolute() or not p.parent.is_dir() or p.parent.stat().st_mode & 0o077:
  raise ValueError('Use an absolute backup path in an existing private directory (mode 700)')
 target=desired(classes)
 if p.exists():
  state=read_state(p)
  if {x.lower() for x in state['classes']}!={x.lower() for x in classes}:raise ValueError('Backup belongs to a different Firefox target scope')
  if state.get('restored'):raise ValueError('Use a new backup filename for a new opt-in session')
  if all(get(k)==v for k,v in state['applied'].items()):print('Already applied; original backup retained:',p);return
  raise ValueError('Existing backup/current settings differ; refusing overwrite')
 preflight()
 original={k:get(k) for k in target};typed(original);scope_ok(original,classes)
 print('Firefox-only dynamic blur; window opacity stays 255. Backup:',p)
 if not commit:return
 if not p.is_absolute() or not p.parent.is_dir():raise ValueError('Use an absolute backup path in an existing private directory')
 state={'schema':SCHEMA,'original':original,'applied':{},'classes':classes,'restored':False,'phase':'pending'}
 save(p,state)
 try:
  put_settings(target)
  state['applied']={k:get(k) for k in target}
  if typed(state['applied'])!=typed(target):raise ValueError('Settings readback differs from the requested preset')
  state['phase']='applied';save(p,state)
 except BaseException:
  try:
   put_settings(original)
   if typed({k:get(k) for k in original})!=typed(original):raise ValueError('Rollback readback mismatch')
  except BaseException:
   state['phase']='incomplete';save(p,state)
   raise ValueError('Apply and rollback could not complete; original backup retained for manual recovery')
  state['restored']=True;state['phase']='restored';save(p,state);raise
 print('Applied:',json.dumps(state['applied']))
def restore(p,commit):
 with operation_lock(pathlib.Path('/tmp')/('aurora-gnome-glass-'+str(os.getuid())+'.lock'),commit):
  return _restore(p,commit)

def _restore(p,commit):
 state=read_state(p)
 if state['restored']:print('Already restored');return
 if not all(get(k)==v for k,v in state['applied'].items()):raise ValueError('User changed application blur settings; refusing to overwrite those changes')
 print('Restore original application blur settings from:',p)
 if not commit:return
 try:
  put_settings(state['original'])
  if typed({k:get(k) for k in state['original']})!=typed(state['original']):raise ValueError('Restore readback differs; rollback will be attempted')
  state['restored']=True;state['phase']='restored';save(p,state)
 except BaseException:
  try:
   put_settings(state['applied'])
   if typed({k:get(k) for k in state['applied']})!=typed(state['applied']):raise ValueError('Rollback readback mismatch')
  except BaseException:
   state['restored']=False;state['phase']='incomplete';save(p,state)
   raise ValueError('Restore and rollback could not complete; preserve the original backup for manual recovery')
  state['restored']=False;state['phase']='applied';save(p,state);raise
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('action',choices=['apply','restore','status']);a.add_argument('--backup',required=True);a.add_argument('--wm-class',action='append',default=[]);a.add_argument('--apply',action='store_true');v=a.parse_args();p=pathlib.Path(v.backup).expanduser()
 if v.action=='apply':apply(p,v.wm_class,v.apply)
 elif v.action=='restore':restore(p,v.apply)
 else:print(json.dumps({k:get(k) for k in desired(['firefox'])},indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as e:print('Refused:',e,file=sys.stderr);sys.exit(1)
