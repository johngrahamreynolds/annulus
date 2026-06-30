#!/usr/bin/env bash
#
# Dev Containers runs Docker Compose before the development container exists.
# Docker Compose interpolates variables in bind mounts from `.devcontainer/.env`,
# not from `env_file` entries that are only visible inside the running container.
#
# This script copies ANNULUS_EVAL_REPO from `.devcontainer/eval/.env` to
# `.devcontainer/.env` so it is available during Compose interpolation.
#
# Notes:
#   - This script intentionally does not validate the host path.
#   - Docker is the source of truth for bind mount resolution and already
#     produces clear errors if the path is invalid or inaccessible.
#   - Users should provide a host-native path:
#       macOS/Linux: /Users/... or /home/...
#       Windows:     C:\Users\...
#   - Shell scripts in this repository should always use LF line endings.
#     See `.gitattributes`.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVAL_ENV="${ROOT}/.devcontainer/eval/.env"
COMPOSE_ENV="${ROOT}/.devcontainer/.env"

[[ -f "${EVAL_ENV}" ]]

# shellcheck disable=SC1090
source "${EVAL_ENV}"

: "${ANNULUS_EVAL_REPO:?Must be set}"

printf 'ANNULUS_EVAL_REPO=%s\n' \
    "${ANNULUS_EVAL_REPO}" \
    > "${COMPOSE_ENV}"
