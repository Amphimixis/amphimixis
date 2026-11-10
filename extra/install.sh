#!/usr/bin/env bash

set -euo pipefail

#URL=https://github.com/Amphimixis/amphimixis
URL=https://github.com/IMBIGFISH4/amphimixis
LLM_CONFIG=~/.local/share/amphimixis/llm-config

if command -v podman &>/dev/null; then
    CONTAINER_TOOL=podman
elif command -v docker &>/dev/null; then
    CONTAINER_TOOL=docker
else
    echo "error: neither podman nor docker found" >&2
    exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

git clone --depth 1 -b dockered-amphimixis $URL $TMPDIR
pushd $TMPDIR
pwd
$CONTAINER_TOOL build -f amphimixis-integrations/doxis/Dockerfile -t amphimixis-opencode:latest .
mkdir -p ~/.local/share/amphimixis
cp amphimixis-integrations/doxis/data/qemu-riscv64-sample.yml ~/.local/share/amphimixis/input.yml
popd

if [ ! -f "$LLM_CONFIG" ]; then
    cat <<EOF > "$LLM_CONFIG"
# Setup model and opencode/kilocode config
MODEL=llama.cpp/default-model-128k
OPENCODE_CONFIG=~/.config/opencode/opencode.jsonc
EOF
fi

mkdir -p ~/.local/bin
cat <<EOF > ~/.local/bin/amixis-docker.sh
#!/usr/bin/env bash

set -eo pipefail

. ~/.local/share/amphimixis/llm-config

if [ "\$1" = "" ]; then
  echo Usage: "\$0" \<project name\>
  echo
  echo Example: "\$0" "samba"
  exit 0
fi

EXTRA_ARGS=""
if [ "\$OPENCODE_CONFIG" != "" ]; then
    EXTRA_ARGS+="-e OPENCODE_CONFIG=\$OPENCODE_CONFIG -v \$OPENCODE_CONFIG:/etc/opencode/opencode.json:ro "
    if [ "\$MODEL" != "" ]; then
        EXTRA_ARGS+="-e MODEL=\$MODEL "
    fi
fi

mkdir "\$1"
cd "\$1"
cp ~/.local/share/amphimixis/input.yml .
$CONTAINER_TOOL run --rm -v ".:/work" -e PROJECT_NAME="\$1" \$EXTRA_ARGS amphimixis-opencode:latest
EOF
chmod a+x ~/.local/bin/amixis-docker.sh

echo Installation almost complete
echo Setup your provider/model and opencode config at $LLM_CONFIG
echo The free models provided by Anomalyco won\'t work with amphimixis-opencode.
echo If you need to tune build env setup, edit ~/.local/share/amphimixis/input.yml
echo
echo run \"amixis-docker.sh \<project name\>\" to start the analysis
