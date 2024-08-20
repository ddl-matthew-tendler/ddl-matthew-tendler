#!/usr/bin/env bash
# This is a bash script for Domino's App publishing feature
# Learn more at https://docs.dominodatalab.com/en/latest/reference/publish/apps/App_publishing_overview.html
 
## Flask example
## This is an example of the code you would need in this bash script for a Python/Flask app
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export FLASK_APP=/mnt/code/run.py
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=8888
