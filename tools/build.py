#!/usr/bin/env python3
"""Deterministic beta ZIP from an explicit public-file manifest."""
import argparse,hashlib,os,pathlib,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION='0.2.2-beta.1'
PUBLIC_FILES=(
 '.gitignore','README.md','README.ko.md','LICENSE','CHANGELOG.md','install.sh',
 'theme/userChrome.css',
 'theme/modules/colors.css','theme/modules/top.css','theme/modules/buttons.css',
 'theme/modules/transparency.css','theme/modules/glass.css',
 'theme/icons/minimize.svg','theme/icons/maximize.svg','theme/icons/restore.svg','theme/icons/close.svg',
 'tools/install.py','tools/gnome_glass.py','tools/build.py','tools/safety.py','tools/setup.py',
 'tests/test_install.py','tests/test_glass.py','tests/test_audit.py','tests/test_release.py','tests/test_hardening.py','tests/test_setup.py',
 'docs/images/preview-light.png','docs/BLUR.md','docs/VALIDATION.md','docs/RELEASE-AUDIT.md','docs/RECOVERY.md','docs/RELEASE-READINESS.md','docs/INSTALLATION.md',
)
def public_inputs(root):
 root=pathlib.Path(root)
 for name in PUBLIC_FILES:
  p=root/name
  if not p.is_file() or any((root/pathlib.Path(*pathlib.PurePosixPath(name).parts[:n])).is_symlink() for n in range(1,len(pathlib.PurePosixPath(name).parts)+1)):
   raise ValueError('Missing or symlinked public release file: '+name)
 return root

def output_dir(root):
 out=root/'dist'
 if out.is_symlink():raise ValueError('Symlinked output directory refused')
 out.mkdir(exist_ok=True);return out

def build(root=ROOT):
 root=public_inputs(root);out=output_dir(root);target=out/('aurora-firefox-'+VERSION+'.zip')
 if target.is_symlink() or (out/'SHA256SUMS').is_symlink():raise ValueError('Symlinked package/checksum target refused')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in sorted(PUBLIC_FILES):
   info=zipfile.ZipInfo('aurora-firefox/'+name,date_time=(2026,10,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100755 if name=='install.sh' else 0o100644)<<16;z.writestr(info,(root/name).read_bytes())
 h=hashlib.sha256(target.read_bytes()).hexdigest();(out/'SHA256SUMS').write_text(h+'  '+target.name+'\n')
 return {'path':str(target),'bytes':target.stat().st_size,'sha256':h}
def export_source(root=ROOT):
 root=public_inputs(root);out=output_dir(root);parent=out/'source';target=parent/'aurora-firefox'
 if parent.is_symlink() or target.is_symlink():raise ValueError('Symlinked source export refused')
 parent.mkdir(exist_ok=True)
 if target.exists():
  actual={x.relative_to(target).as_posix() for x in target.rglob('*') if x.is_file() or x.is_symlink()}
  expected_dirs={str(parent) for n in PUBLIC_FILES for parent in pathlib.PurePosixPath(n).parents if str(parent)!='.'}
  actual_dirs={x.relative_to(target).as_posix() for x in target.rglob('*') if x.is_dir()}
  if actual!=set(PUBLIC_FILES) or actual_dirs!=expected_dirs or any(x.is_symlink() for x in target.rglob('*')) or any((target/n).read_bytes()!=(root/n).read_bytes() for n in PUBLIC_FILES):
   raise ValueError('Source export already differs; preserve edits and move it aside before rebuilding')
 else:
  with tempfile.TemporaryDirectory(prefix='.aurora-source-',dir=parent) as temporary:
   stage=pathlib.Path(temporary)/'aurora-firefox';stage.mkdir()
   for name in PUBLIC_FILES:
    dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/name).read_bytes());dest.chmod(0o755 if name=='install.sh' else 0o644)
   os.rename(stage,target)
 return {'path':str(target),'files':len(PUBLIC_FILES),'version':VERSION}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',action='store_true',help='Export the uncompressed public source tree; never overwrite an edited export.');args=parser.parse_args()
 result=export_source() if args.source else build()
 for key,value in result.items():print(key+':',value)
