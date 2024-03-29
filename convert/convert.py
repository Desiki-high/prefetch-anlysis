#!/usr/bin/env python3

import os
import sys
from argparse import ArgumentParser

import yaml


def exit(status):
    # cleanup
    sys.exit(status)


class Image:
    def __init__(self, source_registry, insecure_source_registry, target_registry, insecure_target_registry, image, prefetch=""):
        """
        the prefetch is the file path of prefetch list file,and it is optional
        """
        self.source_registry = source_registry
        self.insecure_source_registry = insecure_source_registry
        self.target_registry = target_registry
        self.insecure_target_registry = insecure_target_registry
        self.image = image
        self.prefetch = prefetch

    def image_repo(self):
        return self.image.split(":")[0]

    def image_tag(self) -> str:
        try:
            return self.image.split(":")[1]
        except IndexError:
            return None

    def convert_cmd(self):
        if self.prefetch == "":
            target_image = self.image_repo() + ":" + self.image_tag() + "_nydus"
            if self.insecure_source_registry and self.insecure_target_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure --target-insecure"
            elif self.insecure_source_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure"
            elif self.insecure_target_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --target-insecure"
            else:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image}"
        else:
            target_image = self.image_repo() + ":" + self.image_tag() + "_nydus_prefetch"
            if self.insecure_source_registry and self.insecure_target_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure --target-insecure"
            elif self.insecure_source_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure"
            elif self.insecure_target_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --target-insecure"
            else:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image}"

    def tag_convert(self):
        source_image = self.source_registry + "/" + self.image
        target_image = self.target_registry + "/" + self.image
        cmd = ""
        if self.insecure_source_registry:
            cmd = f"nerdctl pull {source_image} --insecure-registry"
        else:
            cmd = f"nerdctl pull {source_image}"
        rc = os.system(cmd)
        assert rc == 0
        tag_cmd = f"nerdctl tag {source_image} {target_image}"
        rc = os.system(tag_cmd)
        assert rc == 0
        if self.insecure_target_registry:
            cmd = f"nerdctl push {target_image} --insecure-registry"
        else:
            cmd = f"nerdctl push {target_image}"
        rc = os.system(cmd)
        assert rc == 0

    def nydus_convert(self):
        """
        convert oci image to nydus image (prefetchfile is optional)
        """
        print(self.convert_cmd())
        rc = os.system(self.convert_cmd())
        assert rc == 0


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-c',
        '--config',
        dest='config',
        type=str,
        required=True,
        help='Input YAML file that conlude the images')

    args = parser.parse_args()
    images = {}
    with open(args.config, 'r', encoding='utf-8') as f:
        try:
            images = yaml.load(stream=f, Loader=yaml.FullLoader)
        except Exception as inst:
            print('error reading config file')
            print(inst)
            exit(-1)
    for item in images["images"]:
        Image(images["source_registry"],
              images["insecure_source_registry"],
              images["target_registry"],
              images["insecure_target_registry"],
              item["name"]).nydus_convert()


def convert_nydus(source_registry: str, insecure_source_registry: bool, target_registry: str, insecure_target_registry: bool, image: str):
    """
    convert nydus image api
    """
    Image(source_registry,
          insecure_source_registry,
          target_registry,
          insecure_target_registry,
          image).nydus_convert()


def convert_nydus_prefetch(source_registry: str, insecure_source_registry: bool, target_registry: str, insecure_target_registry: bool, image: str, prefetch: str):
    """
    convert nydus with prefetch image api
    """
    Image(source_registry,
          insecure_source_registry,
          target_registry,
          insecure_target_registry,
          image, prefetch).nydus_convert()


def convert_oci(source_registry: str, insecure_source_registry: bool, target_registry: str, insecure_target_registry: bool, image: str):
    """
    convert oci image api
    """
    Image(source_registry,
          insecure_source_registry,
          target_registry,
          insecure_target_registry,
          image).tag_convert()


if __name__ == "__main__":
    main()
    exit(0)
