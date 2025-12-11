#!/usr/bin/env bash
set -euo pipefail

# Configure git user + credential helper for debug auto-pushes from inside the container.

REPO_DIR="${REPO_DIR:-/linux-video-encoder}"

if [ ! -d "${REPO_DIR}/.git" ]; then
  echo "Git repository not found at ${REPO_DIR}."
  echo "Set REPO_DIR to the repo path (default /linux-video-encoder) and re-run."
  exit 1
fi

cd "${REPO_DIR}"

read -rp "Git user.name [AutoEncoder Debug]: " GIT_NAME
GIT_NAME="${GIT_NAME:-AutoEncoder Debug}"
read -rp "Git user.email [autoencoder-debug@localhost]: " GIT_EMAIL
GIT_EMAIL="${GIT_EMAIL:-autoencoder-debug@localhost}"

git config --global user.name "${GIT_NAME}"
git config --global user.email "${GIT_EMAIL}"

read -rp "GitHub username: " GH_USER
if [ -z "${GH_USER}" ]; then
  echo "GitHub username is required."
  exit 1
fi
read -rsp "GitHub Personal Access Token (PAT) with repo or contents:write scope: " GH_PAT
echo
if [ -z "${GH_PAT}" ]; then
  echo "PAT is required."
  exit 1
fi

git config --global credential.helper store
git config --global credential.useHttpPath true
mkdir -p "${HOME}/"
cat <<EOF > "${HOME}/.git-credentials"
https://${GH_USER}:${GH_PAT}@github.com
EOF

echo "Saved credentials to ${HOME}/.git-credentials (plain text)."
echo "Remote 'origin' is: $(git remote get-url origin 2>/dev/null || echo 'unset')."
echo "Debug auto-push will add commits only under debug_uploads/ when enabled."
