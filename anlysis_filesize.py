#!/usr/bin/env python3

import matplotlib.pyplot as plt
import pandas as pd


def main():
    df = pd.read_csv("data/wordpress:php8.2_nydus/2023-03-28-15:30:35.csv")

    def classify(x):
        if x <= 1024:
            return "<1K"
        if x <= 16 * 1024:
            return "~16K"
        if x <= 32 * 1024:
            return "~32K"
        if x <= 64 * 1024:
            return "~64K"
        if x <= 128 * 1024:
            return "~128K"
        if x <= 256 * 1024:
            return "~256K"
        if x <= 512 * 1024:
            return "~512K"
        if x <= 1024 * 1024:
            return "~1M"
        if x <= 2 * 1024 * 1024:
            return "~2M"
        if x <= 4 * 1024 * 1024:
            return "~4M"
        return ">4M"

    order = ["<1K", "~16K", "~32K", "~64K", "~128K", "~256K", "~512K", "~1M", "~2M", "~4M", ">4M"]
    df["c_file_size"] = df["file_size"].apply(classify)

    # data = df.groupby("c_file_size")["file_size"].sum()

    data = df["c_file_size"].value_counts().reindex(order)

    plt.bar(data.index, data.values)

    # Add labels to the top of each bar
    for i, v in enumerate(data.values):
        plt.text(i, v+10, str(v), ha='center')

    plt.savefig("file_size.png")


if __name__ == "__main__":
    main()
