[English](README.md) | [한국어](README.ko.md)

# Aurora Firefox

Linux Firefox에 차분한 상단 색상과 세 개의 컬러 창 버튼을 더하는 작은 macOS 느낌의 `userChrome.css` 테마입니다. 선택형 실험적 유리 효과를 제공합니다.

**0.2.2-beta.1 · 베타.** Firefox 157 Snap / GNOME 46 / Wayland에서 확인했습니다. Firefox 내부 UI CSS는 버전마다 달라질 수 있어 모든 업데이트 호환성을 보장하지 않습니다. Mozilla 또는 Apple과 관계없는 독립 비공식 프로젝트입니다.

![빈 Firefox 테스트 프로필의 라이트 테마](docs/images/preview-light.png)

*기본 불투명 모드입니다. 주소줄 줄무늬는 Firefox 자동화 표시이며, 이 화면은 데스크톱 블러의 증거가 아닙니다.*

## 기능

- 라이트/다크 색상과 컬러 창 버튼. Firefox의 기본 클릭 영역·버튼 순서·창 명령을 유지합니다.
- 초록 버튼은 Linux 최대화/복원이며, 위치는 기존 데스크톱 배치를 따릅니다.
- 모듈 CSS와 작은 SVG 4개. 외부 폰트나 실행 중 다운로드가 없습니다.
- 안내형 설치, 명시적으로 고르는 프로필 하나, 적용 전 미리보기, 원래 테마 백업.
- 선택형 상단 반투명 효과. 실제 배경 블러는 별도 compositor 설정이 필요합니다.

## 빠른 시작

**Linux, Bash, Python 3.10 이상과 표준 라이브러리**가 필요합니다. root 권한이나 WhiteSur는 필요하지 않으며 의존성을 자동 설치하지 않습니다.

```bash
git clone https://github.com/GYJeong-AI/aurora-firefox.git
cd aurora-firefox
bash install.sh
```

작업 → 배포형태 탐색 범위 → 프로필 하나 → 모드 → 미리보기 → `APPLY` 순서로 진행합니다. 프로필 절대 경로는 Firefox `about:support`에서 확인하세요. 작업을 저장하고 Firefox를 정상 종료한 뒤 적용하고, 이후 직접 다시 실행하세요. 기존 custom CSS가 있으면 별도 테스트 프로필부터 권장합니다.

명시적 명령은 `--apply` 없이 미리보기만 합니다. 예시 경로를 자신의 경로로 바꾸세요.

```bash
bash install.sh --list-profiles
bash install.sh install --profile "/absolute/path/to/profile" --mode opaque
bash install.sh install --profile "/absolute/path/to/profile" --mode opaque --apply
bash install.sh status --profile "/absolute/path/to/profile"
```

원래 `chrome` 폴더/링크를 보존하고 `user.js`에 CSS 허용 설정 `toolkit.legacyUserProfileCustomizations.stylesheets`의 관리 블록을 추가합니다. `prefs.js`는 개인 복구 스냅샷만 저장하고 수정하지 않습니다. 방문기록·쿠키·로그인·세션은 복사하지 않습니다. 프로필 백업은 공개하지 마세요.

## 업데이트·제거·복구

새 소스를 받아 같은 프로필과 명시적 모드로 업데이트합니다.

```bash
git pull --ff-only
bash install.sh update --profile "/absolute/path/to/profile" --mode opaque --apply
```

관리 테마에 예상하지 못한 편집이나 추가 파일이 있으면 변경을 거절합니다. 사용자 편집을 보존한 뒤 충돌을 해결하세요. 제거하면 원래 테마와 링크 형태를 복원하고 `user.js`의 Aurora 관리 블록만 지웁니다.

```bash
bash install.sh uninstall --profile "/absolute/path/to/profile"
bash install.sh uninstall --profile "/absolute/path/to/profile" --apply
```

제거 후에도 CSS 허용 설정이 `prefs.js`에 남을 수 있습니다. 필요하면 `about:config`에서 **그 키 하나만** 설치 전 값으로 되돌리세요. 오래된 `prefs.js` 전체를 덮어쓰지 마세요. 중단 기록이 남으면 [복구 절차](docs/RECOVERY.md)를 읽고 원본을 보존한 뒤 수동 복구하세요.

## 실험적 유리·블러

```bash
bash install.sh update --profile "/absolute/path/to/profile" --mode glass --apply
```

탭·주소줄 표면에 반투명을 적용하고 웹 콘텐츠는 불투명하게 유지합니다. CSS만으로 실제 데스크톱 블러가 생기지는 않습니다. 선택형 GNOME 도구의 새 적용은 **GNOME 46 · Wayland · 이미 ACTIVE인 Blur my Shell 72**로 제한합니다. 기존 GNOME 명령 도구, 개인 백업, 직접 확인한 Firefox window class가 필요합니다. 전체 창 opacity는 255이며 다른 앱을 포함한 기존 블러 범위는 덮어쓰지 않습니다. [블러 설정·원복](docs/BLUR.md)을 보세요.

렌더러 alpha와 UI 동작은 확인했지만 실제 배경 윤곽의 공간적 퍼짐, compositor 팝업/최대화 문제, 통제된 GPU/프레임 비용은 미검증입니다. 유리와 GNOME 도구는 실험 기능입니다. 문제가 있으면 `--mode opaque`로 업데이트하고 compositor 백업을 별도로 복원하세요.

## 지원 범위·검증

| 항목 | 확인 범위 |
| --- | --- |
| Firefox UI | Firefox 157.0 Snap, Ubuntu 24.04.5, GNOME 46 / Mutter 46.2, Wayland, 내장 Light/Dark |
| 프로필 탐색 | 일반·Snap·Flatpak 등록 위치. 각 배포형태의 UI 호환성을 뜻하지 않습니다 |
| 설치기 | 임시 Linux 프로필, 폴더/절대·상대 링크, 업데이트·제거·충돌·중단·rollback |
| GNOME 도구 | GNOME 46 / Blur my Shell 72 / Wayland, 설정 보호와 모의 실패 검사 |

ESR·다른 Firefox 버전·deb/Flatpak UI·X11·다른 데스크톱·확장 버전은 미검증입니다. 별도 OS 제목줄은 내부 버튼 장식을 가릴 수 있습니다. 실제 접근성·혼합 모니터 배율·전체 합성 성능도 미검증입니다. [검증·업데이트 체크리스트](docs/VALIDATION.md) · [배포 한계](docs/RELEASE-READINESS.md).

## 개발·기여

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
python3 tools/build.py --source
python3 tools/build.py
```

테스트는 80개입니다. 빌더는 명시적 공개 목록으로 비압축 소스나 재현 가능한 ZIP을 만듭니다. 편집된 소스 export는 덮어쓰지 않습니다. 공개 파일 추가 시 `PUBLIC_FILES`와 `.gitignore`를 함께 갱신하세요.

이슈·PR을 환영합니다. Firefox/배포형태·데스크톱/compositor·테마 모드·재현 순서·개인정보를 지운 오류를 포함하세요. 프로필·백업·방문 데이터·개인 로그는 첨부하지 마세요. 작은 변경과 테스트를 권장합니다. [설치 상세](docs/INSTALLATION.md) · [기술 검사](docs/RELEASE-AUDIT.md). 상세 문서는 현재 영어입니다.

## 라이선스

프로젝트 코드는 [MIT License](LICENSE)입니다. Firefox·GNOME 등 제품명과 UI의 권리는 각 소유자에게 있습니다. 미리보기는 브라우저 호환성 설명이며 외부 UI의 소유권을 주장하지 않습니다.
