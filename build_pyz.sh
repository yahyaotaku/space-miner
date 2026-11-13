#!/bin/sh
# Rebuilds the single-file SPACE_MINER.pyz executable (any OS with Python 3).
set -e
cd "$(dirname "$0")"
rm -rf build_exe SPACE_MINER.pyz
mkdir -p build_exe
cp -r space_miner build_exe/
rm -rf build_exe/space_miner/__pycache__
cp main.py build_exe/
python3 -m zipapp build_exe -p "#!/usr/bin/env python3" -o SPACE_MINER.pyz -m "main:main" --compress
rm -rf build_exe
chmod +x SPACE_MINER.pyz
echo "Built SPACE_MINER.pyz — run it with: python3 SPACE_MINER.pyz"
