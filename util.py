#!/usr/bin/env python3
import json
import os
import shutil
import subprocess

NYDUS_CONFIG = "/etc/nydus/config.json"
NYDUS_DIR = "/var/lib/containerd-nydus"


def clean_nydus():
    """
    clear all containers and images and rm nydus workdir
    """
    cmd = ["nerdctl", "rm", "-f", "$(nerdctl ps -aq)"]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0
    cmd = ["nerdctl", "rmi", "-f", "$(nerdctl images -q)"]
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0
    shutil.rmtree(NYDUS_DIR)


def get_nydus_config() -> dict:
    config = []
    with open(NYDUS_CONFIG, 'r', encoding='utf-8') as f:
        objectDict = json.load(f)
        print(objectDict)
    return config


def reload_nydus():
    rc = os.system("systemctl restart nydus-snapshotter.service")
    assert rc == 0
