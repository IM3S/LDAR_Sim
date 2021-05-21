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
import datetime
import warnings
import multiprocessing as mp
from generic_functions import check_ERA5_file, read_parameter_file

if __name__ == '__main__':
    # ------------------------------------------------------------------------------
    # -----------------------------Global parameters--------------------------------
    src_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    src_dir = str(src_dir_path)
    root_dir = str(src_dir_path.parent)
    wd = os.path.abspath(root_dir) + "/inputs_template/"
    output_directory = os.path.abspath(root_dir) + "/outputs/"
    parameters = read_parameter_file(os.path.join(wd, 'parameters.txt'))

    # -----------------------------Set up programs----------------------------------
    warnings.filterwarnings('ignore')  # Temporarily mute warnings
    for program in parameters['programs']:
        for parameter_file in parameters['programs'][program]['parameter_files']:
            # Accumulate parameters for each program
            filename = os.path.join(wd, parameter_file)
            parameters['programs'][program].update(read_parameter_file(filename))

    n_processes = parameters['programs'][parameters['reference_program']]['n_processes']
    print_from_simulations = parameters['programs'][parameters['reference_program']]['print_from_simulations']
    n_simulations = parameters['programs'][parameters['reference_program']]['n_simulations']
    spin_up = parameters['programs'][parameters['reference_program']]['spin_up']
    write_data = parameters['programs'][parameters['reference_program']]['write_data']

    # Check whether ERA5 data is already in the working directory and download data if not
    check_ERA5_file(wd, parameters['programs'][parameters['reference_program']]['weather_file'])

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Set up simulation parameter files
    simulations = []
    for i in range(n_simulations):
        for program in parameters['programs']:
            opening_message = "Simulating program {}; simulation {} of {}".format(
                program, i + 1, n_simulations
            )
            simulations.append(
                [{'i': i, 'program': parameters['programs'][program],
                  'wd': wd,
                  'output_directory': output_directory,
                  'opening_message': opening_message,
                  'print_from_simulation': print_from_simulations}])

    # ldar_sim_run(simulations[1][0])
    # Perform simulations in parallel
    with mp.Pool(processes = n_processes) as p:
        res = p.starmap(ldar_sim_run, simulations)

    # Do batch reporting
    if write_data:
        # Create a data object...
        reporting_data = BatchReporting(
            output_directory, parameters['programs'][parameters['reference_program']]['start_year'],
            spin_up, parameters['reference_program'])
        if n_simulations > 1:
            reporting_data.program_report()
            if len(parameters) > 1:
                reporting_data.batch_report()
                reporting_data.batch_plots()

    # Write metadata
    metadata = open(output_directory + '/metadata.txt', 'w')
    metadata.write(str(list(parameters.values())) + '\n' +
                   str(datetime.datetime.now()))

    metadata.close()

    # Write sensitivity analysis data on a program by program basis
    sa_df = pd.DataFrame(res)
    if 'program' in sa_df.columns:
        for program in sa_df['program'].unique():
            sa_out = sa_df.loc[sa_df['program'] == program, :]
            sa_outfile_name = os.path.join(wd, 'sensitivity_analysis',
                                           'sensitivity_' + program + '.csv')
            sa_out.to_csv(sa_outfile_name, index = False)
