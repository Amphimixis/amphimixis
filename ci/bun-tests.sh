#!/bin/bash
set -e

BLUE='\e[34m'
NC='\e[0m'

echo -e "${BLUE}Running Bun tests...${NC}"
root=$(git rev-parse --show-toplevel)
cd "$root"/amphimixis-integrations/opencode
bun test
