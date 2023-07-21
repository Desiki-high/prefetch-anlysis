#!/usr/bin/env python3

import argparse

import matplotlib.pyplot as plt
import pandas as pd


def draw(filename_path, dest_path="bench.png"):
    data = pd.read_csv(filename_path)
    data.columns = ["timestamp", "registry", "repo", "pull_elapsed(s)", "create_elapsed(s)", "run_elapsed(s)", "total_elapsed(s)", "read_count", "read_amount_total"]
    image = data["repo"][0]
    if len(data) == 7:
        data["repo"] = ["oci", "nydus_no_pf", "nydus_all_pf", "nydus_alg_pf", "bacth-256k", "batch-512k", "batch-1024k"]
    else:
        data["repo"] = ["oci", "nydus_no_pf", "nydus_all_pf", "nydus_alg_pf"]

    fig = plt.figure(figsize=(12, 9))
    plt.suptitle(f"Performance comparison of different {image}", fontsize=18)

    axes = plt.subplot(2, 2, 1)
    plt.bar(data["repo"], data["pull_elapsed(s)"], width=0.6, color=["red", "green", "blue", "black"])
    plt.ylabel("Pull_elapsed(s)", fontsize=14)
    plt.xticks([], fontsize=12)
    for a, b in zip(data["repo"], data["pull_elapsed(s)"]):
        plt.text(a, b, f'{b:.3f}', ha='center', va='bottom', fontsize=12)

    axes = plt.subplot(2, 2, 2)
    if len(data) == 6:
        plt.bar(data["repo"], data["create_elapsed(s)"], width=0.6, color=["red", "green", "blue", "black", "purple", "orange"])
    else:
        plt.bar(data["repo"], data["create_elapsed(s)"], width=0.6, color=["red", "green", "blue", "black"])

    plt.ylabel("Create_elapsed(s)", fontsize=14)
    plt.xticks([], fontsize=12)
    for a, b in zip(data["repo"], data["create_elapsed(s)"]):
        plt.text(a, b, f'{b:.3f}', ha='center', va='bottom', fontsize=12)

    axes = plt.subplot(2, 2, 3)
    plt.bar(data["repo"], data["run_elapsed(s)"], width=0.6, color=["red", "green", "blue", "black"])
    plt.ylabel("Run_elapsed(s)", fontsize=14)
    plt.xticks([], fontsize=12)
    for a, b in zip(data["repo"],  data["run_elapsed(s)"]):
        plt.text(a, b, f'{b:.3f}', ha='center', va='bottom', fontsize=12)

    axes = plt.subplot(2, 2, 4)
    plt.bar(data["repo"], data["total_elapsed(s)"], width=0.6, color=["red", "green", "blue", "black"], label=data["repo"])
    plt.ylabel("Total_elapsed(s)", fontsize=14)
    plt.xticks([], fontsize=12)
    for a, b in zip(data["repo"], data["total_elapsed(s)"]):
        plt.text(a, b, f'{b:.3f}', ha='center', va='bottom', fontsize=12)

    plt.subplots_adjust(left=0.1, bottom=0.1, right=0.9, top=0.85)

    lines, labels = axes.get_legend_handles_labels()
    fig.legend(lines, labels, loc='upper right', fontsize=14)
    plt.savefig(dest_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Handle data of bench, convert csv to png"
    )
    parser.add_argument(
        "-f", type=str, default="bench.csv", help="cvs file"
    )
    args = parser.parse_args()
    draw(args.f)
