import importlib.util,pathlib,shutil,tempfile,unittest,zipfile,hashlib,uuid,subprocess,re
from urllib.parse import unquote, urlsplit
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_build',root/'tools/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class ReleaseTests(unittest.TestCase):
 def test_explicit_archive_is_private_data_free_and_deterministic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);marker=uuid.uuid4().hex
   for name in b.PUBLIC_FILES:
    q=p/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,q)
   for name in ['docs/LOCAL-APPLICATION.md','docs/private-user.js','docs/.aurora-firefox/state.json','qa/light-active.png','tools/private-settings.json']:
    q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(marker)
   a=b.build(p);data=pathlib.Path(a['path']).read_bytes();again=b.build(p);self.assertEqual(a['sha256'],again['sha256'])
   with zipfile.ZipFile(a['path']) as z:
    self.assertIsNone(z.testzip());self.assertEqual(set(z.namelist()),{'aurora-firefox/'+n for n in b.PUBLIC_FILES});self.assertFalse(any(marker.encode() in z.read(n) for n in z.namelist()))
   self.assertEqual(hashlib.sha256(data).hexdigest(),a['sha256'])
 def test_release_manifest_and_git_ignore(self):
  ignore=(root/'.gitignore').read_text().splitlines();self.assertIn('/qa/',ignore);self.assertIn('/docs/LOCAL-APPLICATION.md',ignore)
  self.assertFalse(any('LOCAL-APPLICATION' in n or '/qa/' in n for n in b.PUBLIC_FILES))
  public_theme={p.relative_to(root).as_posix() for p in (root/'theme').rglob('*') if p.is_file()};self.assertEqual(public_theme,{n for n in b.PUBLIC_FILES if n.startswith('theme/')})
 def copied_source(self,p):
  for name in b.PUBLIC_FILES:
   q=p/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,q)
 def test_uncompressed_source_is_exact_and_preserves_edits(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.copied_source(p);(p/'qa').mkdir();(p/'qa/private.txt').write_text('private')
   a=b.export_source(p);target=pathlib.Path(a['path']);self.assertEqual({x.relative_to(target).as_posix() for x in target.rglob('*') if x.is_file()},set(b.PUBLIC_FILES));self.assertEqual((target/'install.sh').stat().st_mode & 0o777,0o755);self.assertEqual(b.export_source(p),a)
   (target/'README.md').write_text('user edit')
   with self.assertRaises(ValueError):b.export_source(p)
   self.assertEqual((target/'README.md').read_text(),'user edit')
 def test_public_git_ignore_matches_allowlist(self):
  if not shutil.which('git'):self.skipTest('Optional git not installed')
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.copied_source(p);subprocess.run(['git','init','-q',str(p)],check=True)
   private=['qa/private.png','docs/LOCAL-APPLICATION.md','docs/private.txt','tools/private.json','new-secret.txt','profiles.ini','user.js','theme/modules/private.css']
   names=[*b.PUBLIC_FILES,*private];result=subprocess.run(['git','check-ignore','--no-index','--stdin'],input='\n'.join(names)+'\n',capture_output=True,text=True,cwd=p)
   self.assertEqual(set(result.stdout.splitlines()),set(private),result.stderr)
 def test_symlinked_build_outputs_are_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.copied_source(p);outside=p/'outside';outside.mkdir();(p/'dist').symlink_to(outside)
   with self.assertRaises(ValueError):b.build(p)
   with self.assertRaises(ValueError):b.export_source(p)
   self.assertEqual(list(outside.iterdir()),[])
 def test_readme_images_are_exported_in_zip_and_source(self):
  images=set()
  for readme in ('README.md','README.ko.md'):
   text=(root/readme).read_text()
   targets=re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)',text)
   targets+=re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']',text,re.IGNORECASE)
   self.assertTrue(targets,readme)
   for target in targets:
    url=urlsplit(target)
    if not url.scheme and not url.netloc:
     name=(pathlib.PurePosixPath(readme).parent/unquote(url.path)).as_posix()
     self.assertIn(name,b.PUBLIC_FILES,readme+' image missing from release: '+name)
     images.add(name)
  self.assertTrue(images)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.copied_source(p)
   archive=b.build(p);export=pathlib.Path(b.export_source(p)['path'])
   with zipfile.ZipFile(archive['path']) as z:
    for name in images:
     self.assertEqual(z.read('aurora-firefox/'+name),(root/name).read_bytes())
     self.assertEqual((export/name).read_bytes(),(root/name).read_bytes())
if __name__=='__main__':unittest.main()
