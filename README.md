# SkipHash - A distirbuted hash table on top of a visualized Skip+ graph

## On this project

This project was created for a distributed algorithms and data structures lecture held by Prof. Dr. Scheideler at Paderborn University in summer term 2018. We reference the lecture slides in some files, however the general principles used are also explained in [this paper](https://dl.acm.org/citation.cfm?id=2629695).

## Setup

Make sure you have python 3.x with pipenv installed. For visualization, you will need Gtk3 too. After cloning you can simply run `make init` for pipenv to create a new virtual environment and install the dependencies into it. If you want to, you can also execute `make dev` in order to install the development dependencies.

## Running the project

For standalone use, executing `pipenv run python -m skiphash -h` in the project directory will provide you with information on the command line options.
When using the distributed hash table in your own project, look at the distrhash testcase [here](skiphash/test/test_distrhash.py) for examples.
