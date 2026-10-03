#!/usr/bin/env python3
"""Explicit-profile installer. Standard library only; never discovers profiles."""
import argparse, datetime, hashlib, json, os, pathlib, shutil, sys, tempfile
from safety import regular, sync_dir, sync_tree, operation_lock
VERSION='0.2.2-beta.1'
STATE='.aurora-firefox'
BEGIN='// BEGIN AURORA FIREFOX MANAGED PREF\n'
END='// END AURORA FIREFOX MANAGED PREF\n'
BLOCK=BEGIN+'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n'+END
ROOT=pathlib.Path(__file__).resolve().parents[1]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,data):
    fd,tmp=tempfile.mkstemp(prefix='.aurora-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        if p.exists(): os.chmod(tmp,p.stat().st_mode & 0o777)
        os.replace(tmp,p); sync_dir(p.parent)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def profile_path(value):
    p=pathlib.Path(value).expanduser()
    if not p.is_absolute(): raise ValueError('--profile must be an absolute path')
    if p.is_symlink(): raise ValueError('profile directory symlinks are refused; use its explicit real path')
    if not p.is_dir() or not (p/'prefs.js').is_file(): raise ValueError('profile must already exist and contain prefs.js; use about:support to select it')
    regular(p/'prefs.js')
    return p.resolve()

def load(p):
    d=p/STATE
    if d.is_symlink(): raise ValueError('state directory must not be a symlink')
    if os.path.lexists(d/'operation.json'): raise ValueError('Interrupted operation detected; preserve backup and follow docs/RECOVERY.md')
    regular(d/'state.json')
    return json.loads((d/'state.json').read_text())

def validate(p,s):
    if not isinstance(s,dict) or not isinstance(s.get('links'),dict) or not isinstance(s.get('hashes'),dict):
        raise ValueError('incomplete install manifest; preserve backup for manual recovery')
    if s.get('profile')!=str(p) or any(not isinstance(s.get(k),bool) for k in ['had_chrome','had_userjs','original_css','transparent']):
        raise ValueError('Invalid profile/flags in manifest')
    if 'glass' in s and not isinstance(s['glass'],bool): raise ValueError('Invalid glass flag')
    if s['original_css'] and not s['had_chrome']: raise ValueError('Invalid original CSS flag')
    if not {'userChrome.css','aurora/userChrome.css'}<=set(s['hashes']): raise ValueError('Missing managed wrapper/theme digest')
    d=p/STATE
    if s['had_userjs']: regular(d/'original-user.js')
    identity=s.get('original_chrome')
    if identity is not None:
        if not isinstance(identity,dict) or identity.get('kind') not in {'absent','directory','absolute-link','relative-link'}:raise ValueError('Invalid original chrome identity')
        if s['had_chrome']!=(identity['kind']!='absent'):raise ValueError('Original chrome identity conflicts with flags')
    if s['had_chrome']:
        original=d/'original-chrome'; raw=d/'original-chrome-link'
        if not original.is_dir(): raise ValueError('Original chrome backup is missing; preserve state for manual recovery')
        if os.path.lexists(raw) and (not raw.is_symlink() or pathlib.Path(os.readlink(raw)).is_absolute()):
            raise ValueError('Invalid original relative chrome link')
        if raw.is_symlink() and ((p/os.readlink(raw)).resolve()!=original.resolve()):
            raise ValueError('Original relative link/alias changed')
        if identity is not None:
            kind=identity['kind']
            if kind=='directory' and (original.is_symlink() or os.path.lexists(raw)):raise ValueError('Original chrome directory changed')
            if kind=='absolute-link' and (not original.is_symlink() or os.readlink(original)!=identity.get('target') or os.path.lexists(raw)):raise ValueError('Original absolute chrome link changed')
            if kind=='relative-link' and (not raw.is_symlink() or os.readlink(raw)!=identity.get('target') or not original.is_symlink() or os.readlink(original)!=identity.get('alias')):raise ValueError('Original relative chrome link changed')
    c=p/'chrome'
    if c.is_symlink() or not c.is_dir(): raise ValueError('installed chrome directory changed; refusing to overwrite')
    if any(x.is_symlink() for x in (c/'aurora').rglob('*')): raise ValueError('theme symlinks are refused before any file read')
    if (c/'aurora').is_symlink() or not (c/'aurora').is_dir(): raise ValueError('managed theme must be a real directory')
    for name,target in s['links'].items():
        if not isinstance(name,str) or name in {'.','..','aurora','userChrome.css'} or '/' in name or target!='../.aurora-firefox/original-chrome/'+name:
            raise ValueError('invalid preserved link in state')
    for name,h in s['hashes'].items():
        if not isinstance(name,str): raise ValueError('Invalid managed path type')
        parts=pathlib.PurePosixPath(name).parts
        if not parts or str(pathlib.PurePosixPath(name))!=name or name.startswith('/') or '..' in parts or (name!='userChrome.css' and parts[0]!='aurora'):
            raise ValueError('invalid managed path in state')
        if not isinstance(h,str) or len(h)!=64 or any(x not in '0123456789abcdef' for x in h):
            raise ValueError('invalid managed digest in state')
    expected={'aurora','userChrome.css'}|set(s['links'])
    if set(x.name for x in c.iterdir()) != expected: raise ValueError('chrome contains added/removed files; preserve your edits and use manual recovery')
    for name,target in s['links'].items():
        q=c/name
        if not q.is_symlink() or os.readlink(q)!=target: raise ValueError('preserved chrome link changed: '+name)
    for name,h in s['hashes'].items():
        q=c/name
        if q.is_symlink() or not q.is_file() or digest(q)!=h: raise ValueError('managed file changed: '+name+'; back up edits before update/removal')
    tree={str(x.relative_to(c)) for x in (c/'aurora').rglob('*') if not x.is_dir()}
    if tree != {n for n in s['hashes'] if n.startswith('aurora/')}: raise ValueError('managed theme contains unexpected files')
    expected_dirs={str(parent) for n in s['hashes'] if n.startswith('aurora/') for parent in pathlib.PurePosixPath(n).parents if str(parent) not in {'.','aurora'}}
    actual_dirs={str(x.relative_to(c)) for x in (c/'aurora').rglob('*') if x.is_dir()}
    if actual_dirs!=expected_dirs: raise ValueError('managed theme contains added/removed directories; preserve your edits')
    if any(x.is_symlink() for x in (c/'aurora').rglob('*')): raise ValueError('theme symlinks are refused')

def write_theme(c,old_css,transparent,glass=False):
    target=c/'aurora'
    if target.exists(): shutil.rmtree(target)
    source=ROOT/'theme'
    if source.is_symlink() or any(x.is_symlink() for x in source.rglob('*')): raise ValueError('Source theme symlinks are refused')
    shutil.copytree(source,target); sync_tree(target)
    text='/* Aurora Firefox: preserved original first, Aurora second. */\n'
    if old_css: text+='@import url("../.aurora-firefox/original-chrome/userChrome.css");\n'
    text+='@import url("aurora/userChrome.css");\n'
    if transparent: text+='@import url("aurora/modules/transparency.css");\n'
    if glass: text+='@import url("aurora/modules/glass.css");\n'
    atomic(c/'userChrome.css',text.encode())
    return {str(x.relative_to(c)):digest(x) for x in [c/'userChrome.css',*[x for x in target.rglob('*') if x.is_file()]]}

def preserve_chrome(c,d):
    # Moving a relative symlink changes its resolution. Keep that raw link
    # separately and use an absolute alias only for preserved CSS imports.
    if c.is_symlink() and not pathlib.Path(os.readlink(c)).is_absolute():
        resolved=c.resolve(strict=True)
        alias=d/'original-chrome'
        if os.path.lexists(alias) and (not alias.is_symlink() or alias.resolve()!=resolved):
            raise ValueError('preserved CSS alias changed; refusing overwrite')
        os.rename(c,d/'original-chrome-link')
        if not os.path.lexists(alias): alias.symlink_to(resolved)
    else:
        os.rename(c,d/'original-chrome')

def restore_chrome(c,d):
    raw=d/'original-chrome-link'
    if os.path.lexists(raw):
        os.rename(raw,c)
    else:
        os.rename(d/'original-chrome',c)

def pref_block_valid(raw):
    return all(raw.count(x.encode())==1 for x in (BLOCK,BEGIN,END))

def install(p,apply,transparent,glass=False):
    with operation_lock(p/'.aurora-firefox.lock',apply):
        return _install(p,apply,transparent,glass)

def _install(p,apply,transparent,glass=False):
    d=p/STATE; c=p/'chrome'; u=p/'user.js'
    regular(u,required=False)
    if transparent and glass: raise ValueError('Glass and legacy transparency are mutually exclusive')
    if d.exists():
        s=load(p); validate(p,s)
        if not pref_block_valid(u.read_bytes()): raise ValueError('managed pref block changed; refusing update')
        print('Update explicit profile:',p)
        if not apply: return
        old_state=(d/'state.json').read_bytes()
        transaction=d/('update-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        transaction.mkdir(mode=0o700); stage=transaction/'staged-chrome'; previous=transaction/'previous-chrome'
        stage.mkdir()
        for name,target in s['links'].items(): (stage/name).symlink_to(target)
        # Build before touching the installed tree. Only old chrome is renamed;
        # no redundant full snapshot copy of unchanged theme assets is needed.
        replacement={**s,'hashes':write_theme(stage,s['original_css'],transparent,glass),'version':VERSION,'transparent':transparent,'glass':glass}
        atomic(transaction/'previous-state.json',old_state)
        atomic(transaction/'prepared-state.json',json.dumps(replacement,indent=2).encode())
        atomic(d/'operation.json',json.dumps({'action':'update','transaction':transaction.name}).encode())
        try:
            os.rename(c,previous); sync_dir(p); sync_dir(transaction)
            os.rename(stage,c); sync_dir(p)
            atomic(d/'state.json',json.dumps(replacement,indent=2).encode())
            (d/'operation.json').unlink(); sync_dir(d)
        except BaseException as cause:
            try:
                if previous.exists():
                    if c.exists(): shutil.rmtree(c)
                    os.rename(previous,c)
                atomic(d/'state.json',old_state)
                if (d/'operation.json').exists(): (d/'operation.json').unlink()
                sync_dir(p); sync_dir(d)
            except BaseException:
                raise ValueError('Update rollback incomplete; preserve all backups and follow docs/RECOVERY.md') from cause
            raise
        print('Updated. Original backup retained:',d); return
    if os.path.lexists(d): raise ValueError('unexpected state path')
    if os.path.lexists(c) and not c.is_dir(): raise ValueError('chrome is neither directory nor valid directory symlink')
    if c.is_dir() and os.path.lexists(c/'aurora'): raise ValueError('existing aurora directory; refusing name collision')
    raw=u.read_bytes() if u.exists() else b''
    if BEGIN.encode() in raw or END.encode() in raw: raise ValueError('unexpected managed pref marker')
    print('Install explicit profile:',p)
    print('Preserve chrome:',os.readlink(c) if c.is_symlink() else ('directory' if c.exists() else 'absent'))
    print('Backup chrome/user.js/prefs.js; no prefs.js writes; no running Firefox termination.')
    if not apply: return
    d.mkdir(mode=0o700)
    s={'version':VERSION,'profile':str(p),'created':datetime.datetime.now(datetime.timezone.utc).isoformat(),'had_chrome':os.path.lexists(c),'had_userjs':u.exists(),'original_css':(c/'userChrome.css').is_file(),'links':{},'transparent':transparent,'glass':glass}
    s['original_chrome']={'kind':'relative-link' if c.is_symlink() and not pathlib.Path(os.readlink(c)).is_absolute() else 'absolute-link' if c.is_symlink() else 'directory' if c.exists() else 'absent'}
    if c.is_symlink():
        s['original_chrome']['target']=os.readlink(c)
        if s['original_chrome']['kind']=='relative-link':s['original_chrome']['alias']=str(c.resolve(strict=True))
    userjs_written=False
    try:
        if u.exists(): shutil.copy2(u,d/'original-user.js')
        shutil.copy2(p/'prefs.js',d/'prefs.js.snapshot')
        os.chmod(d/'prefs.js.snapshot',0o600); sync_tree(d)
        atomic(d/'operation.json',json.dumps({'action':'install','had_chrome':s['had_chrome'],'had_userjs':s['had_userjs']}).encode())
        if s['had_chrome']: preserve_chrome(c,d)
        sync_dir(p); sync_dir(d)
        c.mkdir()
        if s['had_chrome']:
            for x in (d/'original-chrome').iterdir():
                if x.name=='userChrome.css': continue
                link='../.aurora-firefox/original-chrome/'+x.name
                (c/x.name).symlink_to(link); s['links'][x.name]=link
        s['hashes']=write_theme(c,s['original_css'],transparent,glass)
        userjs_written=True  # Backups are complete; replace may succeed before fsync raises.
        atomic(u,raw+(b'\n' if raw and not raw.endswith(b'\n') else b'')+BLOCK.encode())
        atomic(d/'prepared-state.json',json.dumps(s,indent=2).encode())
        atomic(d/'state.json',json.dumps(s,indent=2).encode())
        (d/'operation.json').unlink(); sync_dir(d)
    except BaseException:
        if c.is_dir() and not c.is_symlink() and (os.path.lexists(d/'original-chrome') or os.path.lexists(d/'original-chrome-link') or not s['had_chrome']): shutil.rmtree(c)
        if os.path.lexists(d/'original-chrome') or os.path.lexists(d/'original-chrome-link'): restore_chrome(c,d)
        if userjs_written:
            if s['had_userjs']: atomic(u,(d/'original-user.js').read_bytes())
            elif u.exists(): u.unlink()
        shutil.rmtree(d); raise
    print('Installed. Private backup:',d)
    print('Restart Firefox yourself to load CSS; running windows are unchanged.')

def uninstall(p,apply):
    with operation_lock(p/'.aurora-firefox.lock',apply):
        return _uninstall(p,apply)

def _uninstall(p,apply):
    s=load(p); validate(p,s); d=p/STATE; c=p/'chrome'; u=p/'user.js'
    if u.is_symlink() or not u.is_file(): raise ValueError('user.js changed unexpectedly')
    raw=u.read_bytes()
    if not pref_block_valid(raw): raise ValueError('managed pref block changed; refusing removal')
    after=raw.replace(BLOCK.encode(),b'',1)
    original=(d/'original-user.js').read_bytes() if s['had_userjs'] else b''
    if after==original+b'\n' and not original.endswith(b'\n'): after=original
    print('Restore original chrome and remove only managed user.js pref:',p)
    if not apply: return
    archive=p/('.aurora-firefox-backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    old_state=(d/'state.json').read_bytes()
    atomic(d/'uninstall-user.js',raw)
    atomic(d/'operation.json',json.dumps({'action':'uninstall','archive':archive.name}).encode())
    try:
        os.rename(c,d/'removed-chrome'); sync_dir(p); sync_dir(d)
        if s['had_chrome']: restore_chrome(c,d)
        if not s['had_userjs'] and not after: u.unlink()
        elif after==original and s['had_userjs']: atomic(u,original)
        else: atomic(u,after)
        s['uninstalled']=True
        atomic(d/'state.json',json.dumps(s,indent=2).encode())
        os.rename(d,archive); sync_dir(p)
        (archive/'operation.json').unlink(); sync_dir(archive)
    except BaseException:
        if archive.exists() and not d.exists(): os.rename(archive,d)
        if (d/'removed-chrome').exists():
            if s['had_chrome'] and os.path.lexists(c): preserve_chrome(c,d)
            os.rename(d/'removed-chrome',c)
        atomic(u,raw); atomic(d/'state.json',old_state)
        if (d/'operation.json').exists(): (d/'operation.json').unlink()
        sync_dir(p); sync_dir(d); raise
    print('Removed. Backup retained:',archive)
    print('Restart yourself. CSS pref may remain true in prefs.js; restore only that pref in about:config if desired. Never replace live prefs.js with the old snapshot.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['install','uninstall','status']); ap.add_argument('--profile',required=True)
    ap.add_argument('--apply',action='store_true',help='Without this flag, install/uninstall only preview.')
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--transparent',action='store_true',help='Legacy alpha only; no compositor configuration.')
    mode.add_argument('--glass',action='store_true',help='Opt into real-alpha top substrate; configure compositor separately.')
    a=ap.parse_args(); p=profile_path(a.profile)
    if a.action=='install': install(p,a.apply,a.transparent,a.glass)
    elif a.action=='uninstall': uninstall(p,a.apply)
    elif os.path.lexists(p/STATE):
        with operation_lock(p/'.aurora-firefox.lock',False):
            s=load(p); validate(p,s); print(json.dumps({**{k:s[k] for k in ['version','profile','transparent','created']},'glass':s.get('glass',False)},indent=2))
    else: print('Aurora is not installed in this explicit profile.')
if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError) as e: print('Refused:',e,file=sys.stderr); sys.exit(1)
