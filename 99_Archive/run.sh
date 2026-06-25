#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          NEXUS — AI Development Firm                 ║${NC}"
echo -e "${CYAN}║  Renaissance precision · Palantir systems thinking   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Checks ────────────────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 not found. Install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED="3.10"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}Error: Python 3.10+ required (found ${PYTHON_VERSION})${NC}"
    exit 1
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY is not set${NC}"
    echo "  export ANTHROPIC_API_KEY=your_key_here"
    exit 1
fi
echo -e "${GREEN}✓ ANTHROPIC_API_KEY set${NC}"

if [ -n "${SERPAPI_KEY:-}" ]; then
    echo -e "${GREEN}✓ SERPAPI_KEY set (enhanced web search enabled)${NC}"
else
    echo -e "${YELLOW}ℹ SERPAPI_KEY not set (using DuckDuckGo fallback)${NC}"
fi

# ── Virtual environment ────────────────────────────────────────────────────────

if [ ! -d ".venv" ]; then
    echo ""
    echo "Setting up virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    source .venv/bin/activate
fi

# ── Create required directories ───────────────────────────────────────────────

mkdir -p memory outputs/app outputs/docs outputs/reports

# ── Launch ────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}NEXUS is ready. Launching PM...${NC}"
echo ""

# Pass any CLI arguments as the initial briefing
if [ $# -gt 0 ]; then
    python3 agents/pm.py "$*"
else
    python3 agents/pm.py
fi
