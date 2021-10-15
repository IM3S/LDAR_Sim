# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim main
# Purpose:     Interface for parameterizing and running LDAR-Sim.
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
import shutil
import datetime
import multiprocessing as mp
from pathlib import Path

from initialization.input_manager import InputManager
from initialization.args import files_from_args, get_abs_path
from initialization.build_sims import check_for_generator, build_sims
from utils.generic_functions import check_ERA5_file
from batch_reporting import BatchReporting
from ldar_sim_run import ldar_sim_run
from economics.cost_mitigation import cost_mitigation

if __name__ == '__main__':
    # Get route directory , which is parent folder of ldar_sim_main file
    # Set current working directory directory to root directory
    root_dir = Path(os.path.dirname(os.path.realpath(__file__))).parent
    os.chdir(root_dir)
    parameter_filenames = files_from_args(root_dir)
    input_manager = InputManager()
    simulation_parameters = input_manager.read_and_validate_parameters(parameter_filenames)
    # Assign appropriate local variables to match older way of inputting parameters
    input_directory = get_abs_path(simulation_parameters['input_directory'])
    output_directory = get_abs_path(simulation_parameters['output_directory'])
    programs = simulation_parameters.pop('programs')
    ref_program = simulation_parameters['reference_program']
    no_program = simulation_parameters['baseline_program']
    write_data = simulation_parameters['write_data']
    start_date = simulation_parameters['start_date']

    # -----------------------------Prepare model run----------------------------------
    # Check whether ERA5 data is already in the input directory and download data if not
    for p in programs:
        check_ERA5_file(input_directory, p['weather_file'])

    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)

    input_manager.write_parameters(output_directory / 'parameters.yaml')
    if simulation_parameters['pregenerate_leaks']:
        generator_folder = check_for_generator(input_directory)

    simulations = build_sims(
        programs,
        simulation_parameters,
        generator_folder,
        input_directory,
        output_directory)

    # The following can be used for debugging outside of the starmap
    # trg_sim_idx = next((index for (index, d) in enumerate(simulations)
    #                     if d[0]['program']['program_name'] == "P_air"), None)

    # Perform simulations in parallel
    with mp.Pool(processes=simulation_parameters['n_processes']) as p:
        res = p.starmap(ldar_sim_run, simulations)

    # Do batch reporting
    if write_data:
        # Create a data object...
        cost_mitigation = cost_mitigation(res, ref_program, no_program, output_directory)
        reporting_data = BatchReporting(
            output_directory, start_date, ref_program, no_program)
        if simulation_parameters['n_simulations'] > 1:
            reporting_data.program_report()
            if len(programs) > 1:
                reporting_data.batch_report()
                reporting_data.batch_plots()

    # Write metadata
    metadata = open(output_directory / '_metadata.txt', 'w')
    metadata.write(str(programs) + '\n' +
                   str(datetime.datetime.now()))

    metadata.close()
