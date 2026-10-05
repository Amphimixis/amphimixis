# syntax=docker/dockerfile:1
# Build from the repository root (needed to COPY amphimixis sources):
#   docker build -f amphimixis-integrations/doxis/Dockerfile -t amphimixis-opencode:latest .

FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash coreutils git curl jq ca-certificates \
        build-essential g++ gcc cmake make ninja-build pkg-config \
        gcc-riscv64-linux-gnu g++-riscv64-linux-gnu \
        qemu-user-hwe \
        qemu-user-binfmt-hwe \
        python3 python3-pip python3-venv \
        rsync sshpass time \
        unzip \
        linux-perf linux-tools-common linux-tools-generic-hwe-26.04 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/libexec/perf-core \
    && curl -fsSL https://raw.githubusercontent.com/torvalds/linux/master/tools/perf/perf-archive.sh -o /usr/libexec/perf-core/perf-archive \
    && chmod +x /usr/libexec/perf-core/perf-archive

RUN qemu-riscv64 --version && riscv64-linux-gnu-g++ --version

RUN curl -fsSL https://bun.sh/install | bash \
    && ln -sf /root/.bun/bin/bun /usr/local/bin/bun
ENV BUN_INSTALL=/root/.bun
ENV PATH="/root/.bun/bin:${PATH}"

RUN curl -fsSL https://opencode.ai/install | bash -s -- --version 1.18.30
ENV PATH="/root/.opencode/bin:${PATH}"

COPY . /opt/amphimixis-repo
RUN pip3 install /opt/amphimixis-repo \
    && rm -rf /opt/amphimixis-repo

RUN amixis opencode install --global

WORKDIR /root/.config/opencode
RUN bun add @opencode-ai/plugin@1.18.30 @opencode-ai/sdk@1.18.30

COPY amphimixis-integrations/doxis/docker-entrypoint.sh /usr/local/bin/amphimixis-entrypoint.sh
RUN chmod +x /usr/local/bin/amphimixis-entrypoint.sh

ENV OPENCODE_DATA_HOME=/root/.local/share/opencode
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/amphimixis-entrypoint.sh"]
