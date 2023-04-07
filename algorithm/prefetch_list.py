#!/usr/bin/env python3
import copy
import csv
import math
from functools import cmp_to_key
from typing import Tuple


def read_csv(csv_path: str) -> dict:
    """
    .csv to dictionary
    """
    file_dict = {}
    with open(csv_path, 'r') as fp:
        reader = csv.DictReader(fp)
        for x in reader:
            temp = {}
            temp['ino'] = x['ino']
            temp['file_size'] = int(x['file_size'])
            # temp['latency'] = int(x['latency'])
            temp['first_access_time'] = int(x['first_access_time'])
            temp['access_times'] = int(x['access_times'])
            file_dict[x['file_path']] = temp
    return file_dict


def read_csv2(csv_path: str) -> dict:
    """
    .csv to dictionary, delete >128k
    """
    file_dict = {}
    with open(csv_path, 'r') as fp:
        reader = csv.DictReader(fp)
        for x in reader:
            if int(x['file_size']) > 128*1024:
                continue
            temp = {}
            temp['ino'] = x['ino']
            temp['file_size'] = int(x['file_size'])
            # temp['latency'] = int(x['latency'])
            temp['first_access_time'] = int(x['first_access_time'])
            temp['access_times'] = int(x['access_times'])
            file_dict[x['file_path']] = temp
    return file_dict


def read_ino_csv(ino_csv_path: str) -> dict:
    """
    ino.csv to dictionary
    """
    ino_dict = {}
    with open(ino_csv_path, 'r') as fp:
        reader = csv.DictReader(fp)
        for x in reader:
            if x['ino'] in ino_dict.keys():
                ino_dict[x['ino']]['size'] += int(x['size'])
                ino_dict[x['ino']]['latency'] += int(x['latency'])
                if ino_dict[x['ino']]['ino_access_time'] > x['ino_access_time']:
                    ino_dict[x['ino']]['ino_access_time'] = x['ino_access_time']
            else:
                temp = {}
                temp['size'] = int(x['size'])
                temp['latency'] = int(x['latency'])
                temp['ino_access_time'] = x['ino_access_time']
                ino_dict[x['ino']] = temp
    return ino_dict


def sort_list(csv_path: str) -> Tuple[dict, list]:
    """
    sort access_files
    """
    file_dict = read_csv(csv_path)
    file_list = list(file_dict.keys())

    def comp(a, b):
        if file_dict[a]['first_access_time'] < file_dict[b]['first_access_time']:
            return -1
        else:
            return 1

    file_list.sort(key=cmp_to_key(comp))

    return file_dict, file_list


def optimize_list(csv_path: str, ino_csv_path: str) -> list:
    """
    optimize sorted list - only sort
    """
    file_dict, file_list = sort_list(csv_path)

    return file_list


def optimize_list2(csv_path: str, ino_csv_path: str) -> list:
    """
    optimize sorted list - delete max 1%
    """
    file_dict, file_list = sort_list(csv_path)
    ino_dict = read_ino_csv(ino_csv_path)
    final = copy.deepcopy(file_list)

    def comp_size(a, b):
        if file_dict[a]['file_size'] < file_dict[b]['file_size']:
            return -1
        else:
            return 1

    file_list.sort(key=cmp_to_key(comp_size))
    temp = file_list[math.ceil(0.99*len(file_list)):]
    for i in temp:
        final.remove(i)

    return final


def optimize_list3(csv_path: str, ino_csv_path: str) -> list:
    """
    optimize sorted list - delete Σino<80%
    """
    file_dict, file_list = sort_list(csv_path)
    ino_dict = read_ino_csv(ino_csv_path)
    final = copy.deepcopy(file_list)
    for i in file_list:
        if ino_dict[file_dict[i]['ino']]['size'] / file_dict[i]['file_size'] < 0.8:
            final.remove(i)
    return final


def optimize_list4(csv_path: str, ino_csv_path: str) -> list:
    """
    optimize sorted list  delete max 1% where Σino<80%
    """
    file_dict, file_list = sort_list(csv_path)
    ino_dict = read_ino_csv(ino_csv_path)
    final = copy.deepcopy(file_list)

    def comp_size(a, b):
        if file_dict[a]['file_size'] < file_dict[b]['file_size']:
            return -1
        else:
            return 1

    file_list.sort(key=cmp_to_key(comp_size))
    temp = file_list[math.ceil(0.99*len(file_list)):]

    for i in temp:
        if ino_dict[file_dict[i]['ino']]['size'] / file_dict[i]['file_size'] < 0.8:
            final.remove(i)
    return final


def optimize_list5(csv_path: str, ino_csv_path: str) -> list:
    """
    optimize sorted list put max 1% forward
    """
    file_dict, file_list = sort_list(csv_path)
    ino_dict = read_ino_csv(ino_csv_path)
    final = copy.deepcopy(file_list)

    def comp_size(a, b):
        if file_dict[a]['file_size'] < file_dict[b]['file_size']:
            return -1
        else:
            return 1

    file_list.sort(key=cmp_to_key(comp_size))
    t = file_list[math.ceil(0.99*len(file_list)):]
    for i in t:
        final.remove(i)
    temp = t + final

    return temp


def to_txt(file_list: list, outpath: str):
    """
    prefetch_list to txt
    """
    with open(outpath, 'w')as f:
        for k in file_list:
            f.write(k + '\n')


def get_prefetch_list(csv_path: str, ino_csv_path: str) -> list:
    """
    get prefetch_list
    """
    # optimized_list = optimize_list(csv_path, ino_csv_path)
    # optimized_list = optimize_list2(csv_path, ino_csv_path)
    # optimized_list = optimize_list3(csv_path, ino_csv_path)
    optimized_list = optimize_list4(csv_path, ino_csv_path)
    # optimized_list = optimize_list5(csv_path, ino_csv_path)
    to_txt(optimized_list, '/root/project/prefetch-acceleration/algorithm/out.txt')
    return optimized_list


if __name__ == '__main__':
    optimized_list = get_prefetch_list(
        '/root/project/prefetch-acceleration/data/wordpress:php8.2_nydus/2023-03-28-15:30:35.csv', '/root/project/prefetch-acceleration/data/wordpress:php8.2_nydus/2023-03-28-15:30:35_ino.csv')
    print(optimized_list)
