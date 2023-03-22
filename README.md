# Prefetch Acceleration
Work on:
nydus-snapshotter commit 2ee4efdbef
nydusd, nydus-image, nydusctl, nydusify commit c202e918d4


## Getting started
Please ensure your `nerdctl` is beyond v0.22 and set the containerd environment for nydus.
Before use this tool we should clear local images and containers.
Please run this tool in root

### Run main.py
```shell
# workdir /path/to
./main.py
```

#### result:
| timestamp     | registry                     | repo                               | pull_elapsed(s) | create_elapsed(s) | run_elapsed(s) | total_elapsed(s) |
|---------------|------------------------------|------------------------------------|-----------------|-------------------|----------------|------------------|
| 1679371823127 | dockerhub.kubekey.local/dfns | wordpress:php8.2                   | 90.887442       | 0.394524          | 47.677036      | 138.959002       |
| 1679371930441 | dockerhub.kubekey.local/dfns | wordpress:php8.2_nydus             | 2.707250        | 1.470760          | 102.411740     | 106.589750       |
| 1679372111961 | dockerhub.kubekey.local/dfns | wordpress:php8.2_nydus_prefetchall | 3.341576        | 2.979142          | 175.128998     | 181.449716       |
| 1679372205407 | dockerhub.kubekey.local/dfns | wordpress:php8.2_nydus_prefetch    | 2.879120        | 1.913718          | 88.187928      | 92.980766        |

![](./bench.png)

four benchs for image,the first is oci bech,the second is the nydus without prefetch bench, the third is nydus witch prefech all bench, the latest is nydus prefetch with algorithm bench
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
