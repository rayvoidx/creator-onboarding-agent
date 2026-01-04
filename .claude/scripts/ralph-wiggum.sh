#!/bin/bash
# Ralph Wiggum Technique - Claude Code 자율 실행 래퍼
# "I'm helping!" - 반복적으로 자체 검증 및 수정

set -e

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
RALPH_LOG=".claude/hooks/ralph.log"
PID_FILE=".claude/hooks/ralph.pid"

start_ralph() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Ralph Wiggum is already running (PID: $(cat $PID_FILE))"
        exit 1
    fi

    echo "[$(date)] Starting Ralph Wiggum background verification..." | tee -a "$RALPH_LOG"

    # 백그라운드로 실행
    nohup ./.claude/scripts/auto-verify.sh >> "$RALPH_LOG" 2>&1 &
    echo $! > "$PID_FILE"

    echo "Ralph Wiggum started with PID: $(cat $PID_FILE)"
    echo "Logs: tail -f $RALPH_LOG"
}

stop_ralph() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo "Ralph Wiggum stopped (PID: $pid)"
        else
            echo "Ralph Wiggum was not running"
        fi
        rm -f "$PID_FILE"
    else
        echo "No Ralph Wiggum process found"
    fi
}

status_ralph() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Ralph Wiggum is running (PID: $(cat $PID_FILE))"
        echo ""
        echo "Recent log entries:"
        tail -10 "$RALPH_LOG" 2>/dev/null || echo "No logs yet"
    else
        echo "Ralph Wiggum is not running"
    fi
}

case "${1:-start}" in
    start)
        start_ralph
        ;;
    stop)
        stop_ralph
        ;;
    status)
        status_ralph
        ;;
    restart)
        stop_ralph
        sleep 1
        start_ralph
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
