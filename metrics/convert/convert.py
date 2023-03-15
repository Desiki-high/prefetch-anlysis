#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2023 Yadong Ding
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import yaml
import os
from argparse import ArgumentParser


def exit(status):
    # cleanup
    sys.exit(status)


class Image:
    def __init__(self, source_registry, insecure_source_registry, target_registry, insecure_target_registry, image):
        self.source_registry = source_registry
        self.insecure_source_registry = insecure_source_registry
        self.target_registry = target_registry
        self.insecure_target_registry = insecure_target_registry
        self.image = image

    def image_name(self):
        return self.image.split(':')[0]

    def convert_cmd(self):
        target_image = self.image_name() + ":nydus"
        if self.insecure_source_registry and self.insecure_target_registry:
            return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure --target-insecure"
        elif self.insecure_source_registry:
            return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --source-insecure"
        elif self.insecure_target_registry:
            return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image} --target-insecure"
        else:
            return f"nydusify convert --source {self.source_registry}/{self.image} --target {self.target_registry}/{target_image}"

    def convert(self):
        rc = os.system(self.convert_cmd())
        assert rc == 0


def main():

    parser = ArgumentParser()
    parser.add_argument(
        '-i',
        '--input',
        dest='input',
        type=str,
        required=True,
        help='Input YAML file that conlude the images')

    args = parser.parse_args()
    images = {}
    with open(args.input, 'r', encoding='utf-8') as f:
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
