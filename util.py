#!/usr/bin/env python3
import json
import os
import shutil
import subprocess

def get_nydus_config() -> dict:
    config = []
    with open(NYDUS_CONFIG, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config


def switch_config_prefetch_enable():
    """
    switch the fs_prefetch.enable status
    """
    config = get_nydus_config()
    config["fs_prefetch"]["enable"] = True
    with open(NYDUS_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def switch_config_prefetch_unable():
    """
    switch the fs_prefetch.enable status
    """
    config = get_nydus_config()
    config["fs_prefetch"]["enable"] = False
    with open(NYDUS_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def reload_nydus():
    rc = os.system("systemctl restart nydus-snapshotter.service")
    assert rc == 0
    rc = os.system("systemctl restart containerd.service")
    assert rc == 0


def clean_env():
    rc = os.system("nerdctl ps -q | xargs -r nerdctl stop")
    assert rc == 0
    rc = os.system("nerdctl ps -a -q | xargs -r nerdctl rm")
    assert rc == 0
    rc = os.system("sudo nerdctl image prune --all -f")
    assert rc == 0
    rc = os.system("sudo rm -rf ~/logs/*")
    assert rc == 0
    rc = os.system("sudo rm -rf ~/logs/*")
    assert rc == 0
    # rc = os.system("sudo rm -rf /var/lib/containerd-nydus/cache/*")
    # assert rc == 0
    rc = os.system("sudo systemctl restart containerd")
    assert rc == 0


def image_repo(ref: str):
    return ref.split(":")[0]


def image_tag(ref: str) -> str:
    try:
        return ref.split(":")[1]
    except IndexError:
        return None


def image_nydus(ref: str):
    return image_repo(ref) + ":" + image_tag(ref) + "_nydus"


def image_nydus_prefetch(ref: str) -> str:
    return image_repo(ref) + ":" + image_tag(ref) + "_nydus_prefetch"


def image_nydus_bacth_256(ref: str) -> str:
    return image_repo(ref) + ":batch-256k"


def image_nydus_bacth_512(ref: str) -> str:
    return image_repo(ref) + ":batch-512k"


def image_nydus_bacth_1024(ref: str) -> str:
    return image_repo(ref) + ":batch-1024k"
