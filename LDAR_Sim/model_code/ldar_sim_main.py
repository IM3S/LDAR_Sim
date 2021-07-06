# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim main
# Purpose:     Interface for parameterizing and running LDAR-Sim.
#
# Copyright (C) 2018-2020  Thomas Fox, Mozhou Gao, Thomas Barchyn, Chris Hugenholtz
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
from pathlib import Path

from batch_reporting import BatchReporting
from ldar_sim_run import ldar_sim_run
from input_manager import InputManager
import pandas as pd
import os
import sys
import shutil
import datetime
import warnings
import multiprocessing as mp
from generic_functions import check_ERA5_file

if __name__ == '__main__':
    # ------------------------------------------------------------------------------
    # -----------------------------Read parameters----------------------------------
    parameter_filenames = sys.argv[1:]
    if len(parameter_filenames) == 0:
        print('No parameter files supplied? Parameter files must be supplied as arguments')
        print('Running the simulation with default programs for testing purposes')
        #parameter_filenames = ['..//inputs_template//P_ref.txt',
        #                       '..//inputs_template//P_aircraft.txt',
        #                       '..//inputs_template//P_truck.txt']
        parameter_filenames = ['..//sample_simulations//P_ref.yaml',
                               '..//sample_simulations//OGI.yaml']

    # Parse, map, validate parameters
    input_parameters = InputManager()
    parameters = input_parameters.read_and_validate_parameters(parameter_filenames = parameter_filenames)

    # -----------------------------Set up programs----------------------------------
    warnings.filterwarnings('ignore')    # Temporarily mute warnings

    # Check whether ERA5 data is already in the working directory and download data if not
    check_ERA5_file(parameters['wd'], parameters['weather_file'])

    if os.path.exists(parameters['output_directory']):
        shutil.rmtree(parameters['output_directory'])

    os.makedirs(parameters['output_directory'])

    # Write the parameters for the simulation to the output directory
    input_parameters.write_parameters(os.path.join(parameters['output_directory'], 'parameters.yaml'))

    # Set up simulation parameter files
    simulations = []
    for i in range(parameters['n_simulations']):
        for j in range(len(parameters['programs'])):
            opening_message = "Simulating program {} of {} ; simulation {} of {}".format(
                j + 1, len(parameters['programs']), i + 1, parameters['n_simulations']
            )
            simulations.append(
                [{'i': i, 'program': parameters['programs'][j],
                  'wd': parameters['wd'],
                  'output_directory':parameters['output_directory'],
                  'opening_message': opening_message,
                  'print_from_simulation': parameters['print_from_simulations']}])

    # Perform simulations in parallel
    with mp.Pool(processes=parameters['n_processes']) as p:
        res = p.starmap(ldar_sim_run, simulations)

    # Do batch reporting
    if parameters['write_data']:
        # Create a data object...
        reporting_data = BatchReporting(
            parameters['output_directory'], parameters['start_year'],
            parameters['spin_up'], parameters['reference_program'])
        if parameters['n_simulations'] > 1:
            reporting_data.program_report()
            if len(parameters['programs']) > 1:
                reporting_data.batch_report()
                reporting_data.batch_plots()

    # Write metadata
    with open(parameters['output_directory'] + '/_metadata.txt', 'w') as f:
        f.write(str(parameters['programs']) + '\n' + str(datetime.datetime.now()))

    # Write sensitivity analysis data on a program by program basis
    sa_df = pd.DataFrame(res)
    if 'program' in sa_df.columns:
        for program in sa_df['program'].unique():
            sa_out = sa_df.loc[sa_df['program'] == program, :]
            sa_outfile_name = os.path.join(parameters['wd'], 'sensitivity_analysis',
                                           'sensitivity_' + program + '.csv')
            sa_out.to_csv(sa_outfile_name, index=False)
