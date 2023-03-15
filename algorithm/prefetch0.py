import csv
import os
from functools import cmp_to_key


def read_csv(csv_path):
    file_dict = {}
    file_list = []
    ID = 0
    with open(csv_path, 'r') as fp:
        reader = csv.DictReader(fp)
        for x in reader:
            temp = {}
            temp['file_path'] = x['file_path']
            file_list.append(x['file_path'])
            temp['file_size'] = int(x['file_size'])
            # temp['latency'] = int(x['latency'])
            temp['first_access_time'] = int(x['first_access_time'])
            temp['access_times'] = int(x['access_times'])
            file_dict[ID] = temp
            ID += 1
    return file_dict, file_list


if __name__ == '__main__':
    root = 'data'
    dirs = os.listdir(root)
    for dir in dirs:
        root_dir = os.path.join(root, dir)
        files = os.listdir(root_dir)
        print(os.path.join(root_dir, files[0]))
        file_dict0, file_list = read_csv(os.path.join(root_dir, files[0]))
        prefetch_list = []
        with open('prefetch_list_fake/{}_fake.txt'.format(dir), 'w')as f:
            file_index_list = list(file_dict0.keys())


            def comp(a, b):
                if file_dict0[a]['first_access_time'] < file_dict0[b]['first_access_time']:
                    return -1
                else:
                    return 1


            file_index_list.sort(key=cmp_to_key(comp))
            print(file_index_list)
            for k in file_index_list:
                temp = file_dict0[k]['file_path']
                prefetch_list.append(temp)
                f.write(temp + '\n')

        # todo:得到用时最短的prefetch_list

