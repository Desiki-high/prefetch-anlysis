#!/usr/bin/env python3

import csv
import datetime
import json
import logging
import os
import posixpath
import random
import re
import shutil
import string
import subprocess
import sys
import time
from argparse import ArgumentParser
from typing import Tuple

import yaml

"""
define some file path, binary path and sock api url
"""
LOG_DIR = "log"
TEMP_DIR = "tmp"
DATA_DIR = "data"
URL_PREFIX = "http://localhost/api"
BLOB_CACHE_METRICS = "/v1/metrics/blobcache"
ACCESS_PATTERN_METRICS = "/v1/metrics/pattern"
BACKEND_METRICS = "/v1/metrics/backend"
BOOTSTRAP_DIR = "/var/lib/containerd-nydus/snapshots"
API_DIR = "/var/lib/containerd-nydus/socket"
NYDUS_LOG_DIR = "/var/lib/containerd-nydus/logs"
LOG_FILE = "nydusd.log"


class MetricsCollector:
    def __init__(self, cfg: dict):
        self.registry = cfg["registry"]
        self.insecure_registry = cfg["insecure_registry"]
        self.images = cfg["images"]

    def start_collet(self) -> list[str]:
        files = []
        for i in range(len(self.images)):
            logging.info(self.images[i]["name"] + " metrics collect start")
            if "arg" not in self.images[i]:
                files.append(self.run(self.images[i]["name"]))
            else:
                files.append(self.run(self.images[i]["name"], arg=self.images[i]["arg"]))
        return files

    def run(self, repo: str, arg="") -> Tuple[str, str]:
        image_ref = self.image_ref(repo)
        container_name = repo.replace(":", "-") + random_string()
        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)
        print("Pulling image %s ..." % image_ref)
        rc = os.system(pull_cmd)
        assert rc == 0
        create_cmd = self.create_container_cmd(image_ref, container_name, arg)
        print(create_cmd)
        print("Creating container for image %s ..." % image_ref)
        rc = os.system(create_cmd)
        assert rc == 0
        run_cmd = self.start_container_cmd(container_name)
        print(run_cmd)
        print("Running container %s ..." % container_name)
        rc = os.system(run_cmd)
        assert rc == 0
        file = self.collect(repo)
        self.clean_up(image_ref, container_name)
        return file

    def image_ref(self, repo):
        return posixpath.join(self.registry, repo)

    def pull_cmd(self, image_ref):
        insecure_flag = "--insecure-registry" if self.insecure_registry else ""
        return (
            f"nerdctl --snapshotter nydus pull {insecure_flag} {image_ref}"
        )

    def create_container_cmd(self, image_ref, container_id, arg=""):
        if arg == "":
            return f"nerdctl --snapshotter nydus create --net=host --name={container_id} {image_ref}"
        else:
            return f"nerdctl --snapshotter nydus create --net=host {arg} --name={container_id} {image_ref}"

    def start_container_cmd(self, container_id):
        return f"nerdctl --snapshotter nydus start {container_id}"

    def stop_container_cmd(self, container_id):
        return f"nerdctl --snapshotter nydus stop {container_id}"

    def clean_up(self, image_ref, container_id):
        print("Cleaning up environment for %s ..." % container_id)
        cmd = self.stop_container_cmd(container_id)
        print(cmd)
        rc = os.system(cmd)
        assert rc == 0
        cmd = f"nerdctl --snapshotter nydus rm -f {container_id}"
        print(cmd)
        rc = os.system(cmd)
        assert rc == 0
        cmd = f"nerdctl --snapshotter nydus rmi -f {image_ref}"
        print(cmd)
        rc = os.system(cmd)
        assert rc == 0

    def collect(self, repo) -> str:
        """
            waiting 60s for the container read file from the backend
            then collect the metrics
        """
        time.sleep(180)
        socket = search_file(API_DIR, "api.sock")
        if socket == None:
            print("can't find the api.sock")
            exit(1)
        bootstrap = search_file(BOOTSTRAP_DIR, "image.boot")
        if bootstrap == None:
            print("can't find the bootstrap")
            exit(1)

        # bootstrap
        bootstap_data = check_bootstrap(bootstrap)

        # access_pattern
        access_pattern = get_access_pattern(socket, bootstap_data)
        header = ["file_path", "first_access_time", "file_size"]

        file_name = posixpath.join(DATA_DIR, repo, datetime.datetime.now().strftime(
            '%Y-%m-%d-%H:%M:%S') + ".csv")
        if not os.path.exists(file_name):
            os.makedirs(posixpath.join(DATA_DIR, repo), exist_ok=True)
            os.mknod(file_name)
        with open(file_name, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for item in access_pattern:
                writer.writerow(
                    [item.file_path, item.first_access_time_secs * 10**9 + item.first_access_time_nanos, item.file_size])
        return file_name


def get_file_by_bootstrap(bootstrap, inode):
    """
    load the data of bootstrap
    """
    with open(bootstrap, 'r') as file:
        for line in file:
            if line.startswith("inode:"):
                result = re.search(r'"([^"]+)".*ino (\d+).*i_size (\d+)', line)
                value_file_path = result.group(1)
                value_ino = result.group(2)
                value_file_size = result.group(3)
                if int(value_ino) == inode:
                    return value_file_path, value_file_size
    return None, None


def check_bootstrap(bootstrap):
    """
    use nydus-image to get the data of bootstap
    """
    file_path = random_string()
    cmd = ["nydus-image", "check"]
    cmd.extend(["-B", bootstrap, "-v"])
    with open(TEMP_DIR + "/" + file_path, 'w') as f:
        _ = run_cmd(
            cmd,
            shell=True,
            stdout=f,
            stderr=f,
        )
    return TEMP_DIR + "/" + file_path


class AccessPattern:
    def __init__(self, file_path, first_access_time_secs, first_access_time_nanos, file_size):
        self.file_path = file_path
        self.first_access_time_secs = first_access_time_secs
        self.first_access_time_nanos = first_access_time_nanos
        self.file_size = file_size


def get_access_pattern(sock, bootstap_data):
    """
    get the file access pattern from the sock
    """
    contents = ""
    # The api occasionally returns incomplete information
    while contents.endswith("]") == False:
        with open(send_request(sock, ACCESS_PATTERN_METRICS), 'r') as file:
            contents = file.read()
    resp = json.loads(contents)
    access_pattern_list = []
    for item in resp:
        file_path, file_size = get_file_by_bootstrap(bootstap_data, item['ino'])
        access_pattern_list.append(AccessPattern(
            file_path, item['first_access_time_secs'], item['first_access_time_nanos'], file_size))
    return access_pattern_list


class BackendMetrics:
    def __init__(self, read_count, read_amount_total):
        self.read_count = read_count
        self.read_amount_total = read_amount_total


def collect_backend(sock):
    """
    collect the backend metrics from the sock
    """
    contents = ""
    with open(send_request(sock, BACKEND_METRICS), 'r') as file:
        contents = file.read()
    resp = json.loads(contents)
    return BackendMetrics(resp["read_count"], resp["read_amount_total"])


def random_string():
    """Generate a random string of fixed length """
    return "".join(random.choice(string.ascii_lowercase) for i in range(10))


def search_file(root_dir, file_name):
    """
    search the bootsatrap and api.scok of the image, but only return the first match file,
    so we need to clear the images and containers befor we start metrics.py
    """
    for subdir, _, files in os.walk(root_dir):
        if file_name in files:
            return os.path.join(subdir, file_name)
    return None


def send_request(sock_path, url):
    """
    This function send request to the local socket with the url.

    :param sock_path: The socket path
    :param url: The api url and the URL_PREFIX  is the prefix
    :return: the stdout of the request
    """
    file_path = random_string()
    cmd = ["curl", "--unix-socket", sock_path]
    cmd.extend(["-X", "GET", URL_PREFIX + url])
    with open(TEMP_DIR + "/" + file_path, 'w') as f:
        _ = run_cmd(
            cmd,
            shell=True,
            stdout=f,
            stderr=subprocess.PIPE
        )
    return TEMP_DIR + "/" + file_path


def run_cmd(cmd, wait: bool = True, verbose=True, **kwargs):
    """
    This function run a cmd with the subprocess

    :param cmd: the cmd string or the string list
    :param **kwargs: the  optional keyword argument that is passed to subprocess.Popen()
    :return: the subprocess.Popen object
    """
    shell = kwargs.pop("shell", False)
    if shell:
        cmd = " ".join(cmd)

    if verbose:
        logging.info(cmd)
    else:
        logging.debug(cmd)

    popen_obj = subprocess.Popen(cmd, shell=shell, **kwargs)
    if wait:
        popen_obj.wait()

    return popen_obj.returncode, popen_obj


def init():
    time = datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
    if os.path.exists(LOG_DIR) and os.path.isfile(LOG_DIR):
        os.remove(LOG_DIR)
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
    if os.path.exists(TEMP_DIR):
        if os.path.isdir(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        else:
            os.remove(TEMP_DIR)
    os.mkdir(TEMP_DIR)
    os.mknod(f"{LOG_DIR }/{time}.log")
    logging.basicConfig(filename=f"{LOG_DIR }/{time}.log", filemode="w", format="%(asctime)s  %(levelname)s: %(message)s",
                        datefmt="%Y-%M-%d %H:%M:%S", level=logging.DEBUG)


def exit(status):
    # cleanup
    shutil.rmtree(TEMP_DIR)
    sys.exit(status)


def main():
    init()

    parser = ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        dest='config',
        type=str,
        required=True,
        help='Input YAML configuration file')
    parser.add_argument(
        '-t',
        '--times',
        dest='times',
        type=int,
        default=1,
        required=False,
        help='the times of metrisc collect')

    args = parser.parse_args()
    cfg = {}
    with open(args.config, 'r', encoding='utf-8') as f:
        try:
            cfg = yaml.load(stream=f, Loader=yaml.FullLoader)
        except Exception as inst:
            print('error reading config file')
            print(inst)
            exit(-1)
    metrics_collector = MetricsCollector(cfg)
    for _ in range(args.times):
        metrics_collector.start_collet()
        shutil.rmtree(TEMP_DIR)
        os.mkdir(TEMP_DIR)


def collect_access(local_registry, insecure_local_registry, image) -> str:
    init()
    cfg = {"registry": local_registry, "insecure_registry": insecure_local_registry, "images": [{"name": image}]}
    file = MetricsCollector(cfg).start_collet()[0]
    shutil.rmtree(TEMP_DIR)
    return file


if __name__ == "__main__":
    main()
    exit(0)
