import os, requests, subprocess, json, shutil, time
from typing import List, Optional
from timeit import default_timer as timer

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import click
from tqdm import tqdm

KNOWN_ALGORITHMS = [
    "sensitivity-sampling",
    "group-sampling",
    "uniform-sampling",
]

KNOWN_DATASETS = [
    "covertype",
    "census",
    "tower",
]

MT_PATH = "mt/bin/mt.exe"


def generate_random_seed() -> int:
    # Calling mt.exe to generate a random seed quickly results 
    # in the same random seed. So pause for a second for each
    # generation.
    if not os.path.exists(MT_PATH):
        raise Exception(f"Random seed generator '{MT_PATH}' cannot be found. You can build it: make -C mt")
    time.sleep(1)
    p = subprocess.run([MT_PATH], stdout=subprocess.PIPE)
    return int(p.stdout)


def validate_algorithms(ctx, param, value):
    if value is None or value == "all":
        return KNOWN_ALGORITHMS
    ret_val = []
    for s in value.split(","):
        if s in ["ss", "sensitivity", "sensitivity-sampling"]:
            ret_val.append("sensitivity-sampling")
        elif s in ["gs", "group", "group-sampling"]:
            ret_val.append("group-sampling")
        elif s in ["us", "uniform", "uniform-sampling"]:
            ret_val.append("uniform-sampling")
        elif s in KNOWN_ALGORITHMS:
            ret_val.append(s)
        else:
            raise Exception(f"Known algorithm: {s}")
    return ret_val


def validate_datasets(ctx, param, value):
    if value is None or value == "all":
        return KNOWN_DATASETS
    ret_val = []
    for s in value.split(","):
        if s in ["cov", "covertype"]:
            ret_val.append("covertype")
        elif s in ["cen", "census"]:
            ret_val.append("census")
        elif s in ["t", "to", "tower"]:
            ret_val.append("tower")
        elif s in KNOWN_DATASETS:
            ret_val.append(s)
        else:
            raise Exception(f"Known dataset: {s}")
    return ret_val
        

@click.command(help="Generates experiment files.")
@click.option(
    "-s",
    "--iter-start",
    type=click.INT,
    required=True,
)
@click.option(
    "-e",
    "--iter-end",
    type=click.INT,
    default=-1,
    required=False,
)
@click.option(
    "-c",
    "--coreset-size-multiple",
    type=click.INT,
    required=True,
)
@click.option(
    "-a",
    "--algorithms",
    type=click.STRING,
    required=False,
    default=None,
    callback=validate_algorithms
)
@click.option(
    "-d",
    "--datasets",
    type=click.STRING,
    required=False,
    default=None,
    callback=validate_datasets
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Recreate files."
)
def main(iter_start: int, iter_end: Optional[int], coreset_size_multiple: int, algorithms: List[str], datasets: List[str], force: bool) -> None:
    if not os.path.exists(MT_PATH):
        print(f"Random seed generator '{MT_PATH}' cannot be found. You can build it: make -C mt")
        return
    
    if iter_end is None or iter_end < iter_start:
        iter_end = iter_start

    dataset_k_ranges = {
        "census": [10, 20, 30, 40, 50],
        "covertype": [10, 20, 30, 40, 50],
        "tower": [20, 40, 60, 80, 100],
    }

    ready_dir = Path("data/queue/ready")
    if not ready_dir.exists():
        os.makedirs(ready_dir)
    for dataset, k_values in dataset_k_ranges.items():
        if dataset not in datasets:
            continue
        for algo in algorithms:
            for k in k_values:
                for i in range(iter_start, iter_end+1):
                    m = coreset_size_multiple * k
                    random_seed = generate_random_seed()
                    print(f"Random seed {random_seed}")
                    exp_details = {
                        "iteration": i,
                        "algorithm": algo,
                        "dataset": dataset,
                        "k": k,
                        "m": m,
                        "randomSeed": random_seed,
                    }
                    file_path = ready_dir / f"{i:03}-{dataset}-{algo}-k{k}-m{m}.json"
                    if force or not file_path.exists():
                        print(f"Writing {file_path}...")
                        with open(file_path, "w") as f:
                            json.dump(exp_details, f, indent=4)
                    else:
                        print(f"File already exists {file_path}. Skipping...")

if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
