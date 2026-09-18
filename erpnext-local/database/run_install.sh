#!/bin/sh
set -eu
bench --site logistics.localhost execute exec --args '["exec(compile(open(\"/tmp/install_dong_phong_schema.py\").read(),\"install_schema.py\",\"exec\"),dict(__name__=\"__main__\"))"]'
