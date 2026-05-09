#!/usr/bin/env bash
# Mesh MCP Server — one-shot setup
#
# Sets up everything needed to run Mesh:
#   1. Verify Python 3.10+
#   2. Create .mesh_venv virtual environment
#   3. Install Python dependencies
#   4. Bootstrap .env from .env.example (you must fill in OPENROUTER_API_KEY)
#   5. Detect gemini/codex CLI providers
#   6. Verify the server module imports cleanly
#   7. Register with Claude Code via `claude mcp add` (if claude CLI is on PATH)
#
# Usage:
#   ./setup.sh           # Full setup (idempotent — safe to re-run)
#   ./setup.sh --check   # Verify state without making changes
#   ./setup.sh --help    # Show this message

set -euo pipefail

# --- self-locate ----------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".mesh_venv"
PY_MIN_MAJOR=3
PY_MIN_MINOR=10

# --- args -----------------------------------------------------------
CHECK_ONLY=false
case "${1:-}" in
    --check) CHECK_ONLY=true ;;
    -h|--help)
        sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
        exit 0
        ;;
    "") ;;
    *)
        echo "Unknown option: $1" >&2
        echo "Run with --help for usage." >&2
        exit 2
        ;;
esac

# --- pretty output --------------------------------------------------
if [[ -t 1 ]]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; BLUE=$'\033[0;34m'; BOLD=$'\033[1m'; NC=$'\033[0m'
else
    RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""
fi
info()   { printf "%s[i]%s %s\n" "$BLUE"   "$NC" "$*"; }
ok()     { printf "%s[+]%s %s\n" "$GREEN"  "$NC" "$*"; }
warn()   { printf "%s[!]%s %s\n" "$YELLOW" "$NC" "$*"; }
err()    { printf "%s[x]%s %s\n" "$RED"    "$NC" "$*"; }
hr()     { printf "\n${BOLD}── %s ──${NC}\n" "$*"; }

# --- 1. Python ------------------------------------------------------
hr "1. Python"
if ! command -v python3 >/dev/null; then
    err "python3 not found. Install Python ${PY_MIN_MAJOR}.${PY_MIN_MINOR}+ first."
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=${PY_VER%.*}
PY_MINOR=${PY_VER#*.}
if (( PY_MAJOR < PY_MIN_MAJOR )) || (( PY_MAJOR == PY_MIN_MAJOR && PY_MINOR < PY_MIN_MINOR )); then
    err "Python ${PY_MIN_MAJOR}.${PY_MIN_MINOR}+ required (found ${PY_VER})"
    exit 1
fi
ok "Python ${PY_VER} ($(command -v python3))"

# --- 2. Virtual environment ----------------------------------------
hr "2. Virtual environment"
VENV_PY="$SCRIPT_DIR/$VENV_DIR/bin/python"
VENV_PIP="$SCRIPT_DIR/$VENV_DIR/bin/pip"
if [[ -x "$VENV_PY" ]]; then
    ok "${VENV_DIR}/ already exists"
else
    if $CHECK_ONLY; then
        warn "${VENV_DIR}/ missing (would create)"
    else
        info "Creating ${VENV_DIR}/..."
        python3 -m venv "$VENV_DIR"
        ok "Created ${VENV_DIR}/"
    fi
fi

# --- 3. Dependencies -----------------------------------------------
hr "3. Dependencies"
if [[ -x "$VENV_PY" ]] && "$VENV_PY" -c "import mcp, openai, pydantic, dotenv" >/dev/null 2>&1; then
    ok "Core dependencies importable"
    DEPS_OK=true
else
    DEPS_OK=false
    if $CHECK_ONLY; then
        warn "Some dependencies missing"
    fi
fi
if ! $CHECK_ONLY && ! $DEPS_OK; then
    info "Installing requirements.txt into ${VENV_DIR}/..."
    "$VENV_PIP" install --upgrade pip --quiet
    "$VENV_PIP" install -r requirements.txt --quiet
    ok "Dependencies installed"
fi

# --- 4. .env --------------------------------------------------------
hr "4. .env"
if [[ -f .env ]]; then
    ok ".env exists"
else
    if $CHECK_ONLY; then
        warn ".env missing (would copy from .env.example)"
    else
        cp .env.example .env
        ok "Created .env from .env.example"
    fi
fi

# --- 5. Provider detection -----------------------------------------
hr "5. Providers"
HAS_PROVIDER=false
if command -v gemini >/dev/null; then
    ok "gemini CLI: $(command -v gemini)"
    HAS_PROVIDER=true
else
    warn "gemini CLI not on PATH"
    info "  install with: npm i -g @google/gemini-cli && gemini login"
fi
if command -v codex >/dev/null; then
    ok "codex CLI: $(command -v codex)"
    HAS_PROVIDER=true
else
    warn "codex CLI not on PATH"
    info "  install with: npm i -g @openai/codex && codex login"
fi
if [[ -f .env ]] && grep -qE '^OPENROUTER_API_KEY=sk-or-' .env; then
    ok "OPENROUTER_API_KEY configured in .env"
    HAS_PROVIDER=true
elif [[ -n "${OPENROUTER_API_KEY:-}" && "${OPENROUTER_API_KEY}" =~ ^sk-or- ]]; then
    ok "OPENROUTER_API_KEY set in environment"
    HAS_PROVIDER=true
else
    warn "OPENROUTER_API_KEY not set (edit .env to add it)"
fi
if ! $HAS_PROVIDER; then
    warn "No providers configured. Mesh will start but tool calls will fail until you:"
    warn "  - install gemini and/or codex CLI, OR"
    warn "  - set OPENROUTER_API_KEY in .env"
fi

# --- 6. Smoke test --------------------------------------------------
hr "6. Smoke test"
if [[ ! -x "$VENV_PY" ]]; then
    warn "venv not built — skipping import smoke (re-run without --check)"
elif "$VENV_PY" -c "import server" >/dev/null 2>&1; then
    ok "server.py imports cleanly"
else
    err "server.py failed to import"
    "$VENV_PY" -c "import server" || true
    exit 1
fi

# --- 7. Claude Code registration -----------------------------------
hr "7. Claude Code registration"
if ! command -v claude >/dev/null; then
    warn "claude CLI not found — skipping automatic registration"
    info "Manual config snippet for any MCP client:"
    cat <<EOF

  {
    "mcpServers": {
      "mesh": {
        "command": "${VENV_PY}",
        "args": ["${SCRIPT_DIR}/server.py"]
      }
    }
  }
EOF
elif $CHECK_ONLY; then
    if claude mcp list 2>/dev/null | grep -qE '^mesh:'; then
        ok "mesh registered with Claude Code"
    else
        warn "mesh not registered with Claude Code"
    fi
else
    if claude mcp list 2>/dev/null | grep -qE '^mesh:'; then
        info "Existing mesh registration found — replacing with venv path"
        claude mcp remove mesh >/dev/null 2>&1 || true
    fi
    claude mcp add mesh -s user -- "$VENV_PY" "$SCRIPT_DIR/server.py" >/dev/null
    ok "Registered mesh with Claude Code (user scope)"
fi

# --- Done -----------------------------------------------------------
hr "Done"
echo
echo "${BOLD}Next steps:${NC}"
if [[ ! -f .env ]] || ! grep -qE '^OPENROUTER_API_KEY=sk-or-' .env; then
    echo "  1. Edit .env and set OPENROUTER_API_KEY=sk-or-... (optional if a CLI is installed)"
fi
echo "  2. Restart Claude Code (or your MCP client) so it picks up the new registration"
echo "  3. Verify by asking Claude: \"use mesh listmodels\""
echo
