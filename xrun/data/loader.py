import gzip
from pathlib import Path
from timeit import default_timer as timer
from typing import Callable, Dict, Tuple

import numpy as np
from scipy.sparse.csr import csr_matrix


def load_census_dataset(file_path: str):
    print(f"Loading Census data from {file_path}...")
    start_time = timer()
    data = np.loadtxt(
        fname=file_path,
        dtype=np.double,
        delimiter=",",
        skiprows=1,
        unpack=False
    )
    end_time = timer()
    print(f"Loaded in {end_time - start_time:.2f} secs")
    return data[:,1:]


def load_tower_dataset(file_path: str):
    print(f"Loading Tower dataset from {file_path}...")
    start_time = timer()
    data = np.loadtxt(
        fname=file_path,
        dtype=np.double,
        delimiter=",",
        skiprows=0,
        unpack=False
    )
    end_time = timer()
    print(f"Loaded in {end_time - start_time:.2f} secs")
    
    D = 3
    N = int(data.shape[0] / D)
    return data.reshape((N, D))


def load_covertype_dataset(file_path: str):
    print(f"Loading Covertype dataset from {file_path}...")
    start_time = timer()
    data = np.loadtxt(
        fname=file_path,
        dtype=np.double,
        delimiter=",",
        skiprows=0,
        unpack=False
    )
    end_time = timer()
    print(f"Loaded in {end_time - start_time:.2f} secs")
    return data[:, 0:-1] # Skip the last column which is the classification column



def load_csv_dataset(input_path: str):
    dimensions = 0 # The `nonlocal dimensions` below in iter_func() binds to this variable.
    def iter_func():
        nonlocal dimensions
        with gzip.open(input_path,'rt') as f:
            for line in f:
                if len(line) > 0:
                    line = line.rstrip().split(",")
                    for item in line:
                        yield float(item)
            dimensions = len(line)

    print(f"Loading csv dataset from {input_path}...")
    start_time = timer()

    data = np.fromiter(iter_func(), dtype=np.double)
    data = data.reshape((-1, dimensions))
    end_time = timer()
    print(f"Loaded matrix of shape {data.shape} in {end_time - start_time:.2f} secs")
    return data


def load_dataset(input_path: str) -> object:
    loader_fn_map : Dict[str, Callable[[str], object]] = {
        "Tower": load_tower_dataset,
        "USCensus1990": load_census_dataset,
        "covtype": load_covertype_dataset,
    }
    for name_like, loader_fn in loader_fn_map.items():
        if name_like in input_path:
            return loader_fn(input_path)
    raise Exception(f"Cannot parse {input_path} because format is unknown.")
