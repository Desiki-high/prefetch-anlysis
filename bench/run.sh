#! /bin/bash

python3 hello.py --engine nerdctl --snapshotter nydus --registry=$1 --image=$2 --insecure-registry --out-format json --bench-times $3