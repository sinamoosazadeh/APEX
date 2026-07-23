#!/data/data/com.termux/files/usr/bin/bash
# APEX Termux installation (Phase 14 deployment; docs/DEPLOYMENT.md).
set -euo pipefail

echo "== APEX Termux install =="
pkg update -y
# python-cryptography ships as a Termux package (no Rust build needed).
pkg install -y python git python-cryptography termux-api
pip install --upgrade uv

if [ ! -d "$HOME/APEX" ]; then
  git clone https://github.com/sinamoosazadeh/APEX.git "$HOME/APEX"
fi
cd "$HOME/APEX"
uv sync

echo
echo "Next steps (docs/DEPLOYMENT.md):"
echo "  1. export APEX_MASTER_KEY=<your master key>   # add to ~/.bashrc"
echo "  2. VALUE=<key>    uv run apex secrets set --name toobit_api_key --from-env VALUE"
echo "  3. VALUE=<secret> uv run apex secrets set --name toobit_api_secret --from-env VALUE"
echo "  4. uv run apex secrets seal"
echo "  5. uv run apex secure-check --live"
echo "  6. bash deploy/termux/apex-service.sh   # supervised operational loop"
