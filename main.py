#!/usr/bin/env python3

import yaml

import util

CONFIG = "config.yaml"


def main():
    """
    1. read config file to knows the  images:tag and registry and if we need convert to nydus image or not
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
    print(cfg)


if __name__ == "__main__":
    util.clean_nydus()
    util.reload_nydus()
    main()
