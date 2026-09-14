#!/usr/bin/env bash
# Operator entry point. Storage changes are validated by the Python helper.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: ./babylonpiles.sh [command]
  start          Build and start services, keeping managed storage settings
  stop           Stop services (preserve volumes)
  restart        Recreate services to apply current configuration
  status         Show service status and authenticated storage information
  logs           Show recent service logs
  storage-logs   Show recent storage logs
  add-drive      Add an existing directory or block device
  remove-drive   Detach an empty drive; preserve its files and host mount
  auto-mount     Add a block device and a validated persistent mount entry
  scan-drives    Rescan storage through the authenticated API
  test           Run the fixture-only installer tests
  compose ARGS   Run another Compose command with managed storage applied
  help           Show help without requiring Docker
  interactive    Open the menu (default)

The helper requires Python 3.11+ and Docker Compose v2. Storage administration
prompts for an administrator login, or reads BABYLONPILES_TOKEN from the
environment. Files go into a dedicated 'babylonpiles' child of the selected
directory. Original files and disk ownership are preserved. Device mounting
requires Linux host tools and sudo; directory allocation works on macOS too.
EOF
}

helper() { python3 "$ROOT/scripts/manage_storage.py" "$@"; }
compose() { helper compose "$@"; }

start() {
    if [[ ! -f "$ROOT/vendor/EmergencyStorage/emergency_storage.sh" ]]; then
        printf '%s\n' 'Initialize the dependency first: git submodule update --init --recursive' >&2
        return 1
    fi
    compose up --build -d --wait --wait-timeout 120 || return
    printf '%s\n' 'Services are ready: http://localhost:3000' \
        'First installation: ./babylonpiles.sh compose exec backend python -m app.admin create --username admin'
}

storage_change() {
    local action="$1" selection
    if [[ "$action" == remove ]]; then
        helper status || return
        read -r -p 'Drive ID to detach (for example hdd2): ' selection || return
        helper remove "$selection"
    else
        read -r -p 'Existing directory or full block-device path: ' selection || return
        if [[ "$action" == persistent ]]; then
            helper add "$selection" --persistent
        else
            helper add "$selection"
        fi
    fi
}

dispatch() {
    case "$1" in
        start|1) start ;;
        stop|2) compose down ;;
        restart|3) compose up -d --force-recreate --wait --wait-timeout 120 ;;
        status|4) compose ps && helper status ;;
        logs|5) compose logs --tail=50 ;;
        storage-logs|6) compose logs --tail=50 storage ;;
        add-drive|7) storage_change add ;;
        remove-drive|8) storage_change remove ;;
        scan-drives|9) helper scan ;;
        auto-mount|10) storage_change persistent ;;
        test|11) python3 -m unittest discover -s "$ROOT/tests" -p 'test_installer*.py' -v ;;
        compose) shift; compose "$@" ;;
        help|--help|-h) usage ;;
        *) printf 'Unknown command: %s\n' "$1" >&2; return 1 ;;
    esac
}

main() {
    local action="${1:-interactive}" choice
    if [[ "$action" == help || "$action" == --help || "$action" == -h ]]; then
        usage
        return
    fi
    command -v python3 >/dev/null || { printf '%s\n' 'Install Python 3.11 or newer.' >&2; return 1; }
    if [[ "$action" != interactive ]]; then
        dispatch "$@"
        return
    fi
    while true; do
        printf '\n%s\n' 'BabylonPiles: 1=start, 2=stop, 3=restart, 4=status, 5=logs,' \
            '6=storage-logs, 7=add-drive, 8=remove-drive, 9=scan-drives,' \
            '10=auto-mount, 11=test, help, 0=quit. Names also work.'
        read -r -p 'Command: ' choice || return 0
        [[ "$choice" == quit || "$choice" == 0 ]] && return 0
        # A failed command reports an error and returns to the interactive menu.
        dispatch "$choice" || printf '%s\n' 'Command failed; no success was reported.' >&2
    done
}

main "$@"
