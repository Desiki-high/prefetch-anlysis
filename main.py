#!/usr/bin/env python3

from typing import Tuple

import yaml

import algorithm.prefetch_list as alg
import bench.bench as bench
import convert.convert as cvt
import draw
import metrics.metrics as metrics
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
        util.clean_env()
    for image in cfg["images"]:
        file, ino = collect_metrics(cfg, image)
        _ = alg.get_prefetch_list(file, ino)
        cvt.convert_nydus_prefetch(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image, PREFETCH_FILE_LIST)
        start_bench(cfg, image)
        draw.draw(util.image_repo(image) + ".csv", util.image_repo(image) + ".png")


def convert(cfg: dict, image: str):
    """
    from dokcer hub pull image and push to local registry
    """
    cvt.convert_oci(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)
    cvt.convert_nydus(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)


def collect_metrics(cfg: dict, image: str) -> Tuple[str, str]:
    """
    collect metrics
    """
    return metrics.collect(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image))


def start_bench(cfg: dict, image: str):
    """
    bench oci, nydus without prefetch, nydus with all prefetch, nydus witch alg prefetch
    """
    f = open(util.image_repo(image) + ".csv", "w")
    csv_headers = "timestamp,registry,repo,pull_elapsed(s),create_elapsed(s),run_elapsed(s),total_elapsed(s)"
    f.writelines(csv_headers + "\n")
    f.flush()
    # oci
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], image, f)
    # no prefetch
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image), f, "nydus")
    # TODO: change prefetch enable and bench
    util.switch_config_prefetch_enable()
    util.reload_nydus()
    # prefetch all
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image), f, "nydus", False)
    # prefetch list
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus_prefetch(image), f, "nydus")
    util.switch_config_prefetch_enable()
    util.reload_nydus()


if __name__ == "__main__":
    util.clean_env()
    main()
