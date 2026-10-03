#!/usr/bin/env python3
"""Read-only profile discovery and guided calls to the existing safe engines."""
import argparse,configparser,json,os,pathlib,shutil,subprocess,sys
import install as engine
import gnome_glass as glass
from safety import regular
ROOT=pathlib.Path(__file__).resolve().parents[1]
DISTRIBUTIONS={'regular':('.mozilla/firefox','일반'),'snap':('snap/firefox/common/.mozilla/firefox','Snap'),'flatpak':('.var/app/org.mozilla.firefox/.mozilla/firefox','Flatpak')}
class Cancelled(Exception):pass

def safe_text(text):
    if not text or any(ord(c)<32 or ord(c)==127 for c in text):raise ValueError('빈 값이나 제어 문자가 있는 경로/이름은 사용할 수 없습니다.')
    return text

def no_links(path):
    if any(x.is_symlink() for x in [path,*path.parents]):raise ValueError('프로필 경로의 심볼릭 링크를 탐색하지 않습니다. about:support의 실제 절대 경로를 직접 지정하세요.')

def discover(home=None,distribution='all'):
    home=pathlib.Path.home() if home is None else pathlib.Path(home)
    found={};warnings=[]
    for kind,(relative,label) in DISTRIBUTIONS.items():
        if distribution not in {'all',kind}:continue
        base=home/relative;index=base/'profiles.ini'
        if not os.path.lexists(index):continue
        try:
            no_links(index);regular(index)
            if index.stat().st_size>2*1024*1024:raise ValueError('profiles.ini가 너무 큽니다.')
            config=configparser.ConfigParser(interpolation=None);config.read_string(index.read_text(encoding='utf-8-sig'))
            for section in config.sections():
                if not section.startswith('Profile') or not section[7:].isdigit():continue
                try:
                    value=safe_text(config.get(section,'Path'));name=safe_text(config.get(section,'Name',fallback=section))[:160]
                    relative_flag=config.get(section,'IsRelative',fallback='1')
                    if relative_flag not in {'0','1'}:raise ValueError('IsRelative 값은 0 또는 1이어야 합니다.')
                    part=pathlib.Path(value)
                    if relative_flag=='1':
                        if part.is_absolute() or '..' in part.parts:raise ValueError('상대 프로필 경로가 Firefox 폴더 밖으로 나갑니다.')
                        candidate=base/part
                    else:
                        if not part.is_absolute():raise ValueError('절대 프로필 경로가 아닙니다.')
                        candidate=part
                    no_links(candidate);candidate=engine.profile_path(str(candidate))
                    if candidate not in found:found[candidate]={'path':str(candidate),'name':name,'distribution':kind,'label':label}
                    elif kind not in found[candidate]['distribution'].split(','):found[candidate]['distribution']+=','+kind;found[candidate]['label']+=', '+label
                except (OSError,ValueError,configparser.Error) as exc:warnings.append(f'{label} {section}: {exc}')
        except (OSError,ValueError,configparser.Error,UnicodeError) as exc:warnings.append(f'{label}: {exc}')
    return sorted(found.values(),key=lambda x:x['path']),warnings

def prompt(message):
    try:return input(message)
    except EOFError:raise Cancelled()

def choose(message,options):
    while True:
        print(message)
        for key,label,value in options:print(f'  {key}. {label}')
        value=prompt('번호 (0 취소): ').strip()
        if value=='0':raise Cancelled()
        for key,label,result in options:
            if value==key:return result
        print('표시된 번호를 입력하세요.')

def select_profile(distribution):
    entries,warnings=discover(distribution=distribution)
    for warning in warnings:print('탐색 제외:',warning,file=sys.stderr)
    print('profiles.ini의 경로/이름만 읽었습니다. 방문기록·쿠키는 읽지 않습니다.')
    for n,item in enumerate(entries,1):print(f"  {n}. [{item['label']}] {item['name']}\n     {item['path']}")
    print('  M. about:support에서 확인한 절대 경로 직접 입력')
    while True:
        value=prompt('프로필 번호, M 또는 0 취소: ').strip()
        if value=='0':raise Cancelled()
        if value.lower()=='m':
            path=prompt('프로필의 절대 경로 (0 취소): ')
            if path=='0':raise Cancelled()
            try:safe_text(path);return engine.profile_path(path)
            except (OSError,ValueError) as exc:print('경로 오류:',exc);continue
        if value.isdigit() and 1<=int(value)<=len(entries):return pathlib.Path(entries[int(value)-1]['path'])
        print('표시된 프로필 번호 또는 M을 입력하세요.')

def running_hint(profile):
    locked=any(os.path.lexists(profile/name) for name in ['.parentlock','parent.lock','lock'])
    process=False
    try:
        for path in pathlib.Path('/proc').iterdir():
            if not path.name.isdecimal():continue
            try:
                if (path/'comm').read_text().strip() in {'firefox','firefox-bin'}:process=True;break
            except OSError:continue
    except OSError:pass
    return locked or process

def run_engine(action,profile,mode,commit):
    args=[sys.executable,str(ROOT/'tools/install.py'),'install' if action=='update' else action,'--profile',str(profile)]
    if action in {'install','update'}:
        if mode=='glass':args.append('--glass')
        elif mode=='alpha':args.append('--transparent')
    if commit:args.append('--apply')
    subprocess.run(args,check=True)

def run_blur(action,backup,classes,commit):
    args=[sys.executable,str(ROOT/'tools/gnome_glass.py'),action,'--backup',str(backup)]
    for name in classes:args.extend(['--wm-class',name])
    if commit:args.append('--apply')
    subprocess.run(args,check=True)

def blur_plan(profile,backup,classes):
    for command in ['gsettings','gnome-shell','gnome-extensions']:
        if shutil.which(command) is None:raise ValueError(f'{command}가 필요합니다. 자동 설치는 하지 않습니다.')
    glass.desired(classes);glass.preflight()
    if backup.is_symlink():raise ValueError('블러 백업 링크는 사용하지 않습니다.')
    if not backup.is_absolute():raise ValueError('블러 백업은 절대 경로여야 합니다.')
    no_links(backup)
    if backup.parent.exists():
        if not backup.parent.is_dir() or backup.parent.stat().st_mode & 0o077:raise ValueError('블러 백업의 상위 폴더는 mode 700 개인 폴더여야 합니다.')
    elif backup.parent!=profile/engine.STATE:raise ValueError('블러 백업의 상위 폴더가 없습니다.')
    if backup.exists():glass.apply(backup,classes,False)
    else:
        original={key:glass.get(key) for key in glass.desired(classes)};glass.typed(original);glass.scope_ok(original,classes)

def confirm():
    value=prompt('위 대상에 적용하려면 APPLY 입력, 그 외 입력은 취소: ')
    if value!='APPLY':raise Cancelled()

def parser():
    p=argparse.ArgumentParser(description='Aurora 안내형 설치. 자동 의존성 설치/Firefox 종료/원격 다운로드 없음.')
    p.add_argument('action',nargs='?',choices=['install','update','uninstall','status','restore-blur'])
    p.add_argument('--profile',help='about:support에서 확인한 절대 프로필 경로')
    p.add_argument('--distribution',choices=['all',*DISTRIBUTIONS],default='all')
    p.add_argument('--mode',choices=['opaque','glass','alpha'],help='기본 불투명 / 실험적 유리 / legacy alpha')
    group=p.add_mutually_exclusive_group();group.add_argument('--apply',action='store_true');group.add_argument('--dry-run',action='store_true')
    p.add_argument('--list-profiles',action='store_true');p.add_argument('--json',action='store_true',help='--list-profiles 결과만 JSON으로 출력')
    p.add_argument('--gnome-blur',action='store_true',help='별도의 실험적 GNOME 설정 변경에 opt-in')
    p.add_argument('--wm-class',action='append',default=[],help='직접 확인한 exact Firefox class. 여러 번 지정 가능')
    p.add_argument('--blur-backup',help='GNOME 설정 백업 절대 경로. 원복에도 사용')
    return p

def main(argv=None):
    p=parser();a=p.parse_args(argv);interactive=sys.stdin.isatty() and sys.stdout.isatty()
    if a.json and not a.list_profiles:p.error('--json은 --list-profiles와 함께 사용하세요.')
    if a.list_profiles:
        if a.action or a.profile or a.apply or a.mode or a.gnome_blur or a.blur_backup or a.wm_class:p.error('--list-profiles는 읽기 전용 독립 명령입니다.')
        entries,warnings=discover(distribution=a.distribution)
        if a.json:print(json.dumps({'profiles':entries,'warnings':warnings},ensure_ascii=False,indent=2))
        else:
            for n,item in enumerate(entries,1):print(f"{n}. [{item['label']}] {item['name']}\n   {item['path']}")
            if not entries:print('등록된 유효 프로필이 없습니다. Firefox about:support에서 절대 경로를 확인하세요.')
            for warning in warnings:print('탐색 제외:',warning,file=sys.stderr)
        return 0
    if not interactive:
        if not a.action:p.error('비대화형에서는 명시적 action/--profile/--mode를 지정하세요. 예: bash install.sh install --profile "/절대/프로필" --mode opaque (미리보기). --apply를 추가해야 변경합니다.')
        if a.action!='restore-blur' and not a.profile:p.error('비대화형에서는 --profile 절대 경로가 필요합니다.')
        if a.action in {'install','update'} and not a.mode:p.error('비대화형에서는 --mode를 명시하세요. 업데이트에서 모드를 추측하지 않습니다.')
        if a.action=='restore-blur' and not a.blur_backup:p.error('restore-blur에는 --blur-backup 절대 경로가 필요합니다.')
    if a.action is None:a.action=choose('작업 선택',[('1','설치 / 기존 설치 업데이트','install'),('2','테마 제거','uninstall'),('3','설치 상태 확인','status'),('4','GNOME 블러 설정 원복','restore-blur')])
    if a.action=='restore-blur':
        if a.profile or a.mode or a.gnome_blur or a.wm_class:p.error('restore-blur는 프로필 설치와 별개입니다. --blur-backup만 지정하세요.')
        if shutil.which('gsettings') is None:raise ValueError('gsettings가 필요합니다. 자동 설치는 하지 않습니다.')
        value=a.blur_backup or prompt('블러 백업 절대 경로 (0 취소): ')
        if value=='0':raise Cancelled()
        safe_text(value);backup=pathlib.Path(value).expanduser();no_links(backup)
        if not backup.is_absolute():raise ValueError('블러 백업은 절대 경로여야 합니다.')
        run_blur('restore',backup,[],False)
        print('원복 대상 백업:',backup)
        if a.dry_run or (not interactive and not a.apply):return 0
        if interactive:confirm()
        run_blur('restore',backup,[],True);return 0
    if a.action not in {'install','update'} and (a.mode or a.gnome_blur or a.blur_backup or a.wm_class):p.error('모드/블러 적용 인자는 install/update에서만 사용합니다. 블러 원복은 restore-blur를 별도로 실행하세요.')
    if a.action=='status' and a.apply:p.error('status는 읽기 전용입니다.')
    if a.profile:
        safe_text(a.profile);profile=engine.profile_path(a.profile)
    else:
        distribution=a.distribution
        if distribution=='all':distribution=choose('Firefox 배포 형태 선택',[('1','일반 패키지','regular'),('2','Snap','snap'),('3','Flatpak','flatpak'),('4','전체 목록','all')])
        profile=select_profile(distribution)
    if a.action=='update' and not os.path.lexists(profile/engine.STATE):raise ValueError('이 프로필에는 Aurora가 없습니다. 신규 설치는 install을 선택하세요.')
    if a.action in {'install','update'} and a.mode is None:a.mode=choose('테마 모드 선택',[('1','기본 불투명','opaque'),('2','유리: 상단 alpha + 별도 실제 compositor blur (실험적)','glass')])
    if a.mode=='glass' and interactive and not a.dry_run and not a.gnome_blur:
        print('유리 CSS만으로 실제 블러가 생기지는 않습니다. GNOME 설정 변경은 별도 선택입니다.')
        a.gnome_blur=prompt('기존 GNOME 46 / Blur my Shell 72의 실험적 블러도 설정할까요? y 또는 그 외 아니오: ').lower()=='y'
    if a.gnome_blur and a.mode!='glass':p.error('--gnome-blur는 --mode glass와 함께 사용하세요.')
    if (a.blur_backup or a.wm_class) and not a.gnome_blur:p.error('--blur-backup/--wm-class는 --gnome-blur와 함께 사용하세요.')
    backup=None
    if a.gnome_blur:
        if not a.wm_class and interactive:
            print('실제 창 class를 직접 확인하세요. 허용 이름: firefox, firefox_firefox, org.mozilla.firefox. 추측하지 않습니다.')
            value=prompt('확인한 class를 쉼표로 입력 (0 취소): ')
            if value=='0':raise Cancelled()
            a.wm_class=[v.strip() for v in value.split(',')]
        if not a.wm_class:p.error('--gnome-blur에는 직접 확인한 --wm-class가 필요합니다.')
        if not interactive and not a.blur_backup:p.error('비대화형 --gnome-blur에는 --blur-backup 절대 경로가 필요합니다.')
        value=a.blur_backup or str(profile/engine.STATE/('gnome-glass-'+engine.VERSION+'.json'))
        safe_text(value);backup=pathlib.Path(value).expanduser()
    print(f'대상 한 개: {profile}\n작업: {a.action}\n모드: {a.mode or "해당 없음"}',flush=True)
    if a.mode=='glass':print('유리 CSS는 상단 alpha입니다. 실제 블러에는 외부 compositor가 필요하며 GNOME 적용은 별도 선택입니다.',flush=True)
    if running_hint(profile):print('Firefox 프로세스 또는 프로필 잠금이 보입니다. 강제 종료하지 않습니다.',flush=True)
    print('작업을 저장한 뒤 사용자가 정상 종료/재실행해야 새 CSS가 로드됩니다. 탐지 결과만으로 종료 여부를 보장하지 않습니다.',flush=True)
    run_engine(a.action,profile,a.mode,False)
    if a.action=='status':return 0
    if a.gnome_blur:
        blur_plan(profile,backup,a.wm_class)
        print('별도 GNOME 변경: Firefox exact class만, 창 opacity 255, Gaussian sigma 18, blur 활성화.\n웹 본문은 불투명. 실제 합성·GPU 성능은 미검증.\n블러 백업:',backup,'\n대상 class:',', '.join(a.wm_class),flush=True)
    if a.dry_run or (not interactive and not a.apply):print('미리보기 완료. 파일/설정 변경 없음.');return 0
    if interactive:confirm()
    run_engine(a.action,profile,a.mode,True)
    if a.gnome_blur:
        try:run_blur('apply',backup,a.wm_class,True)
        except subprocess.CalledProcessError:
            print('테마 설치는 완료되었으나 별도 GNOME 블러 적용은 실패했습니다. 해당 백업/원복 메시지와 docs/RECOVERY.md를 확인하세요.',file=sys.stderr);return 1
    print('완료. Firefox는 사용자가 정상 재실행하세요. 제거 후에도 CSS 허용 pref가 남을 수 있으므로 README의 한 키 복원 안내를 확인하세요.')
    if a.action=='uninstall':print('GNOME 블러는 별도 설정입니다. 해당 백업으로 restore-blur를 실행해야 원복됩니다. 백업이 프로필 state 안에 있었다면 보존된 archive 경로를 사용하세요.')
    return 0

def cli():
    try:return main()
    except Cancelled:print('취소: 파일/설정 변경 없음.');return 0
    except KeyboardInterrupt:print('\n중단되었습니다. 엔진의 rollback/백업 메시지를 확인하세요.',file=sys.stderr);return 130
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as exc:print('거절/실패:',exc,file=sys.stderr);return 1
if __name__=='__main__':sys.exit(cli())
