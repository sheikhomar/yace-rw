# Coreset Algorithms on Real-World Data Sets

## Getting Started

Remember to install the prerequisite libraries and tools:

```bash
./install_prerequisites.sh
```

The MT project can be built with Make:

```bash
make -C mt
```

The k-means++ tool can be built with Make:

```bash
make -C kmeans
```

The GS project can be built with CMake:

```bash
sudo apt-get update
sudo apt-get install -y ninja-build
cmake -S gs -B gs/build -G "Ninja"
cmake --build gs/build
```

## Running Experiments

```bash
pyenv install
poetry install
poetry run python -m xrun.gen -s 0 -e 9 -a ss,gs,us -d tower,census,covertype -c 200
poetry run python -m xrun.go -o data/experiments -m 1
poetry run python -m xrun.calc_costs -r data/experiments
```
