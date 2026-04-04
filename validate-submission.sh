#!/usr/bin/env bash
# validate-submission.sh
# Ported from official OpenEnv Hackathon requirements

set -uo pipefail

if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' NC=''
fi

run_with_timeout() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
  else
    "$@" &
    local pid=$!
    ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
  fi
}

portable_mktemp() {
  local prefix="${1:-validate}"
  mktemp "${TMPDIR:-/tmp}/${prefix}-XXXXXX" 2>/dev/null || mktemp
}

echo -e "${BOLD}🏁 STARTING JENKINSOPS VALIDATION...${NC}"

# 1. Mandatory File Presence
FILES=("main.py" "inference.py" "Dockerfile" "requirement.txt" "openenv.yaml")
for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
        echo -e "${GREEN}✅ [OK] Found $f${NC}"
    else
        echo -e "${RED}❌ [FAIL] Missing $f (Disqualification Risk)${NC}"
        exit 1
    fi
done

# 2. Variable Presence
VARS=("API_BASE_URL" "MODEL_NAME" "HF_TOKEN")
for v in "${VARS[@]}"; do
    if [ -n "${!v:-}" ]; then
        echo -e "${GREEN}✅ [OK] Variable $v is set.${NC}"
    else
        echo -e "${YELLOW}⚠️ [WARN] Variable $v is missing (Ensure it's set in Space Env Vars).${NC}"
    fi
done

# 3. Syntax Verification
echo -e "${BOLD}🔍 CHECKING PYTHON SYNTAX...${NC}"
python3 -m py_compile main.py inference.py environment/*.py &>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ [OK] Syntax check passed.${NC}"
else
    echo -e "${RED}❌ [FAIL] Syntax error detected.${NC}"
    exit 1
fi

echo -e "${BOLD}🚀 JENKINSOPS IS READY FOR SUBMISSION!${NC}"
