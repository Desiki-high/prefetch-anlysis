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
            target_image = self.image_repo() + "_nydus:" + self.image_tag()
            if self.insecure_source_registry and self.insecure_target_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure --target-insecure"
            elif self.insecure_source_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure"
            elif self.insecure_target_registry:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --target-insecure"
            else:
                return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image}"
        else:
            target_image = self.image_repo() + "_nydus_prefetch:" + self.image_tag()
            if self.insecure_source_registry and self.insecure_target_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure --target-insecure"
            elif self.insecure_source_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure"
            elif self.insecure_target_registry:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --target-insecure"
            else:
                return f"cat {self.prefetch} | nydusify convert --prefetch-patterns --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image}"

    def convert(self):
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
              item["name"]).convert()


if __name__ == "__main__":
    main()
    exit(0)
