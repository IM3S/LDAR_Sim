# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim site generator
# Purpose:     Gemerate sites for modelling
#
# Copyright (C) 2018-2021  Intelligent Methane Monitoring and Management System (IM3S) Group
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the MIT License as published
# by the Free Software Foundation, version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.

# You should have received a copy of the MIT License
# along with this program.  If not, see <https://opensource.org/licenses/MIT>.
#
# ------------------------------------------------------------------------------


import os
from pathlib import Path
import time
import pickle

from initialization.args import files_from_args, get_abs_path
from initialization.input_manager import InputManager
from initialization.virtual_world import gen_world

opening_msg = """
You are running LDAR-Sim version 2.0 an open sourced software (MIT) license.
It is continually being developed by the University of Calgary's Intelligent
Methane Monitoring and Management System (IM3S) Group.
Provide any issues, comments, questions, or recommendations to the IM3S by
adding an issue to https://github.com/LDAR-Sim/LDAR_Sim.git.

"""

if __name__ == '__main__':
    print(opening_msg)

    # Get route directory , which is parent folder of ldar_sim_main file
    # Set current working directory directory to root directory
    root_dir = Path(os.path.dirname(os.path.realpath(__file__))).parent
    os.chdir(root_dir)

    # --- Retrieve input parameters and parse ---
    parameter_filenames = files_from_args(root_dir)
    input_manager = InputManager()
    sim_params = input_manager.read_and_validate_parameters(parameter_filenames)

    # --- Assign local variabls
    in_dir = get_abs_path(sim_params['input_directory'])
    vm_label = sim_params['virtual_world']['label']

    gen_site_file_loc = root_dir / 'virtual_world'
    if not os.path.exists(gen_site_file_loc):
        os.makedirs(gen_site_file_loc)

    if not os.path.exists(gen_site_file_loc / vm_label):
        os.makedirs(gen_site_file_loc / vm_label)

    t0 = time.time()
    sites, weather = gen_world(sim_params, in_dir)
    print("Sites load time: {} s".format(round(time.time() - t0, 2)))

    print("exporting virtual world to {}/{}".format(gen_site_file_loc, vm_label))
    with open(gen_site_file_loc / vm_label / 'sites', "wb") as f:
        pickle.dump(sites, f)
    with open(gen_site_file_loc / vm_label / 'weather', "wb") as f:
        pickle.dump(weather, f)
    print("cool! cya")
