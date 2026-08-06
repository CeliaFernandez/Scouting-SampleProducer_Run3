#!/bin/bash
#
# crab_resubmit_loop.sh
#
# Resubmits every CRAB task under a work area, once per hour, forever.
# Meant to be left running inside tmux so it survives disconnecting from
# lxplus.
#
# Usage:
#   source /cvmfs/cms.cern.ch/crab3/crab.sh        # crab must be in PATH
#   voms-proxy-init --voms cms --valid 192:00      # long-lived proxy
#
#   tmux new -s crab_resubmit
#   ./crab_resubmit_loop.sh [work_area] [interval_seconds]
#   # Ctrl-b d to detach, then close the terminal / disconnect freely.
#   # Reattach later with: tmux attach -t crab_resubmit
#
# Defaults: work_area = ../crab_gensim_rawsim_hlt2024 (relative to this
# script), interval = 3600s (1 hour).

set -uo pipefail

WORK_AREA="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../crab_gensim_rawsim_hlt2024" && pwd)}"
INTERVAL="${2:-3600}"
LOGFILE="${WORK_AREA}/resubmit_loop.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

if ! command -v crab >/dev/null 2>&1; then
    echo "ERROR: 'crab' not found in PATH. Source the CRAB environment first:" >&2
    echo "       source /cvmfs/cms.cern.ch/crab3/crab.sh" >&2
    exit 1
fi

if [[ ! -d "$WORK_AREA" ]]; then
    echo "ERROR: work area not found: $WORK_AREA" >&2
    exit 1
fi

STOP=0
trap 'STOP=1; log "Signal received, stopping after the current round."' SIGINT SIGTERM

log "Starting resubmit loop on $WORK_AREA (every ${INTERVAL}s). Logging to $LOGFILE"

while [[ "$STOP" -eq 0 ]]; do
    if ! voms-proxy-info --exists >/dev/null 2>&1; then
        log "WARNING: no valid voms proxy -- resubmits will fail. Run: voms-proxy-init --voms cms --valid 192:00"
    fi

    mapfile -t TASK_DIRS < <(find "$WORK_AREA" -maxdepth 1 -type d -name 'crab_*' | sort)
    log "Found ${#TASK_DIRS[@]} CRAB task directories."

    for dir in "${TASK_DIRS[@]}"; do
        [[ "$STOP" -eq 1 ]] && break
        name=$(basename "$dir")
        log "  resubmit: $name"
        if crab resubmit "$dir" --maxmemory 5000 >>"$LOGFILE" 2>&1; then
            log "    OK"
        else
            log "    FAILED (see $LOGFILE -- often harmless, e.g. task already COMPLETE or nothing to resubmit)"
        fi
    done

    [[ "$STOP" -eq 1 ]] && break

    log "Round done. Sleeping ${INTERVAL}s..."
    sleep "$INTERVAL" &
    wait $!
done

log "Stopped."
