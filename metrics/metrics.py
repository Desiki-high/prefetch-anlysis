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

    def start_collet(self):
        for i in range(len(self.images)):
            logging.info(self.images[i]["name"] + " metrics collect start")
            if "arg" not in self.images[i]:
                self.run(self.images[i]["name"])
            else:
                self.run(self.images[i]["name"], arg=self.images[i]["arg"])

    def run(self, repo: str, arg=""):
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
        self.collect(repo)
        self.clean_up(image_ref, container_name)

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

#  问题一：这里的相对时间有问题，在关闭预取的情况下测试无法拿到预取的开始时间以启动时间为预取开始时间存在时间误差
    def collect(self, repo):
        """
            waiting 60s for the container read file from the backend
            then collect the metrics
        """
        time.sleep(60)
        socket = search_file(API_DIR, "api.sock")
        if socket == None:
            print("can't find the api.sock")
            exit(1)
        bootstrap = search_file(BOOTSTRAP_DIR, "image.boot")
        if bootstrap == None:
            print("can't find the bootstrap")
            exit(1)

        # prefetch
        # prefetch = get_prefetch(socket)

        # bootstrap
        bootstap_data = check_bootstrap(bootstrap)

        # access_pattern
        access_pattern = get_access_pattern(socket, bootstap_data)

        header = ["file_path", "ino", "first_access_time",
                  "access_times", "file_size"]

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
                    [item.file_path, item.ino, item.first_access_time_secs * 10**6 + item.first_access_time_micros,
                     item.access_times, item.file_size])
        self.colletc_ino(repo)

#  问题二：依赖于埋点日志 log::info!() 需要转换为metrics 从接口拿数据更为合理
    def colletc_ino(self, repo):
        file_path = search_file(NYDUS_LOG_DIR, LOG_FILE)
        result = []
        if file_path != None:
            with open(file_path) as file:
                result = re.findall(r"\d+\s+\d+\s+\d+\s+\d+\s+\d+$", file.read(), re.MULTILINE)
            header = ["ino", "offset", "size", "latency", "ino_access_time"]
            file_name = posixpath.join(DATA_DIR, repo, datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')+"_ino" + ".csv")
            if not os.path.exists(file_name):
                os.makedirs(posixpath.join(DATA_DIR, repo), exist_ok=True)
                os.mknod(file_name)
            with open(file_name, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for item in result:
                    writer.writerow([int(num) for num in item.split()])


def get_prefetchtime():
    """
    get prefetchtime from log(hack)
    """
    file_path = search_file(NYDUS_LOG_DIR, LOG_FILE)
    result = []
    if file_path != None:
        with open(file_path) as file:
            for line in file:
                if line.find("prefetch_begin") != -1:
                    logging.info(line)
                    result = re.search(r'prefetch_begin:(\d+)$', line)
                    return int(result.group(1))
    return None

# class BackendLatency:
#     def __init__(self, latencys):
#         self.blcok_interval = ["<1K", "1K~", "4K~",
#                                "16K~", "64K~", "128K~", "512K~", "1M~"]
#         self.latencys = latencys


# def get_backend(sock):
#     """
#     get the backend metrics from the sock
#     """
#     contents = ""
#     with open(send_request(sock, BACKEND_METRICS), 'r') as file:
#         contents = file.read()
#     resp = json.loads(contents)
#     backend_latency = BackendLatency(
#         resp["read_cumulative_latency_millis_dist"])
#     return backend_latency


# def get_latency(backend_latency, file_size):
#     file_size = int(file_size)
#     if file_size < 1024:
#         return backend_latency.latencys[0]
#     elif 1024 <= file_size < 4096:
#         return backend_latency.latencys[1]
#     elif 4096 <= file_size < 16384:
#         return backend_latency.latencys[2]
#     elif 16384 <= file_size < 65536:
#         return backend_latency.latencys[3]
#     elif 65536 <= file_size < 131072:
#         return backend_latency.latencys[4]
#     elif 131072 <= file_size < 524288:
#         return backend_latency.latencys[5]
#     elif 524288 <= file_size < 1048576:
#         return backend_latency.latencys[6]
#     else:
#         return backend_latency.latencys[7]


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
    def __init__(self, file_path, ino, access_times, first_access_time_secs, first_access_time_micros, file_size):
        self.file_path = file_path
        self.ino = ino
        self.access_times = access_times
        # the access_time is relative to the time of prefetch begin
        self.first_access_time_secs = first_access_time_secs
        self.first_access_time_micros = first_access_time_micros
        self.file_size = file_size

    def show(self):
        print("file_path: ", self.file_path)
        print("access_times: ", self.access_times)
        print("first_access_time_secs: ", self.first_access_time_secs)
        print("first_access_time_millis: ", self.first_access_time_millis)
        print("file_size: ", self.file_size)
        print("latency: ", self.latency)


def get_access_pattern(sock, bootstap_data):
    """
    get the file access pattern from the sock
    """
    contents = ""
    while contents.endswith("]") == False:
        with open(send_request(sock, ACCESS_PATTERN_METRICS), 'r') as file:
            contents = file.read()
    resp = json.loads(contents)
    access_pattern_list = []
    prefetch_begin_time = get_prefetchtime()
    for item in resp:
        logging.info(item['first_access_time_secs'])
        logging.info(item["first_access_time_nanos"])
        item['first_access_time_secs'] = item['first_access_time_secs'] - prefetch_begin_time // 1000000
        item["first_access_time_nanos"] = item["first_access_time_nanos"] // 1000 - (prefetch_begin_time % 1000)
        if item["first_access_time_nanos"] < 0:
            item["first_access_time_nanos"] += 1000000
            item['first_access_time_secs'] -= 1
        file_path, file_size = get_file_by_bootstrap(bootstap_data, item['ino'])
        access_pattern_list.append(AccessPattern(
            file_path, item['ino'], item['nr_read'], item['first_access_time_secs'], item['first_access_time_nanos'], file_size))
    return access_pattern_list


class Prefetch:
    def __init__(self, prefetch_begin_time_secs, prefetch_begin_time_millis):
        self.prefetch_begin_time_secs = prefetch_begin_time_secs
        self.prefetch_begin_time_millis = prefetch_begin_time_millis

    def show(self):
        print("prefetch_begin_time_secs: ", self.prefetch_begin_time_secs)
        print("prefetch_begin_time_millis: ", self.prefetch_begin_time_millis)


def get_prefetch(sock):
    """
    get the prefetch begin time from the sock
    """
    contents = ""
    with open(send_request(sock, BLOB_CACHE_METRICS), 'r') as file:
        contents = file.read()
    resp = json.loads(contents)
    return Prefetch(
        prefetch_begin_time_secs=resp["prefetch_begin_time_secs"],
        prefetch_begin_time_millis=resp["prefetch_begin_time_millis"]
    )


# def format_number(number, n):
#     """
#     Formats the given int number to have n digits, adding trailing zeros if necessary.
#     """
#     number_str = str(number)
#     if len(number_str) < n:
#         number_str = number_str.zfill(n)
#     return int(number_str)


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


if __name__ == "__main__":
    main()
    exit(0)
