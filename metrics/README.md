## Run metrics
Please ensure your `nerdctl` is beyond v0.22 and set the containerd environment for nydus and before use this tool we should clear image containers
```shell
# workdir /path/to/metrics
#collect metrics (optional use -t 10 to controll the metrics times default once)
python3 metrics.py -i config.yaml
#conver dockerhub image to nydus format 
python3 convert.py -i image.yaml
```

This is a example of the config.yaml
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
