#! /bin/bash

nydusify convert --source docker.io/wordpress:php8.2 --target dockerhub.kubekey.local/dfns/wordpress:batch-256k --batch-size 0x40000 --target-insecure
nydusify convert --source docker.io/wordpress:php8.2 --target dockerhub.kubekey.local/dfns/wordpress:batch-512k --batch-size 0x80000 --target-insecure
nydusify convert --source docker.io/wordpress:php8.2 --target dockerhub.kubekey.local/dfns/wordpress:batch-1024k --batch-size 0x100000 --target-insecure