#!/bin/bash
# CardMaker App - Reliable startup script
# Usage: bash app/run.sh        (starts everything)
#        bash app/run.sh stop  (stops everything)
#        bash app/run.sh status (reports service status)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Detect Python: prefer anaconda (known good env), then python3, then python
if [ -x "/opt/anaconda3/bin/python" ]; then
    PYTHON="/opt/anaconda3/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
elif command -v python &>/dev/null; then
    PYTHON="$(command -v python)"
else
    echo "Error: no Python interpreter found. Install Python or set PYTHON manually." >&2
    exit 1
fi

# Detect Node / npm
if [ -x "/opt/homebrew/bin/npm" ]; then
    NPM="/opt/homebrew/bin/npm"
    NODE="/opt/homebrew/bin/node"
elif command -v npm &>/dev/null; then
    NPM="$(command -v npm)"
    if command -v node &>/dev/null; then
        NODE="$(command -v node)"
    else
        NODE="$(dirname "$NPM")/node"
    fi
else
    echo "Error: npm not found. Install Node.js or set NPM manually." >&2
    exit 1
fi

export PATH="$(dirname "$NODE"):$(dirname "$PYTHON"):$PATH"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════╗${NC}"
echo -e "${BLUE}║       ${NC}CardMaker App${BLUE}          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════╝${NC}"
echo ""

# --- Status mode ---
if [ "$1" = "status" ]; then
    echo -e "${BLUE}Service status${NC}"
    if curl -s http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
        echo -e "  ComfyUI:  ${GREEN}RUNNING${NC} (http://localhost:8188)"
    else
        echo -e "  ComfyUI:  ${YELLOW}NOT RUNNING${NC}"
    fi
    if curl -s http://127.0.0.1:8000/api/comfyui/status > /dev/null 2>&1; then
        echo -e "  Backend:  ${GREEN}RUNNING${NC} (http://localhost:8000)"
    else
        echo -e "  Backend:  ${YELLOW}NOT RUNNING${NC}"
    fi
    if curl -s http://127.0.0.1:5173/ > /dev/null 2>&1; then
        echo -e "  Frontend: ${GREEN}RUNNING${NC} (http://localhost:5173)"
    else
        echo -e "  Frontend: ${YELLOW}NOT RUNNING${NC}"
    fi
    exit 0
fi

# --- Stop mode ---
if [ "$1" = "stop" ]; then
    echo -e "${YELLOW}Stopping all CardMaker services...${NC}"
    lsof -i :8000 -t 2>/dev/null | xargs kill 2>/dev/null && echo -e "  ${GREEN}Backend stopped${NC}" || echo "  Backend was not running"
    lsof -i :5173 -t 2>/dev/null | xargs kill 2>/dev/null && echo -e "  ${GREEN}Frontend stopped${NC}" || echo "  Frontend was not running"
    echo -e "${GREEN}Done.${NC}"
    exit 0
fi

# --- Kill any stale processes on our ports ---
echo -e "${YELLOW}Cleaning up stale processes...${NC}"
lsof -i :8000 -t 2>/dev/null | xargs kill -9 2>/dev/null
lsof -i :5173 -t 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

# --- Check ComfyUI ---
echo ""
if curl -s http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
    echo -e "  ComfyUI:  ${GREEN}RUNNING${NC}"
else
    echo -e "  ComfyUI:  ${YELLOW}NOT RUNNING${NC} (art generation won't work)"
    echo -e "            Start it separately: cd /Users/timothyjordan/Git/ComfyUI && python main.py"
fi

# --- Start Backend ---
echo ""
echo -e "${YELLOW}Starting backend...${NC}"
cd "$PROJECT_ROOT/app/backend"
$PYTHON -m uvicorn main:app --reload --port 8000 > /tmp/cardmaker-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
for i in {1..15}; do
    if curl -s http://127.0.0.1:8000/api/comfyui/status > /dev/null 2>&1; then
        echo -e "  Backend:  ${GREEN}RUNNING${NC} (http://localhost:8000)"
        break
    fi
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "  Backend:  ${RED}FAILED TO START${NC}"
        echo "  Check logs: cat /tmp/cardmaker-backend.log"
        cat /tmp/cardmaker-backend.log
        exit 1
    fi
    sleep 1
done

# --- Start Frontend ---
echo -e "${YELLOW}Starting frontend...${NC}"
cd "$PROJECT_ROOT/app/frontend"
$NPM run dev > /tmp/cardmaker-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
for i in {1..15}; do
    if curl -s http://127.0.0.1:5173/ > /dev/null 2>&1; then
        echo -e "  Frontend: ${GREEN}RUNNING${NC} (http://localhost:5173)"
        break
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "  Frontend: ${RED}FAILED TO START${NC}"
        echo "  Check logs: cat /tmp/cardmaker-frontend.log"
        cat /tmp/cardmaker-frontend.log
        exit 1
    fi
    sleep 1
done

# --- Open browser ---
echo ""
echo -e "${GREEN}Opening CardMaker in your browser...${NC}"
sleep 1
open http://localhost:5173

echo ""
echo -e "${BLUE}════════════════════════════════${NC}"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop everything"

# Keep script alive so the subshell doesn't exit and kill background jobs
trap 'echo "" && echo -e "${YELLOW}Stopping services...${NC}" && bash "$(dirname "$0")/run.sh" stop && exit 0' INT
wait
