import copy
import csv
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
    optimize sorted list
    """
    file_dict, file_list = sort_list(csv_path)
    ino_dict = read_ino_csv(ino_csv_path)
    time = 0
    final = copy.deepcopy(file_list)
    for i in file_list:
        if file_dict[i]['first_access_time'] < time + ino_dict[file_dict[i]['ino']]['latency']:
            final.remove(i)
        else:
            time += ino_dict[file_dict[i]['ino']]['latency']
    return final


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
    optimized_list = optimize_list(csv_path, ino_csv_path)
    to_txt(optimized_list, 'algorithm/out.txt')
    return optimized_list


if __name__ == '__main__':
    optimized_list = get_prefetch_list('2023-03-17-19_54_53.csv', '2023-03-17-19_54_53_ino.csv')
    print(optimized_list)