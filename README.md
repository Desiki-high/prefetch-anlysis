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

the result like:
| timestamp     | registry                     | repo                            | pull_elapsed(s) | create_elapsed(s) | run_elapsed(s) | total_elapsed(s) |
|---------------|------------------------------|---------------------------------|-----------------|-------------------|----------------|------------------|
| 1679369853801 | dockerhub.kubekey.local/dfns | alpine:3.17.2                   | 6.48            | 0.33              | 0.42           | 7.23             |
| 1679369858182 | dockerhub.kubekey.local/dfns | alpine:3.17.2_nydus             | 2.14            | 2.44              | 1.55           | 6.13             |
| 1679369864362 | dockerhub.kubekey.local/dfns | alpine:3.17.2_nydus_prefetchall | 2.07            | 3.88              | 0.47           | 6.42             |
| 1679369868065 | dockerhub.kubekey.local/dfns | alpine:3.17.2_nydus_prefetch    | 2.11            | 1.67              | 0.7            | 4.48             |


we do four bench for each oci image,the first is oci bech,the second is the nydus without prefetch bench, the third is nydus witch prefech all bench, the latest is nydus prefetch with algorithm bench
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
