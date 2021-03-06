import os, subprocess, shutil, re

from timeit import default_timer as timer
from typing import List, Optional
from pathlib import Path

import pandas as pd
import numpy as np
import click
import numba

from sklearn.metrics import pairwise_distances, pairwise_distances_argmin_min
from scipy.sparse import linalg as sparse_linalg, issparse
from sklearn.utils import shuffle
from sklearn.utils.extmath import safe_sparse_dot

from xrun.gen import generate_random_seed
from xrun.data.loader import load_dataset
from xrun.data.run_info import RunInfo

KMEANS_PATH = "kmeans/bin/kmeans.exe"


def unzip_file(input_path: Path) -> Path:
    output_path = Path(os.path.splitext(input_path)[0])
    if not output_path.exists():
        print(f"Unzipping file {input_path}...")
        p = subprocess.Popen(
            args=["gunzip", "-k", str(input_path)],
            start_new_session=True
        )
        p.wait()
    assert(output_path.exists())
    return output_path


def compute_centers_via_external_kmeanspp(result_file_path: Path) -> Path:
    center_path = result_file_path.parent / "centers.txt"
    
    if center_path.exists() and center_path.stat().st_size > 0:
        return center_path

    if not os.path.exists(KMEANS_PATH):
        raise Exception(f"Program '{KMEANS_PATH}' cannot be found. You can build it: make -C kmeans")

    start_time = timer()

    with open(result_file_path, 'r') as f:
        line1 = next(f)  # Skip the first line
        line2 = next(f)  # Read the first point data to figure out dimensions

    # When counting the number of dimensions for points skip the
    # first entry as it is the weight of the point.
    d = len(line2.split(" ")) - 1  
    k = int(re.findall(r'-k(\d+)-', str(result_file_path))[0])
    random_seed = generate_random_seed()
    command = [
        KMEANS_PATH,
        str(result_file_path),
        str(k),
        str(d),
        str(center_path),
        "0",
        str(random_seed),
    ]
    proc = subprocess.Popen(
        args=command,
        start_new_session=True
    )
    proc.wait()
    end_time = timer()
    print(f"k-means++ centers computed in {end_time - start_time:.2f} secs")
    return center_path


def get_centers(result_file_path: Path) -> np.ndarray:
    for i in range(10):
        centers_file_path = compute_centers_via_external_kmeanspp(result_file_path)
        centers = np.loadtxt(fname=centers_file_path, dtype=np.double, delimiter=' ', skiprows=0)
        center_weights = centers[:,0] 
        center_points = centers[:,1:]

        if np.any(np.isnan(center_points)):
            print("Detected NaN values in the computed centers.")

            center_nan_count = np.count_nonzero(np.isnan(center_points))
            center_inf_count = np.count_nonzero(np.isinf(center_points))

            print(f"- NaN Count: {center_nan_count}")
            print(f"- Inf Count: {center_inf_count}")
            print(f"- NaN: {np.argwhere(np.isnan(center_points))}")
            
            print(f"Removing {centers_file_path}...")
            os.remove(centers_file_path)
        else:
            return center_points

    raise Exception(f"Failed to find centers without NaN values. Giving up after {i+1} iterations!")


datasets = dict()

def load_original_data(run_info: RunInfo):
    dataset_name = run_info.dataset

    if dataset_name not in datasets:
        dataset = load_dataset(run_info.dataset_path)
        datasets[dataset_name] = dataset

    return datasets[dataset_name]


def compute_real_cost(data_points: np.ndarray, center_points: np.ndarray, cost_file_path: Path) -> Path:
    if cost_file_path.exists():
        return cost_file_path

    print("Computing real cost... ", end="")

    D = pairwise_distances(data_points, center_points, metric="sqeuclidean")

    # For each point (w, p) in S, find the distance to its closest center
    dist_closest_centers = np.min(D, axis=1)

    # Weigh the distances and sum it all up
    cost = np.sum(dist_closest_centers)

    print(f"Computed real cost: {cost}")
    
    with open(cost_file_path, "w") as f:
        f.write(str(cost))
    return cost_file_path


def compute_coreset_costs(coreset: np.ndarray, center_points: np.ndarray, cost_file_path: Path) -> Path:
    if cost_file_path.exists():
        return cost_file_path

    print("Computing coreset cost... ", end='')
    coreset_weights = coreset[:,0]
    coreset_points = coreset[:,1:]

    # Distances between all corset points and center points
    D = pairwise_distances(coreset_points, center_points, metric="sqeuclidean")

    # For each point (w, p) in S, find the distance to its closest center
    dist_closest_centers = np.min(D, axis=1)

    # Weigh the distances and sum it all up
    cost = np.sum(coreset_weights * dist_closest_centers)

    print(f"Computed coreset cost: {cost}")

    with open(cost_file_path, "w") as f:
        f.write(str(cost))
    return cost_file_path


def load_run_info(experiment_dir: Path) -> Optional[RunInfo]:
    run_file_paths = list(experiment_dir.glob("*.json"))
    if len(run_file_paths) != 1:
        # print(f"Expected a single run file in {experiment_dir} but found {len(run_file_paths)} files.")
        return None
    return RunInfo.load_json(run_file_paths[0])


def find_unprocesses_result_files(results_dir: str) -> List[Path]:
    search_dir = Path(results_dir)
    output_paths = list(search_dir.glob('**/results.txt.gz'))
    return_paths = []
    for file_path in output_paths:
        costs_computed = np.all([
            os.path.exists(file_path.parent / cfn)
            for cfn in [
                "real_cost.txt", "coreset_cost.txt",
            ]
        ])
        run_info = load_run_info(file_path.parent)
        if not costs_computed and run_info is not None:
            return_paths.append(file_path)
    return return_paths


def load_cost_from_file(file_path: Path):
    with open(file_path, "r") as f:
        return float(f.read())


def compute_real_dataset_costs(run_info: RunInfo, coreset_path: Path) -> None:
    experiment_dir = coreset_path.parent

    coreset_cost_path = experiment_dir / f"coreset_cost.txt"
    real_cost_path = experiment_dir / f"real_cost.txt"
    
    if coreset_cost_path.exists() and real_cost_path.exists():
        print("Costs are already computed!")
        return

    unzipped_result_path = unzip_file(coreset_path)
    original_data_points = load_original_data(run_info)

    coreset = np.loadtxt(fname=unzipped_result_path, dtype=np.double, delimiter=' ', skiprows=1)

    # Compute a candidate solution on the coreset
    solution = get_centers(unzipped_result_path)

    compute_coreset_costs(
        coreset=coreset,
        center_points=solution,
        cost_file_path=coreset_cost_path,
    )

    compute_real_cost(
        data_points=original_data_points,
        center_points=solution,
        cost_file_path=real_cost_path,
    )

    # Compute distortion
    coreset_cost = load_cost_from_file(coreset_cost_path)
    real_cost = load_cost_from_file(real_cost_path)
    distortion = max(coreset_cost/real_cost, real_cost/coreset_cost)
    print(f"Distortion: {distortion:0.5f}")
    with open(experiment_dir / f"distortion.txt", "w") as f:
        f.write(str(distortion))


@click.command(help="Compute costs for coresets.")
@click.option(
    "-r",
    "--results-dir",
    type=click.STRING,
    required=True,
)
def main(results_dir: str) -> None:
    output_paths = find_unprocesses_result_files(results_dir)
    total_files = len(output_paths)
    for index, result_path in enumerate(output_paths):
        print(f"Processing file {index+1} of {total_files}: {result_path}")
        experiment_dir = result_path.parent

        run_info = load_run_info(experiment_dir)
        if run_info is None:
            print("Cannot process results file because run file is missing.")
            continue

        if not os.path.exists(run_info.dataset_path):
            print(f"Dataset path: {run_info.dataset_path} cannot be found. Skipping...")
            continue

        compute_real_dataset_costs(
            run_info=run_info,
            coreset_path=result_path,
        )

        print(f"Done processing file {index+1} of {total_files}.")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
