#!/bin/bash
################################################################################
# test_all_phases.sh
# Master orchestrator for testing all phases (1-6) of Argus
# Runs integration tests + unit tests + reports results
#
# USAGE:
#   Local development (macOS/Linux):
#     $ bash test_all_phases.sh
#
#   Windows users: Use Docker instead (Windows lacks C++ build tools):
#     $ docker compose up -d
#     $ docker compose exec gateway bash test_all_phases.sh
#
#   CI/CD (GitHub Actions): Runs automatically with all dependencies
################################################################################

set -u

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Phase counters
PHASES_PASSED=0
PHASES_FAILED=0
TOTAL_TESTS=0
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

# Print section header
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

# Parse pytest output to extract test counts
parse_pytest_output() {
    local output_file="$1"
    local passed=0
    local failed=0
    local skipped=0

    if [ -f "$output_file" ]; then
        # Look for the summary line like "5 passed in 0.42s"
        passed=$(grep -oE '(\d+) passed' "$output_file" | grep -oE '\d+' | head -1 || echo "0")
        failed=$(grep -oE '(\d+) failed' "$output_file" | grep -oE '\d+' | head -1 || echo "0")
        skipped=$(grep -oE '(\d+) skipped' "$output_file" | grep -oE '\d+' | head -1 || echo "0")
    fi

    echo "$passed $failed $skipped"
}

# Report phase results
report_phase() {
    local phase_name="$1"
    local passed="$2"
    local failed="$3"
    local skipped="$4"

    if [ "$failed" -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC} - $phase_name ($passed tests)"
        PHASES_PASSED=$((PHASES_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC} - $phase_name ($failed failed, $passed passed)"
        PHASES_FAILED=$((PHASES_FAILED + 1))
    fi

    TOTAL_PASS=$((TOTAL_PASS + passed))
    TOTAL_FAIL=$((TOTAL_FAIL + failed))
    TOTAL_SKIP=$((TOTAL_SKIP + skipped))
    TOTAL_TESTS=$((TOTAL_TESTS + passed + failed + skipped))
}

# Main execution
main() {
    # Determine script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"

    print_header "🧪 ARGUS ALL PHASES TEST SUITE (1-6)"
    echo "Working directory: $PWD"
    echo ""

    # Check if running on Windows - if so, direct to Docker
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo -e "${YELLOW}⚠️  Windows detected${NC}"
        echo ""
        echo -e "${CYAN}asyncpg requires C++ build tools (causes hangs/failures on Windows).${NC}"
        echo -e "${CYAN}Recommended: Use Docker:${NC}"
        echo ""
        echo "  \$ docker compose up -d"
        echo "  \$ docker compose exec gateway python -m pytest /app/tests/ -v"
        echo ""
        exit 1
    fi

    # Setup Python path for imports
    export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/gateway:${PYTHONPATH:-}"

    # Create temp directory for logs
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT

    # ========================================================================
    # PHASE 1-2: Integration Tests (Foundation + Performance)
    # ========================================================================
    print_header "PHASE 1-2: Foundation & Performance (Integration)"
    echo "Running: tests/integration/test_full_pipeline.py"

    python -m pytest tests/integration/test_full_pipeline.py -v --tb=short > "$TEMP_DIR/phase12.txt" 2>&1
    PHASE12_EXIT=$?
    cat "$TEMP_DIR/phase12.txt" | tail -20

    read PASSED FAILED SKIPPED <<< "$(parse_pytest_output "$TEMP_DIR/phase12.txt")"
    if [ -z "$PASSED" ]; then PASSED=0; fi
    if [ -z "$FAILED" ]; then FAILED=0; fi
    if [ -z "$SKIPPED" ]; then SKIPPED=0; fi
    if [ "$PHASE12_EXIT" -ne 0 ] && [ "$FAILED" -eq 0 ]; then FAILED=1; fi

    report_phase "Foundation & Performance (1-2)" "$PASSED" "$FAILED" "$SKIPPED"

    # ========================================================================
    # PHASE 3: Unit Tests (Intelligence/Caching Tests)
    # ========================================================================
    print_header "PHASE 3: Intelligence (Caching & Analytics)"
    echo "Running: tests/unit/test_cache.py tests/unit/test_analyzer.py"

    python -m pytest tests/unit/test_cache.py tests/unit/test_analyzer.py \
        -v --tb=short > "$TEMP_DIR/phase3.txt" 2>&1
    PHASE3_EXIT=$?
    cat "$TEMP_DIR/phase3.txt" | tail -20

    read PASSED FAILED SKIPPED <<< "$(parse_pytest_output "$TEMP_DIR/phase3.txt")"
    if [ -z "$PASSED" ]; then PASSED=0; fi
    if [ -z "$FAILED" ]; then FAILED=0; fi
    if [ -z "$SKIPPED" ]; then SKIPPED=0; fi
    if [ "$PHASE3_EXIT" -ne 0 ] && [ "$FAILED" -eq 0 ]; then FAILED=1; fi

    report_phase "Intelligence (Phase 3)" "$PASSED" "$FAILED" "$SKIPPED"

    # ========================================================================
    # PHASE 4: Unit Tests (Observability)
    # ========================================================================
    print_header "PHASE 4: Observability (Metrics & Monitoring)"
    echo "Running: tests/unit/test_metrics.py tests/unit/test_audit.py"

    python -m pytest tests/unit/test_metrics.py tests/unit/test_audit.py \
        -v --tb=short > "$TEMP_DIR/phase4.txt" 2>&1
    PHASE4_EXIT=$?
    cat "$TEMP_DIR/phase4.txt" | tail -20

    read PASSED FAILED SKIPPED <<< "$(parse_pytest_output "$TEMP_DIR/phase4.txt")"
    if [ -z "$PASSED" ]; then PASSED=0; fi
    if [ -z "$FAILED" ]; then FAILED=0; fi
    if [ -z "$SKIPPED" ]; then SKIPPED=0; fi
    if [ "$PHASE4_EXIT" -ne 0 ] && [ "$FAILED" -eq 0 ]; then FAILED=1; fi

    report_phase "Observability (Phase 4)" "$PASSED" "$FAILED" "$SKIPPED"

    # ========================================================================
    # PHASE 5: Integration Tests (Security Hardening)
    # ========================================================================
    print_header "PHASE 5: Security Hardening (Integration)"
    echo "Running: tests/integration/test_phase5.py"

    python -m pytest tests/integration/test_phase5.py -v --tb=short > "$TEMP_DIR/phase5.txt" 2>&1
    PHASE5_EXIT=$?
    cat "$TEMP_DIR/phase5.txt" | tail -20

    read PASSED FAILED SKIPPED <<< "$(parse_pytest_output "$TEMP_DIR/phase5.txt")"
    if [ -z "$PASSED" ]; then PASSED=0; fi
    if [ -z "$FAILED" ]; then FAILED=0; fi
    if [ -z "$SKIPPED" ]; then SKIPPED=0; fi
    if [ "$PHASE5_EXIT" -ne 0 ] && [ "$FAILED" -eq 0 ]; then FAILED=1; fi

    report_phase "Security Hardening (Phase 5)" "$PASSED" "$FAILED" "$SKIPPED"

    # ========================================================================
    # PHASE 6: Unit Tests (AI + Polish)
    # ========================================================================
    print_header "PHASE 6: AI & Polish (Unit Tests)"
    echo "Running: tests/unit/test_ai.py tests/unit/test_validator.py tests/unit/test_encryptor.py"

    python -m pytest tests/unit/test_ai.py tests/unit/test_validator.py tests/unit/test_encryptor.py \
        -v --tb=short > "$TEMP_DIR/phase6.txt" 2>&1
    PHASE6_EXIT=$?
    cat "$TEMP_DIR/phase6.txt" | tail -20

    read PASSED FAILED SKIPPED <<< "$(parse_pytest_output "$TEMP_DIR/phase6.txt")"
    if [ -z "$PASSED" ]; then PASSED=0; fi
    if [ -z "$FAILED" ]; then FAILED=0; fi
    if [ -z "$SKIPPED" ]; then SKIPPED=0; fi
    if [ "$PHASE6_EXIT" -ne 0 ] && [ "$FAILED" -eq 0 ]; then FAILED=1; fi

    report_phase "AI & Polish (Phase 6)" "$PASSED" "$FAILED" "$SKIPPED"

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_header "📊 TEST SUMMARY"

    echo "Phase Results:"
    echo "  Phases Passed:   ${GREEN}$PHASES_PASSED${NC}/6"
    echo "  Phases Failed:   ${RED}$PHASES_FAILED${NC}/6"

    echo ""
    echo "Test Counts:"
    echo "  Total Tests:     $TOTAL_TESTS"
    echo "  ✅ Passed:        ${GREEN}$TOTAL_PASS${NC}"
    echo "  ❌ Failed:        ${RED}$TOTAL_FAIL${NC}"
    echo "  ⊘  Skipped:       ${YELLOW}$TOTAL_SKIP${NC}"

    echo ""
    if [ "$TOTAL_FAIL" -eq 0 ] && [ "$PHASES_FAILED" -eq 0 ]; then
        echo -e "${GREEN}✅ All phases (1-6) passed successfully!${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Some tests failed. See details above.${NC}"
        echo ""
        return 1
    fi
}

# Run main function
main
exit $?
