#!/bin/bash
BLUE='\e[34m'
NC='\e[0m'

echo -e "${BLUE}Running Markdown linter...${NC}"
mapfile -t files < <(git ls-files ':/*.md' | grep -Ev '(opencode|^docs/reports/)')
mdl -r '~MD007,~MD029,~MD013,~MD033' "${files[@]}"
