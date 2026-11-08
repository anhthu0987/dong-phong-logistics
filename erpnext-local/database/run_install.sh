#!/bin/sh
set -eu

echo ">>> [1/2] Running System Schema Installation (install.py)..."
bench --site logistics.localhost execute exec --args '["exec(compile(open(\"/tmp/install.py\").read(),\"install.py\",\"exec\"),dict(__name__=\"__main__\"))"]'

echo ">>> [2/2] Running Demo Data Reset & Seeding (reset_seed.py)..."
bench --site logistics.localhost execute exec --args '["exec(compile(open(\"/tmp/reset_seed.py\").read(),\"reset_seed.py\",\"exec\"),dict(__name__=\"__main__\"))"]'

echo ">>> Cleaning Cache..."
bench --site logistics.localhost clear-cache