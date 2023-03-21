#!/usr/bin/env python3
import json
import os
import shutil
import subprocess

NYDUS_CONFIG = "/etc/nydus/config.json"
NYDUS_DIR = "/var/lib/containerd-nydus"
CONTAINRD_DIR = "/var/lib/containerd"
NYDUS_RUN_DIR = "/run/containerd-nydus"
CONTAINRD_RUN_DIR = "/run/containerd"


def clean_nerdctl():
    """
    clear all containers and images and rm nydus workdir
    """
    cmd = ["nerdctl", "rm", "-f", "$(nerdctl ps -aq)"]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0
    cmd = ["nerdctl", "rmi", "-f", "$(nerdctl images -q)"]
    result = subprocess.run(cmd, capture_output=True)


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
    config["fs_prefetch"]["enable"] = not config["fs_prefetch"]["enable"]
    with open(NYDUS_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def reload_nydus():
    rc = os.system("systemctl restart nydus-snapshotter.service")
    assert rc == 0
    rc = os.system("systemctl restart containerd.service")
    assert rc == 0


def clean_env():
    clean_nerdctl()
    rc = os.system("systemctl stop nydus-snapshotter.service")
    assert rc == 0
    rc = os.system("systemctl stop containerd.service")
    assert rc == 0
    shutil.rmtree(NYDUS_DIR)
    shutil.rmtree(CONTAINRD_DIR)
    shutil.rmtree(NYDUS_RUN_DIR)
    shutil.rmtree(CONTAINRD_RUN_DIR)
    rc = os.system("systemctl start nydus-snapshotter.service")
    assert rc == 0
    rc = os.system("systemctl start containerd.service")
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
