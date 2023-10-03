#!/bin/sh
set -e
mkdir -p tmp/cache tmp/downloads

PYTHON_BINARY=python3
if [ bin/${PYTHON_BINARY} ]; then
  PYTHON_BINARY=bin/${PYTHON_BINARY}
fi

${PYTHON_BINARY} -u -m flask run --host=0.0.0.0
