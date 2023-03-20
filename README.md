# Prefetch Acceleration
Work in nydus v2.2.0


## Getting started
Please ensure your `nerdctl` is beyond v0.22 and set the containerd environment for nydus.
Before use this tool we should clear local images and containers.
Please run this tool in root

### Run main.py
```shell
# workdir /path/to
./main.py
```

### Run convert.py and metrics.py

```shell
# workdir /path/to/metrics
# collect metrics (optional use -t 10 to controll the metrics times default once)
python3 metrics.py --config config.yaml
# conver dockerhub image to nydus format 
python3 convert.py --config config.yaml
# you can also use the run.sh
```

This is a example of the config.yaml for metrics.py
```yaml
# the registry of the images
registry: dockerhub.kubekey.local/dfns
# we will use the --insecure-registry if this is True
insecure_registry: True
# the image list which includes the name(:tag) and the arg(option, such as -e  -v) 
images:
 - name: mysql:nydus 
   arg: -e MYSQL_ROOT_PASSWD=123456
 - name: node:nydus
```
### Run bench.py
Please ensure your `nerdctl` is beyond v0.22 and have containerd environment for nydus
```shell
# To run benchmark for nydus snapshotter.
# workdir /path/to/bench
./bench.py --snapshotter nydus --registry=dockerhub.kubekey.local/dfns --insecure-registry --images alpine:nydus
```
## Description
