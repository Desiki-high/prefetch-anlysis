#!/usr/bin/env python3

import copy
import json
import logging
import os
import posixpath
import random
import shutil
import string
import subprocess
import sys
import tempfile
import time
import urllib.request
from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import datetime
from io import TextIOWrapper

import metrics.metrics as metric
TMP_DIR = tempfile.mkdtemp()


def exit(status):
    # cleanup
    shutil.rmtree(TMP_DIR)
    sys.exit(status)


def tmp_dir():
    tmp_dir.nxt += 1
    return os.path.join(TMP_DIR, str(tmp_dir.nxt))


tmp_dir.nxt = 0


def logging_setup(logging_stream=sys.stderr):
    """Inspired from Kadalu project"""
    root = logging.getLogger()

    if root.hasHandlers():
        return

    verbose = True

    # Errors should also be printed to screen.
    handler = logging.StreamHandler(logging_stream)

    if verbose:
        root.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s "
        "[%(module)s - %(lineno)s:%(funcName)s] "
        "- %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


logging_setup()


def random_chars():
    return "".join(random.choice(string.ascii_lowercase) for i in range(10))


def run(cmd, wait: bool = True, verbose=True, **kwargs):

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


def tmp_copy(src):
    dst = tmp_dir()
    shutil.copytree(src, dst)
    return dst


def get_current_time():
    return datetime.now()


def delta_time(t_end, t_start):
    delta = t_end - t_start
    return delta.total_seconds(), delta.microseconds


@contextmanager
def timer(cmd):
    start = get_current_time()
    try:
        rc = os.system(cmd)
        assert rc == 0
        end = get_current_time()
        sec, usec = delta_time(end, start)
        yield sec + usec / 1e6
        logging.info("%s, Takes time %u.%u seconds", cmd, sec, usec)
    finally:
        pass


class RunArgs:
    def __init__(
        self, env={}, arg="", stdin="", stdin_sh="sh", waitline="", mount=[], waitURL=""
    ):
        self.env = env
        self.arg = arg
        self.stdin = stdin
        self.stdin_sh = stdin_sh
        self.waitline = waitline
        self.mount = mount
        self.waitURL = waitURL


class Bench:
    def __init__(self, name, category="other"):
        self.name = name
        self.category = category

    def __str__(self):
        return json.dumps(self.__dict__)

    def set_tag(self, tag):
        self.name = f"{self.name}:{tag}"


class BenchRunner:
    ECHO_HELLO = set(
        [
            "alpine",
            "busybox",
            "crux",
            "cirros",
            "debian",
            "ubuntu",
            "ubuntu-upstart",
            "ubuntu-debootstrap",
            "centos",
            "fedora",
            "opensuse",
            "oraclelinux",
            "mageia",
        ]
    )

    CMD_ARG_WAIT = {
        "mysql": RunArgs(
            env={"MYSQL_ROOT_PASSWORD": "abc"}, waitline="mysqld: ready for connections"
        ),
        "percona": RunArgs(
            env={"MYSQL_ROOT_PASSWORD": "abc"}, waitline="mysqld: ready for connections"
        ),
        "mariadb": RunArgs(
            env={"MYSQL_ROOT_PASSWORD": "abc"},
            waitline="mariadbd: ready for connections",
        ),
        "postgres": RunArgs(waitline="database system is ready to accept connections"),
        "redis": RunArgs(waitline="Ready to accept connections"),
        "crate": RunArgs(waitline="started"),
        "rethinkdb": RunArgs(waitline="Server ready"),
        "ghost": RunArgs(waitline="Listening on"),
        "glassfish": RunArgs(waitline="Running GlassFish"),
        "drupal": RunArgs(waitline="apache2 -D FOREGROUND"),
        "elasticsearch": RunArgs(waitline="] started"),
        "cassandra": RunArgs(waitline="Listening for thrift clients"),
        "httpd": RunArgs(waitline="httpd -D FOREGROUND"),
        "jenkins": RunArgs(waitline="Jenkins is fully up and running"),
        "jetty": RunArgs(waitline="main: Started"),
        "mongo": RunArgs(waitline="waiting for connections"),
        "php-zendserver": RunArgs(waitline="Zend Server started"),
        "rabbitmq": RunArgs(waitline="Server startup complete"),
        "sonarqube": RunArgs(waitline="Process[web] is up"),
        "tomcat": RunArgs(arg="catalina.sh run", waitline="Server startup"),
    }

    CMD_STDIN = {
        "php": RunArgs(stdin='php -r "echo \\"hello\\n\\";"'),
        "ruby": RunArgs(stdin='ruby -e "puts \\"hello\\""'),
        "jruby": RunArgs(stdin='jruby -e "puts \\"hello\\""'),
        "julia": RunArgs(stdin="julia -e 'println(\"hello\")'"),
        "gcc": RunArgs(stdin="cd /src; gcc main.c; ./a.out", mount=[("gcc", "/src")]),
        "golang": RunArgs(
            stdin="cd /go/src; go run main.go", mount=[("go", "/go/src")]
        ),
        "clojure": RunArgs(
            stdin="cd /hello/hello; lein run", mount=[("clojure", "/hello")]
        ),
        "rails": RunArgs(stdin="rails new hello"),
        "haskell": RunArgs(stdin='"hello"', stdin_sh=None),
        "hylang": RunArgs(stdin='(print "hello")', stdin_sh=None),
        "java": RunArgs(
            stdin="cd /src; javac Main.java; java Main", mount=[("java", "/src")]
        ),
        "mono": RunArgs(
            stdin="cd /src; mcs main.cs; mono main.exe", mount=[("mono", "/src")]
        ),
        "r-base": RunArgs(stdin='sprintf("hello")', stdin_sh="R --no-save"),
        "thrift": RunArgs(
            stdin="cd /src; thrift --gen py hello.idl", mount=[("thrift", "/src")]
        ),
        "benchmark": RunArgs(
            stdin='sed -i "s/.cuda()//g" /benchmark/vision/test.py; sed -i "s/cuda/cpu/g" /benchmark/vision/test.py; sed -i "/^  assert/d" /benchmark/vision/test.py; sed -i "s/required=True/required=False/g" /benchmark/vision/test.py; sed -i "s/20/1/g" /benchmark/vision/test.py; cd /benchmark; python /benchmark/vision/test.py'
        ),
    }

    CMD_ARG = {
        "perl": RunArgs(arg="perl -e 'print(\"hello\\n\")'"),
        "rakudo-star": RunArgs(arg="perl6 -e 'print(\"hello\\n\")'"),
        "pypy": RunArgs(arg="pypy3 -c 'print(\"hello\")'"),
        "python": RunArgs(arg="python -c 'print(\"hello\")'"),
        "hello-world": RunArgs(),
    }

    CMD_URL_WAIT = {
        "nginx": RunArgs(waitURL="http://localhost:80"),
        "wordpress": RunArgs(waitURL="http://localhost:80"),
        "iojs": RunArgs(
            arg="iojs /src/index.js",
            mount=[("iojs", "/src")],
            waitURL="http://localhost:80",
        ),
        "node": RunArgs(
            waitURL="http://localhost:3000",
        ),
        "django": RunArgs(waitURL="http://127.0.0.1:8000"),
        "registry": RunArgs(
            env={"GUNICORN_OPTS": '["--preload"]'}, waitURL="http://localhost:5000"
        ),
    }

    # complete listing
    ALL = dict(
        [
            (b.name, b)
            for b in [
                Bench("alpine", "distro"),
                Bench("busybox", "distro"),
                Bench("crux", "distro"),
                Bench("cirros", "distro"),
                Bench("debian", "distro"),
                Bench("ubuntu", "distro"),
                Bench("ubuntu-upstart", "distro"),
                Bench("ubuntu-debootstrap", "distro"),
                Bench("centos", "distro"),
                Bench("fedora", "distro"),
                Bench("opensuse", "distro"),
                Bench("oraclelinux", "distro"),
                Bench("mageia", "distro"),
                Bench("mysql", "database"),
                Bench("percona", "database"),
                Bench("mariadb", "database"),
                Bench("postgres", "database"),
                Bench("redis", "database"),
                Bench("crate", "database"),
                Bench("rethinkdb", "database"),
                Bench("php", "language"),
                Bench("ruby", "language"),
                Bench("jruby", "language"),
                Bench("julia", "language"),
                Bench("perl", "language"),
                Bench("rakudo-star", "language"),
                Bench("pypy", "language"),
                Bench("python", "language"),
                Bench("golang", "language"),
                Bench("clojure", "language"),
                Bench("haskell", "language"),
                Bench("hylang", "language"),
                Bench("java", "language"),
                Bench("mono", "language"),
                Bench("r-base", "language"),
                Bench("gcc", "language"),
                Bench("thrift", "language"),
                Bench("benchmark"),
                Bench("cassandra", "database"),
                Bench("mongo", "database"),
                Bench("elasticsearch", "database"),
                Bench("hello-world"),
                Bench("ghost"),
                Bench("drupal"),
                Bench("jenkins"),
                Bench("sonarqube"),
                Bench("rabbitmq"),
                Bench("registry"),
                Bench("httpd", "web-server"),
                Bench("nginx", "web-server"),
                Bench("glassfish", "web-server"),
                Bench("jetty", "web-server"),
                Bench("php-zendserver", "web-server"),
                Bench("tomcat", "web-server"),
                Bench("django", "web-framework"),
                Bench("rails", "web-framework"),
                Bench("node", "web-framework"),
                Bench("iojs", "web-framework"),
                Bench("wordpress", "web-framework"),
            ]
        ]
    )

    def __init__(
        self,
        registry="localhost:5000",
        snapshotter="overlayfs",
        cleanup=True,
        insecure_registry=False,
    ):
        self.registry = registry
        if self.registry != "":
            self.registry += "/"

        self.snapshotter = snapshotter
        self.insecure_registry = insecure_registry

        self.cleanup = cleanup

    def image_ref(self, repo):
        return posixpath.join(self.registry, repo)

    def run(self, bench):
        repo = image_repo(bench.name)
        if repo in BenchRunner.ECHO_HELLO:
            return self.run_echo_hello(repo=bench.name)
        elif repo in BenchRunner.CMD_ARG:
            return self.run_cmd_arg(repo=bench.name, runargs=BenchRunner.CMD_ARG[repo])
        elif repo in BenchRunner.CMD_ARG_WAIT:
            return self.run_cmd_arg_wait(
                repo=bench.name, runargs=BenchRunner.CMD_ARG_WAIT[repo]
            )
        elif repo in BenchRunner.CMD_STDIN:
            return self.run_cmd_stdin(
                repo=bench.name, runargs=BenchRunner.CMD_STDIN[repo]
            )
        elif repo in BenchRunner.CMD_URL_WAIT:
            return self.run_cmd_url_wait(
                repo=bench.name, runargs=BenchRunner.CMD_URL_WAIT[repo]
            )
        else:
            print("Unknown bench: " + repo)
            exit(1)

    def run_echo_hello(self, repo: str):
        image_ref = self.image_ref(repo)
        container_name = repo.replace(":", "-") + random_chars()

        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)

        print("Pulling image %s ..." % image_ref)
        with timer(pull_cmd) as t:
            pull_elapsed = t

        create_cmd = self.create_echo_hello_cmd(image_ref, container_name)
        print(create_cmd)

        print("Creating container for image %s ..." % image_ref)
        with timer(create_cmd) as t:
            create_elapsed = t

        run_cmd = self.task_start_cmd(container_name, iteration=False)
        print(run_cmd)

        print("Running container %s ..." % container_name)
        with timer(run_cmd) as t:
            run_elapsed = t
        if self.cleanup:
            backend_metric = self.clean_up(image_ref, container_name)

        return pull_elapsed, create_elapsed, run_elapsed, backend_metric.read_count, backend_metric.read_amount_total

    def run_cmd_arg(self, repo, runargs):
        assert len(runargs.mount) == 0

        image_ref = self.image_ref(repo)
        container_name = repo.replace(":", "-") + random_chars()

        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)

        print("Pulling image %s ..." % image_ref)
        with timer(pull_cmd) as t:
            pull_elapsed = t

        create_cmd = self.create_cmd_arg_cmd(image_ref, container_name, runargs)
        print(create_cmd)

        print("Creating container for image %s ..." % image_ref)
        with timer(create_cmd) as t:
            create_elapsed = t

        run_cmd = self.task_start_cmd(container_name, iteration=False)
        print(run_cmd)

        with timer(run_cmd) as t:
            run_elapsed = t

        if self.cleanup:
            backend_metric = self.clean_up(image_ref, container_name)

        return pull_elapsed, create_elapsed, run_elapsed, backend_metric.read_count, backend_metric.read_amount_total

    def run_cmd_arg_wait(self, repo, runargs):
        image_ref = self.image_ref(repo)
        container_name = repo.replace(":", "-") + random_chars()

        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)

        print("Pulling image %s ..." % image_ref)
        with timer(pull_cmd) as t:
            pull_elapsed = t

        create_cmd = self.create_cmd_arg_wait_cmd(image_ref, container_name, runargs)
        print(create_cmd)

        print("Creating container for image %s ..." % image_ref)
        with timer(create_cmd) as t:
            create_elapsed = t

        run_cmd = self.task_start_cmd(container_name, iteration=True)
        print(run_cmd)

        r, w = os.pipe()
        reader = os.fdopen(r)
        writer = os.fdopen(w)

        print("Running container %s ..." % container_name)
        start_run = datetime.now()

        p = subprocess.Popen(run_cmd, shell=True, stdout=writer, stderr=writer)

        while True:
            l = reader.readline()
            if l == "":
                continue
            print("out: " + l.strip())
            # are we done?
            if l.find(runargs.waitline) >= 0:
                end_run = datetime.now()
                run_elapsed = datetime.timestamp(end_run) - datetime.timestamp(
                    start_run
                )
                print("DONE")
                break
        print("Run time: %f s" % run_elapsed)

        if self.cleanup:
            backend_metric = self.clean_up(image_ref, container_name)

        return pull_elapsed, create_elapsed, run_elapsed, backend_metric.read_count, backend_metric.read_amount_total

    def run_cmd_stdin(self, repo, runargs):
        image_ref = self.image_ref(repo)
        container_name = repo.replace(":", "-") + random_chars()

        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)

        print("Pulling image %s ..." % image_ref)
        with timer(pull_cmd) as t:
            pull_elapsed = t

        create_cmd = self.create_cmd_stdin_cmd(image_ref, container_name, runargs)
        print(create_cmd)

        print("Creating container for image %s ..." % image_ref)
        with timer(create_cmd) as t:
            create_elapsed = t

        run_cmd = self.task_start_cmd(container_name, iteration=True)
        print(run_cmd)

        print("Running container %s ..." % container_name)
        start_run = datetime.now()

        p = subprocess.Popen(
            run_cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            stderr=sys.stdout,
            bufsize=0,
        )

        print(runargs.stdin)
        stdin = runargs.stdin + "\nexit\n"
        p.communicate(stdin.encode())
        end_run = datetime.now()
        run_elapsed = datetime.timestamp(end_run) - datetime.timestamp(start_run)
        print("p.returncode:", p.returncode)
        # assert(p.returncode == 0)

        print("Run time: %f s" % run_elapsed)

        if self.cleanup:
            backend_metric = self.clean_up(image_ref, container_name)

        return pull_elapsed, create_elapsed, run_elapsed, backend_metric.read_count, backend_metric.read_amount_total

    def run_cmd_url_wait(self, repo, runargs):
        image_ref = self.image_ref(repo)
        container_id = random_chars()

        pull_cmd = self.pull_cmd(image_ref)
        print(pull_cmd)

        print("Pulling image %s ..." % image_ref)
        with timer(pull_cmd) as t:
            pull_elapsed = t

        create_cmd = self.create_cmd_url_wait_cmd(image_ref, container_id, runargs)
        print(create_cmd)

        print("Creating container for image %s ..." % image_ref)
        with timer(create_cmd) as t:
            create_elapsed = t

        run_cmd = self.task_start_cmd(container_id, iteration=False)
        print(run_cmd)

        print("Running container %s ..." % container_id)
        start_run = datetime.now()

        p = subprocess.Popen(run_cmd, shell=True)
        while True:
            try:
                req = urllib.request.urlopen(runargs.waitURL)
                print(req.status)
                req.close()
                break
            except:
                time.sleep(0.01)  # wait 10ms
                pass  # retry

        end_run = datetime.now()
        run_elapsed = datetime.timestamp(end_run) - datetime.timestamp(start_run)

        print("Run time: %f s" % run_elapsed)

        if self.cleanup:
            backend_metric = self.clean_up(image_ref, container_id)

        return pull_elapsed, create_elapsed, run_elapsed, backend_metric.read_count, backend_metric.read_amount_total

    def pull_cmd(self, image_ref):
        insecure_flag = "--insecure-registry" if self.insecure_registry else ""
        return (
            f"nerdctl --snapshotter {self.snapshotter} pull {insecure_flag} {image_ref}"
        )

    def create_echo_hello_cmd(self, image_ref, container_id):
        return f"nerdctl --snapshotter {self.snapshotter} create --net=host --name={container_id} {image_ref} -- echo hello"

    def create_cmd_arg_cmd(self, image_ref, container_id, runargs):
        cmd = f"nerdctl --snapshotter {self.snapshotter} create --net=host --name={container_id} {image_ref} "
        return cmd + runargs.arg

    def create_cmd_arg_wait_cmd(self, image_ref, container_id, runargs):
        cmd = f"nerdctl --snapshotter {self.snapshotter} create --net=host "
        if len(runargs.env) > 0:
            env = " ".join(["--env %s=%s" % (k, v) for k, v in runargs.env.items()])
            cmd += f" {env} "
        for a, b in runargs.mount:
            a = os.path.join(os.path.dirname(os.path.abspath(__file__)), a)
            a = tmp_copy(a)
            cmd += f"--volume {a}:{b} "
        cmd += f"--name={container_id} {image_ref}"
        if len(runargs.arg) > 0:
            cmd += f" -- {runargs.arg} "

        return cmd

    def create_cmd_stdin_cmd(self, image_ref, container_id, runargs):
        cmd = f"nerdctl --snapshotter {self.snapshotter} create --net=host "
        for a, b in runargs.mount:
            a = os.path.join(os.path.dirname(os.path.abspath(__file__)), a)
            a = tmp_copy(a)
            cmd += f"--volume {a}:{b} "
        cmd += f"--name={container_id} {image_ref}"
        if runargs.stdin_sh:
            cmd += f" -- {runargs.stdin_sh}"  # e.g., sh -c
        return cmd

    def create_cmd_url_wait_cmd(self, image_ref, container_id, runargs):
        cmd = f"nerdctl --snapshotter {self.snapshotter} create --net=host "
        for a, b in runargs.mount:
            a = os.path.join(os.path.dirname(os.path.abspath(__file__)), a)
            a = tmp_copy(a)
            cmd += f"--volume {a}:{b} "
        if len(runargs.env) > 0:
            env = " ".join([f"--env {k}={v}" for k, v in runargs.env.items()])
            cmd += f" {env} "
        cmd += f"--name={container_id} {image_ref}"
        if len(runargs.arg) > 0:
            cmd += f" -- {runargs.arg} "
        return cmd

    def task_start_cmd(self, container_id, iteration: bool):
        if iteration:
            return f"nerdctl --snapshotter {self.snapshotter} start -a {container_id}"
        else:
            return f"nerdctl --snapshotter {self.snapshotter} start {container_id}"

    def task_kill_cmd(self, container_id):
        return f"nerdctl --snapshotter {self.snapshotter} stop {container_id}"

    def clean_up(self, image_ref, container_id) -> metric.BACKEND_METRICS:
        if self.snapshotter == "nydus":
            backend_metric = metric.collect_backend()
        else:
            backend_metric = metric.BackendMetrics(0, 0)
        print("Cleaning up environment for %s ..." % container_id)
        cmd = self.task_kill_cmd(container_id)
        print(cmd)
        rc = os.system(cmd)  # sometimes containers already exit. we ignore the failure.
        cmd = f"nerdctl --snapshotter {self.snapshotter} rm -f {container_id}"
        print(cmd)
        rc = os.system(cmd)
        assert rc == 0
        cmd = f"nerdctl --snapshotter {self.snapshotter} rmi -f {image_ref}"
        print(cmd)
        rc = os.system(cmd)
        assert rc == 0
        return backend_metric


def image_repo(ref: str):
    return ref.split(":")[0]


def image_tag(ref: str) -> str:
    try:
        return ref.split(":")[1]
    except IndexError:
        return None


def main():
    benches = []

    parser = ArgumentParser()
    parser.add_argument(
        "--images",
        nargs="+",
        dest="images_list",
        type=str,
        default="",
    )

    parser.add_argument(
        "--registry",
        type=str,
        default="",
    )

    parser.add_argument(
        "--all", dest="all_supported_images", action="store_true", required=False
    )

    parser.add_argument(
        "--snapshotter",
        type=str,
        help="only applied with containerd",
        choices=["overlayfs", "nydus", "stargz"],
        default="overlayfs",
    )

    parser.add_argument(
        "--no-cleanup", dest="no_cleanup", action="store_true", required=False
    )

    parser.add_argument(
        "--insecure-registry",
        dest="insecure_registry",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "--out-format",
        dest="output_format",
        type=str,
        choices=["csv", "json"],
        default="json",
    )

    parser.add_argument(
        "--bench-times",
        dest="bench_times",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    registry = args.registry
    all_supported_images = args.all_supported_images
    images_list = args.images_list
    snapshotter = args.snapshotter
    cleanup = not args.no_cleanup
    insecure_registry = args.insecure_registry

    output_format = args.output_format
    bench_times = args.bench_times

    if all_supported_images:
        benches.extend(BenchRunner.ALL.values())
    else:
        for i in images_list:
            try:
                bench = copy.deepcopy(BenchRunner.ALL[image_repo(i)])

                tag = image_tag(i)
                if tag is not None:
                    bench.set_tag(tag)

                benches.append(bench)
            except KeyError:
                logging.warning("image %s not supported, skip", i)

    f = open("bench." + output_format, "w")

    # run benchmarks
    runner = BenchRunner(
        registry=registry,
        snapshotter=snapshotter,
        cleanup=cleanup,
        insecure_registry=insecure_registry,
    )

    if output_format == "csv":
        csv_headers = "timestamp,registry,repo,pull_elapsed(s),create_elapsed(s),run_elapsed(s),total_elapsed(s)"
        f.writelines(csv_headers + "\n")
        f.flush()

    for bench in benches:
        for _ in range(bench_times):
            pull_elapsed, create_elapsed, run_elapsed, _, _ = runner.run(bench)

            total_elapsed = f"{pull_elapsed + create_elapsed + run_elapsed: .6f}"
            timetamp = int(time.time() * 1000)
            pull_elapsed = f"{pull_elapsed: .6f}"
            create_elapsed = f"{create_elapsed: .6f}"
            run_elapsed = f"{run_elapsed: .6f}"

            if output_format == "json":
                row = {
                    "timestamp": timetamp,
                    "registry": runner.registry[:-1],
                    "repo": bench.name,
                    "pull_elapsed": pull_elapsed,
                    "create_elapsed": create_elapsed,
                    "run_elapsed": run_elapsed,
                    "total_elapsed": total_elapsed,
                }
                line = json.dumps(row)
            elif output_format == "csv":
                line = f"{timetamp},{runner.registry[:-1]},{bench.name},{pull_elapsed},{create_elapsed},{run_elapsed},{total_elapsed}"

            print(line)
            f.writelines(line + "\n")
            f.flush()

    f.close()


def bench_image(local_registry, insecure_local_registry, image, f: TextIOWrapper, snapshotter="overlayfs", flag=True):
    try:
        bench = copy.deepcopy(BenchRunner.ALL[image_repo(image)])
        tag = image_tag(image)
        if tag is not None:
            bench.set_tag(tag)
    except KeyError:
        logging.warning("image %s not supported, skip", image)
        exit(1)
    runner = BenchRunner(
        registry=local_registry,
        snapshotter=snapshotter,
        cleanup=True,
        insecure_registry=insecure_local_registry,
    )
    pull_elapsed, create_elapsed, run_elapsed, read_count, read_amount_total = runner.run(bench)
    total_elapsed = f"{pull_elapsed + create_elapsed + run_elapsed: .6f}"
    timetamp = int(time.time() * 1000)
    pull_elapsed = f"{pull_elapsed: .6f}"
    create_elapsed = f"{create_elapsed: .6f}"
    run_elapsed = f"{run_elapsed: .6f}"
    if flag:
        line = f"{timetamp},{runner.registry[:-1]},{bench.name},{pull_elapsed},{create_elapsed},{run_elapsed},{total_elapsed},{read_count},{read_amount_total}"
    else:
        line = f"{timetamp},{runner.registry[:-1]},{bench.name}_prefetchall,{pull_elapsed},{create_elapsed},{run_elapsed},{total_elapsed},{read_count},{read_amount_total}"
    f.writelines(line + "\n")
    f.flush()


if __name__ == "__main__":
    main()
    exit(0)
