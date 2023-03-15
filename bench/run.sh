#! /bin/bash

python3 hello.py --engine nerdctl --snapshotter nydus --op run --registry=$1 --image=$2 --insecure-registry --out-format json --bench-times $3
