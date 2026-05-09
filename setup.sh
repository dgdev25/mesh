#!/usr/bin/env bash

#=============================================================================
# Mesh MCP Server Setup Script
#=============================================================================
# Comprehensive setup script for Mesh - CLI-first MCP server
#
# This script:
# 1. Validates environment (Python, dependencies)
# 2. Detects/installs Gemini CLI and Codex CLI
# 3. Creates .env configuration file
# 4. Runs test suite to verify installation
# 5. Starts the Mesh MCP server
#
# Usage:
#   ./setup.sh                  # Interactive setup
#   ./setup.sh --skip-tests     # Setup without tests
#   ./setup.sh --start-only     # Just start server (assumes setup complete)
#=============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults
SKIP_TESTS=false
START_ONLY=false
MESH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${MESH_DIR}/.env"
OPENROUTER_API_KEY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --start-only)
            START_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-tests     Skip running test suite after setup"
            echo "  --start-only     Skip setup and just start the server"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#=============================================================================
# Helper Functions
#=============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-yes}"
    local response

    while true; do
        if [[ "$default" == "yes" ]]; then
            read -p "$(echo -e "${BLUE}?${NC}  $prompt (Y/n): ")" response
            response="${response:-yes}"
        else
            read -p "$(echo -e "${BLUE}?${NC}  $prompt (y/N): ")" response
            response="${response:-no}"
        fi

        case "$response" in
            [Yy][Ee][Ss]|[Yy])
                return 0
                ;;
            [Nn][Oo]|[Nn])
                return 1
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

#=============================================================================
# Validation Functions
#=============================================================================

check_python() {
    print_step "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi

    local python_version=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)

    if (( major < 3 || (major == 3 && minor < 10) )); then
        print_error "Python 3.10+ required (found $python_version)"
        exit 1
    fi

    print_success "Python $python_version found"
}

check_pip() {
    print_step "Checking pip..."

    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip not found"
        exit 1
    fi

    print_success "pip is available"
}

install_python_dependencies() {
    print_step "Installing Python dependencies..."

    if [[ ! -f "${MESH_DIR}/requirements.txt" ]]; then
        print_error "requirements.txt not found in $MESH_DIR"
        exit 1
    fi

    python3 -m pip install -q -r "${MESH_DIR}/requirements.txt" 2>/dev/null || {
        print_warning "Some dependencies may have failed to install, continuing..."
    }

    print_success "Dependencies installed"
}

check_gemini_cli() {
    if command -v gemini &> /dev/null; then
        return 0
    fi
    return 1
}

check_codex_cli() {
    if command -v codex &> /dev/null; then
        return 0
    fi
    return 1
}

install_gemini_cli() {
    print_step "Installing Gemini CLI..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install google-gemini/gemini-cli/gemini || {
                print_warning "brew install failed, trying pip..."
                python3 -m pip install -q google-gemini-cli || {
                    print_error "Failed to install Gemini CLI"
                    return 1
                }
            }
        else
            print_error "Homebrew not found. Please install from: https://cloud.google.com/docs/generative-ai/install-gemini-cli"
            return 1
        fi
    else
        # Linux
        print_warning "Please install Gemini CLI from: https://cloud.google.com/docs/generative-ai/install-gemini-cli"
        return 1
    fi

    if check_gemini_cli; then
        print_success "Gemini CLI installed"
        return 0
    fi

    return 1
}

install_codex_cli() {
    print_step "Installing Codex CLI..."

    python3 -m pip install -q openai[cli] || {
        print_error "Failed to install Codex CLI via pip"
        return 1
    }

    if check_codex_cli; then
        print_success "Codex CLI installed"
        return 0
    fi

    return 1
}

#=============================================================================
# Configuration Functions
#=============================================================================

create_env_file() {
    print_header "Environment Configuration"

    local gemini_path=""
    local codex_path=""
    local timeout="30"

    # Check for existing CLIs
    if check_gemini_cli; then
        gemini_path=$(command -v gemini)
        print_success "Gemini CLI found at: $gemini_path"
    else
        print_warning "Gemini CLI not found"
        if prompt_yes_no "Install Gemini CLI now?" yes; then
            if install_gemini_cli; then
                gemini_path=$(command -v gemini)
            else
                print_warning "Skipping Gemini CLI (optional)"
            fi
        fi
    fi

    if check_codex_cli; then
        codex_path=$(command -v codex)
        print_success "Codex CLI found at: $codex_path"
    else
        print_warning "Codex CLI not found"
        if prompt_yes_no "Install Codex CLI now?" yes; then
            if install_codex_cli; then
                codex_path=$(command -v codex)
            else
                print_warning "Skipping Codex CLI (optional)"
            fi
        fi
    fi

    # Check if at least one CLI is available
    if [[ -z "$gemini_path" && -z "$codex_path" ]]; then
        print_warning "Neither Gemini CLI nor Codex CLI found"
        print_step "You can set OPENROUTER_API_KEY for fallback instead"
    fi

    # Configure timeout
    echo ""
    print_step "Configure CLI timeout (default: 30 seconds)"
    read -p "$(echo -e "${BLUE}?${NC}  Enter timeout in seconds (or press Enter for default): ")" timeout_input
    if [[ -n "$timeout_input" ]]; then
        timeout="$timeout_input"
    fi

    # Configure OpenRouter API key (optional)
    echo ""
    print_step "Configure OpenRouter fallback (optional)"
    if prompt_yes_no "Set OpenRouter API key for fallback?" no; then
        read -sp "$(echo -e "${BLUE}?${NC}  Enter OpenRouter API key (hidden): ")" OPENROUTER_API_KEY
        echo ""
    fi

    # Create .env file
    print_step "Creating .env file..."
    cat > "${ENV_FILE}" << EOF
# Mesh MCP Server Configuration
# Generated by setup.sh

# CLI Tool Paths (leave empty to use PATH)
GEMINI_CLI_PATH=${gemini_path:-gemini}
CODEX_CLI_PATH=${codex_path:-codex}

# CLI Subprocess Timeout (in seconds)
CLI_TIMEOUT_SECONDS=${timeout}

# OpenRouter API Key (optional fallback)
EOF

    if [[ -n "$OPENROUTER_API_KEY" ]]; then
        echo "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" >> "${ENV_FILE}"
    else
        echo "# OPENROUTER_API_KEY=sk-or-v1-..." >> "${ENV_FILE}"
    fi

    # Add logging level
    cat >> "${ENV_FILE}" << EOF

# Logging Level (DEBUG, INFO, WARNING, ERROR)
LOGLEVEL=INFO
EOF

    print_success "Configuration saved to: $ENV_FILE"
}

#=============================================================================
# Validation Functions
#=============================================================================

validate_environment() {
    print_header "Validating Environment"

    print_step "Running environment validation..."
    python3 << 'PYTHON_SCRIPT'
import os
import sys

# Load .env file if it exists
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

try:
    from utils.env import validate_provider_environment
    validate_provider_environment()
except Exception as e:
    print(f"Error validating environment: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT

    if [[ $? -eq 0 ]]; then
        print_success "Environment validation passed"
    else
        print_error "Environment validation failed"
        return 1
    fi
}

#=============================================================================
# Testing Functions
#=============================================================================

run_tests() {
    print_header "Running Test Suite"

    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Tests skipped (--skip-tests flag)"
        return 0
    fi

    if [[ ! -f "${MESH_DIR}/pytest.ini" ]]; then
        print_warning "pytest.ini not found, tests may not run correctly"
    fi

    print_step "Running Phase 1 tests (CLI execution)..."
    if python3 -m pytest tests/test_providers_cli.py -q 2>/dev/null; then
        print_success "Phase 1 tests passed"
    else
        print_error "Phase 1 tests failed"
        return 1
    fi

    print_step "Running Phase 2 tests (Error handling & fallback)..."
    if python3 -m pytest tests/test_fallback_logic.py -q 2>/dev/null; then
        print_success "Phase 2 tests passed"
    else
        print_error "Phase 2 tests failed"
        return 1
    fi

    print_step "Running Phase 3 tests (Integration)..."
    if python3 -m pytest tests/test_all_tools.py -q 2>/dev/null; then
        print_success "Phase 3 tests passed"
    else
        print_error "Phase 3 tests failed"
        return 1
    fi

    echo ""
    print_success "All test suites passed!"
}

#=============================================================================
# Server Functions
#=============================================================================

start_server() {
    print_header "Starting Mesh MCP Server"

    # Verify .env exists
    if [[ ! -f "${ENV_FILE}" ]]; then
        print_error ".env file not found. Run setup first."
        exit 1
    fi

    # Load environment
    export $(cat "${ENV_FILE}" | grep -v '^#' | xargs)

    print_step "Environment loaded from: $ENV_FILE"
    print_step "Starting server..."
    print_warning "Press Ctrl+C to stop the server"
    echo ""

    cd "${MESH_DIR}"
    python3 server.py
}

#=============================================================================
# Claude Code Integration
#=============================================================================

check_claude_cli() {
    if command -v claude &> /dev/null; then
        return 0
    fi
    return 1
}

add_mcp_to_claude() {
    print_header "Connect to Claude Code"

    if ! check_claude_cli; then
        print_warning "Claude CLI not found (optional - can be installed later)"
        return
    fi

    print_step "Registering Mesh with Claude Code..."

    if claude mcp add mesh --path "${MESH_DIR}" -- python3 server.py 2>/dev/null; then
        print_success "Mesh registered with Claude Code!"
        print_step "Verify connection: claude mcp list"
    else
        print_warning "Could not register Mesh (Claude CLI may need update)"
    fi
}

#=============================================================================
# Main Setup Flow
#=============================================================================

main() {
    # Start-only mode
    if [[ "$START_ONLY" == true ]]; then
        start_server
        return
    fi

    print_header "Mesh MCP Server Setup"
    echo "CLI-first MCP server using Gemini CLI + Codex CLI with OpenRouter fallback"
    echo ""
    echo "Directory: $MESH_DIR"
    echo ""

    # Change to mesh directory
    cd "${MESH_DIR}"

    # Step 1: Python validation
    print_header "Step 1: Environment Validation"
    check_python
    check_pip

    # Step 2: Install dependencies
    print_header "Step 2: Install Dependencies"
    install_python_dependencies

    # Step 3: Create configuration
    create_env_file

    # Step 4: Validate environment
    if ! validate_environment; then
        print_warning "Environment validation had issues, but continuing..."
    fi

    # Step 5: Run tests
    if ! run_tests; then
        print_error "Some tests failed. Please check the output above."
        if ! prompt_yes_no "Continue to server startup despite test failures?" no; then
            exit 1
        fi
    fi

    # Step 6: Connect to Claude Code
    echo ""
    add_mcp_to_claude

    # Step 7: Ask to start server
    echo ""
    if prompt_yes_no "Start Mesh MCP Server now?" yes; then
        start_server
    else
        print_step "To start the server later, run:"
        echo "  cd \"${MESH_DIR}\""
        echo "  ./setup.sh --start-only"
    fi
}

# Run main if script is executed (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
