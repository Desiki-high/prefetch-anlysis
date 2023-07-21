#!/usr/bin/env python3

import os
import shutil
from typing import Tuple

import yaml

import algorithm.prefetch_list as alg
import bench.bench as bench
import convert.convert as cvt
import draw
import metrics.metrics as metrics
import util

DATA_DIR = "data"
LOG_DIR = "log"
CONFIG = "config.yaml"
PREFETCH_FILE_LIST = "out_list.txt"


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
        if cfg["algorithm"]:
            # collect metrics dat
            file = collect_metrics(cfg, image)
            # generate prefetch list
            _ = alg.get_prefetch_list(file)
            # rebuild
            cvt.convert_nydus_prefetch(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image, PREFETCH_FILE_LIST)
        # bench
        start_bench(cfg, image)
        # draw bench result
        draw.draw(util.image_repo(image) + ".csv", util.image_repo(image) + ".png")


def convert(cfg: dict, image: str):
    """
    from dokcer hub pull image and push to local registry
    """
    cvt.convert_oci(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)
    cvt.convert_nydus(cfg["source_registry"], cfg["insecure_source_registry"], cfg["local_registry"], cfg["insecure_local_registry"], image)


def collect_metrics(cfg: dict, image: str) -> str:
    """
    collect metrics
    """
    return metrics.collect_access(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image))


def start_bench(cfg: dict, image: str):
    """
    bench oci, nydus without prefetch, nydus with all prefetch, nydus witch alg prefetch
    """
    f = open(util.image_repo(image) + ".csv", "w")
    csv_headers = "timestamp,registry,repo,pull_elapsed(s),create_elapsed(s),run_elapsed(s),total_elapsed(s),read_count,read_amount_total"
    f.writelines(csv_headers + "\n")
    f.flush()
    # oci
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], image, f)
    util.switch_config_prefetch_unable()
    util.reload_nydus()
    # no prefetch
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image), f, "nydus")
    util.switch_config_prefetch_enable()
    util.reload_nydus()
    # prefetch all
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus(image), f, "nydus", False)
    # prefetch list
    bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus_prefetch(image), f, "nydus")
    if cfg["batch"]:
        bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus_bacth_256(image), f, "nydus")
        bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus_bacth_512(image), f, "nydus")
        bench.bench_image(cfg["local_registry"], cfg["insecure_local_registry"], util.image_nydus_bacth_1024(image), f, "nydus")
    util.reload_nydus()


if __name__ == "__main__":
    util.clean_env()
    try:
        main()
    except Exception:
        print(Exception)
        util.reload_nydus()
    if os.path.exists(LOG_DIR):
        shutil.rmtree(LOG_DIR)
