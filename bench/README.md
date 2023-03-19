# Bench

## Run Bench
Please ensure your `nerdctl` is beyond v0.22 and have environment for nydus
```shell
# To run benchmark for nydus snapshotter.
./hello.py --engine nerdctl --snapshotter nydus --registry=dockerhub.kubekey.local/dfns --insecure-registry --images alpine:nydus
```