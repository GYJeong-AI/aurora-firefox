#!/usr/bin/env bash
set -eu

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.10 이상이 필요합니다. 직접 준비한 뒤 다시 실행하세요. 자동 설치는 하지 않습니다.' >&2
    exit 1
fi
if ! python3 -c 'import sys; import fcntl; sys.exit(0 if sys.platform.startswith("linux") and sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    printf '%s\n' 'Linux 및 Python 3.10 이상이 필요합니다. 자동 설치나 sudo 호출은 하지 않습니다.' >&2
    exit 1
fi
case ${BASH_SOURCE[0]} in
    */*) script_directory=${BASH_SOURCE[0]%/*} ;;
    *) script_directory=. ;;
esac
script_directory=$(CDPATH= cd -- "$script_directory" && pwd -P)
exec python3 "$script_directory/tools/setup.py" "$@"
