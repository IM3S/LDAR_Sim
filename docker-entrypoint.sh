#!/bin/bash --login
# The --login ensures the bash configuration is loaded,
# enabling Conda..
conda activate ldar_sim_env
pip install orbit_predictor
pip install timezonefinder
export AWS_KEY=AKIAVZXPNFOVPRYFUWWR
export AWS_SEC=ZZl2zdpjm/jrcCNVPf7OjNYy58TIMWG11VXwKJMj
exec python /code/LDAR_Sim/src/ldar_sim_main.py --in_dir=./simulations

