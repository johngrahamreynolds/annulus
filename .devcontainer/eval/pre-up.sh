#!/usr/bin/env bash
# Dev Containers runs docker compose before the container exists. Compose interpolates
# ${ANNULUS_EVAL_REPO} in volume paths from .devcontainer/.env — not from env_file
# (that only applies inside the running container). Sync eval/.env → ../.env here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVAL_ENV="${ROOT}/.devcontainer/eval/.env"
COMPOSE_ENV="${ROOT}/.devcontainer/.env"

if [[ ! -f "${EVAL_ENV}" ]]; then
  echo "Missing ${EVAL_ENV}" >&2
  echo "Copy .devcontainer/eval/.env.example to .devcontainer/eval/.env and set ANNULUS_EVAL_REPO." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${EVAL_ENV}"

if [[ -z "${ANNULUS_EVAL_REPO:-}" ]]; then
  echo "ANNULUS_EVAL_REPO is unset in ${EVAL_ENV}" >&2
  exit 1
fi

if [[ ! -d "${ANNULUS_EVAL_REPO}" ]]; then
  echo "ANNULUS_EVAL_REPO is not a directory: ${ANNULUS_EVAL_REPO}" >&2
  exit 1
fi

printf 'ANNULUS_EVAL_REPO=%s\n' "${ANNULUS_EVAL_REPO}" > "${COMPOSE_ENV}"
