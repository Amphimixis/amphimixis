#!/bin/bash
set -e

BLUE='\e[34m'
NC='\e[0m'
CI_PATH=$(dirname "$0")

echo "Running shellcheck..."
shellcheck "${CI_PATH}"/*.sh

"${CI_PATH}"/environment_configure.sh

echo -e "${BLUE}Run CI:${NC}"
"${CI_PATH}"/mdl.sh
"${CI_PATH}"/black.sh
"${CI_PATH}"/ruff.sh
"${CI_PATH}"/mypy.sh
"${CI_PATH}"/pylint.sh
"${CI_PATH}"/eslint.sh
"${CI_PATH}"/pytest.sh
"${CI_PATH}"/bun-tests.sh
