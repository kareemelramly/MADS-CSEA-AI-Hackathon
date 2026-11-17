#!/usr/bin/env bash
# Prints which kind of Docker is installed (no changes). Share the output with the team.
echo "context: $(docker context show 2>/dev/null)"
echo "server:  $(docker info --format '{{.OperatingSystem}} | runtimes: {{json .Runtimes}}' 2>/dev/null)"
command -v snap >/dev/null && snap list docker 2>/dev/null | tail -1 | sed 's/^/snap:    /'
systemctl --user is-active docker-desktop 2>/dev/null | sed 's/^/desktop: /'
systemctl is-active docker 2>/dev/null | sed 's/^/service: /'
which nvidia-ctk nvidia-container-runtime 2>/dev/null | sed 's/^/toolkit: /'
nvidia-smi -L 2>/dev/null | sed 's/^/gpu:     /'
