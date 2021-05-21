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
import pandas as pd
import os
import sys
import datetime
import warnings
import multiprocessing as mp
from generic_functions import check_ERA5_file, read_parameter_file

if __name__ == '__main__':
    # ------------------------------------------------------------------------------
    # -----------------------------Global parameters--------------------------------
    parameter_files = sys.argv[1:]
    if len(parameter_files) == 0:
        print('No parameter files supplied? Parameter files must be supplied as arguments')
        print('Loading default parameters: default_parameters.yaml')
        parameter_files = ['..//inputs_template//default_parameters.yaml']

    parameters = {}
    for parameter_file in parameter_files:
        parameters.update(read_parameter_file(parameter_file))

    # Set internal working directories
    src_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    src_dir = str(src_dir_path)
    root_dir = str(src_dir_path.parent)
    parameters['wd'] = os.path.abspath(parameters['wd']) + '//'
    parameters['output_directory'] = os.path.abspath(parameters['output_directory']) + '//'

    # -----------------------------Set up programs----------------------------------
    warnings.filterwarnings('ignore')  # Temporarily mute warnings
    for program in parameters['programs']:
        for parameter_file in parameters['programs'][program]['parameter_files']:
            # Accumulate parameters for each program
            if not os.path.isabs(parameter_file):
                parameter_file = os.path.join(parameters['wd'], parameter_file)

            parameters['programs'][program].update(read_parameter_file(parameter_file))

        # Accumulate methods from method files
        if 'method_files' in parameters['programs'][program]:
            for method_file in parameters['programs'][program]['method_files']:
                if not os.path.isabs(method_file):
                    method_file = os.path.join (parameters['wd'], method_file)

                parameters['programs'][program]['methods'].update(read_parameter_file(method_file))

    # Check whether ERA5 data is already in the working directory and download data if not
    check_ERA5_file(parameters['wd'], parameters['programs'][parameters['reference_program']]['weather_file'])

    if not os.path.exists(parameters['output_directory']):
        os.makedirs(parameters['output_directory'])

    # Set up simulation parameter files
    simulations = []
    for i in range(parameters['n_simulations']):
        for program in parameters['simulation_programs']:
            opening_message = "Simulating program {}; simulation {} of {}".format(
                program, i + 1, parameters['n_simulations']
            )
            simulations.append(
                [{'i': i, 'program': parameters['programs'][program],
                  'wd': parameters['wd'],
                  'output_directory': parameters['output_directory'],
                  'opening_message': opening_message,
                  'print_from_simulation': parameters['print_from_simulations']}])

    # ldar_sim_run(simulations[1][0])
    # Perform simulations in parallel
    with mp.Pool(processes = parameters['n_processes']) as p:
        res = p.starmap(ldar_sim_run, simulations)

    # Do batch reporting
    if parameters['write_data']:
        # Create a data object...
        reporting_data = BatchReporting(
            parameters['output_directory'], parameters['programs'][parameters['reference_program']]['start_year'],
            parameters['spin_up'], parameters['reference_program'])
        if parameters['n_simulations'] > 1:
            reporting_data.program_report()
            if len(parameters) > 1:
                reporting_data.batch_report()
                reporting_data.batch_plots()

    # Write metadata
    metadata = open(parameters['output_directory'] + '/metadata.txt', 'w')
    metadata.write(str(list(parameters['programs'].values())) + '\n' +
                   str(datetime.datetime.now()))

    metadata.close()

    # Write sensitivity analysis data on a program by program basis
    sa_df = pd.DataFrame(res)
    if 'program' in sa_df.columns:
        for program in sa_df['program'].unique():
            sa_out = sa_df.loc[sa_df['program'] == program, :]
            sa_outfile_name = os.path.join(parameters['wd'], 'sensitivity_analysis',
                                           'sensitivity_' + program + '.csv')
            sa_out.to_csv(sa_outfile_name, index=False)
