#!/usr/bin/env python3

import yaml

import algorithm.prefetch_list as alg
import convert.convert as cvt
import util

CONFIG = "config.yaml"
PREFETCH_FILE_LIST = "algorithm/out.txt"


def main():
    """
    1. read config file to knows the images:tag and registry and if we need convert to nydus image or not
    2. convert image if we need
    3. collet metrics from nydus image(close prefetch)
    4. analysis the metrics to create the prefetch file list
    5. use the prefetch file list to rebuild the image
    6. bench the oci image use overlayfs,the nydus image without prefetch and the nydus image with prefetch(maybe we need to enable prefetch by change the config.json and restart the snapshotter service)
    """
    cfg = {}
    with open(CONFIG, 'r', encoding='utf-8') as f:
        try:
            cfg = yaml.load(stream=f, Loader=yaml.FullLoader)
        except Exception as inst:
            print('error reading config file')
            print(inst)
            exit(-1)
    # convert image
    for image in cfg["images"]:
        if cfg["convert"]:
            convert(cfg, image)
    util.clean_nerdctl()
    # collect metrics, get prefetch list , rebuild  image , bench
    for image in cfg["images"]:
        if cfg["convert"]:
            convert(cfg, image)
    # _ = alg.get_prefetch_list('metrics/data/wordpress:nydus/2023-03-18-14:44:55.csv', 'metrics/data/wordpress:nydus/2023-03-18-14:44:55_ino.csv')


def convert(cfg: dict, image: str):
    """
    from dokcer hub pull image and push to local registry
    """
    cvt.convert_oci(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)
    cvt.convert_nydus(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)


if __name__ == "__main__":
    util.clean_env()
    main()
