#!/usr/bin/env bash
# install.sh - install the pavese-hub Quadlet into the user Quadlet directory (idempotent).
#
# The Quadlet files in this directory are the source of truth (E10). Run this after a release has
# been merged, never against a dev tree that has not been reviewed.
#
# Usage: deploy/install.sh [--dry-run] [--no-reload] [--restart] [--dest DIR] [-h|--help]
#   --dry-run    print what would be done, change nothing
#   --no-reload  do not run `systemctl --user daemon-reload`
#   --restart    restart the service after installing (default: no restart)
#   --dest DIR   Quadlet directory (default: $QUADLET_DEST_DIR or ~/.config/containers/systemd)
#
# A unit that differs from the installed one is backed up as <unit>.bak-<YYYYmmdd-HHMMSS> in the same
# directory first (Quadlet ignores that suffix). An identical unit is left alone.
set -euo pipefail

UNITS=(pavese-hub.container)
SERVICES=(pavese-hub.service)
SYSTEMCTL_TIMEOUT="${SYSTEMCTL_TIMEOUT:-60}"

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest_dir="${QUADLET_DEST_DIR:-${HOME}/.config/containers/systemd}"
dry_run=0
reload=1
restart=0

usage() { sed -n '2,/^set -/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) dry_run=1 ;;
        --no-reload) reload=0 ;;
        --restart) restart=1 ;;
        --dest)
            [ $# -ge 2 ] || { echo "install: --dest needs a directory" >&2; exit 2; }
            dest_dir="$2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "install: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

run() {
    if [ "$dry_run" -eq 1 ]; then echo "install: [dry-run] $*"; else "$@"; fi
}

for unit in "${UNITS[@]}"; do
    [ -f "${src_dir}/${unit}" ] || { echo "install: missing ${src_dir}/${unit}" >&2; exit 1; }
done

changed=0
run mkdir -p "$dest_dir"
for unit in "${UNITS[@]}"; do
    src="${src_dir}/${unit}"
    dest="${dest_dir}/${unit}"
    if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
        echo "install: ${unit} unchanged"
        continue
    fi
    if [ -f "$dest" ]; then
        backup="${dest}.bak-$(date +%Y%m%d-%H%M%S)"
        echo "install: backing up ${dest} -> ${backup}"
        run cp -p -- "$dest" "$backup"
    fi
    echo "install: installing ${unit} -> ${dest}"
    run install -m 0644 -- "$src" "$dest"
    changed=$((changed + 1))
done

if [ "$reload" -eq 1 ] && [ "$changed" -gt 0 ]; then
    run timeout "$SYSTEMCTL_TIMEOUT" systemctl --user daemon-reload
fi
if [ "$restart" -eq 1 ]; then
    for svc in "${SERVICES[@]}"; do
        run timeout "$SYSTEMCTL_TIMEOUT" systemctl --user restart "$svc"
    done
fi
echo "install: done (${changed} unit(s) changed)"
