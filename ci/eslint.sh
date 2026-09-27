#!/bin/bash
BLUE='\e[34m'
NC='\e[0m'

echo -e "${BLUE}Running linter Eslint...${NC}"
mapfile -t files < <(git ls-files ':/*.ts')
bun run eslint "${files[@]}"
