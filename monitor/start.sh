#!/bin/sh

set -o allexport

if [[ -d /config && -d /config/env ]]; then
  source /config/env/*
fi

exec /usr/bin/python /monitor/main.py "$@"