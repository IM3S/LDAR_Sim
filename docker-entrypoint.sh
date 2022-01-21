#!/bin/bash --login
# The --login ensures the bash configuration is loaded,
# enabling Conda..
conda activate ldar_sim_env
# pip install orbit_predictor
pip install timezonefinder
exec python /code/LDAR_Sim/src/ldar_sim_main.py --in_dir=./simulations

