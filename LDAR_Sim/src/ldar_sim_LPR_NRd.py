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

import json
import multiprocessing as mp
import os
from copy import deepcopy
import shutil
from pathlib import Path

from initialization.args import files_from_args, get_abs_path
from initialization.input_manager import InputManager
from initialization.sims import create_sims
from initialization.sites import init_generator_files
from ldar_sim_run import ldar_sim_run
from out_processing.lpr_nrd_sens import BatchReporting, gen_active_leak_cnt
from utils.generic_functions import check_ERA5_file
from utils.sensitivity import yaml_to_dict
opening_msg = """
You are running LDAR-Sim version 2.0 an open sourced software (MIT) license.
It is continually being developed by the University of Calgary's Intelligent
Methane Monitoring and Management System (IM3S) Group.
Provide any issues, comments, questions, or recommendations to the IM3S by
adding an issue to https://github.com/LDAR-Sim/LDAR_Sim.git.

"""


def run_sims(sim_params, ref_program, base_program, prog_colors, prog_linestyles):
    # --- Run simulations (in parallel) --
    with mp.Pool(processes=sim_params['n_processes']) as p:
        sim_out = p.starmap(ldar_sim_run, simulations)

    # ---- Generate Outputs ----

    # Do batch reporting
    if sim_params['write_data']:
        # Create a data object...
        # cost_mit = cost_mitigation(sim_outputs, ref_program, base_program, out_dir)
        reporting_data = BatchReporting(
            out_dir, sim_params['start_date'],
            ref_program, base_program,
            sim_out[0]['meta']['site_samples'])
        reporting_data.batch_plots(prog_colors, prog_linestyles)
        gen_active_leak_cnt(sim_out, out_dir)
    return None


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
    out_dir = get_abs_path(sim_params['output_directory'])
    sens_parameters = yaml_to_dict(in_dir / 'OP_paper_1.yaml')
    programs_raw = sim_params.pop('programs')

    ref_program = None
    base_program = None

    programs = {}
    prog_colors = {}
    prog_linestyles = {}
    for pidx, program in programs_raw.items():
        for lidx, LPR in enumerate(sens_parameters['LPR']):
            for nidx, NRd in enumerate(sens_parameters['NRd']):
                new_prog = deepcopy(program)
                prog_name = "{}_L{}_N{}".format(pidx, str(LPR).zfill(2), str(NRd).zfill(3))
                if ref_program is None:
                    ref_program = prog_name
                if base_program is None:
                    base_program = prog_name
                new_prog.update({
                    'program_name': prog_name,
                    'NRd': NRd,
                })
                new_prog['emissions'].update({
                    'LPR': LPR/365
                })
                prog_colors.update({prog_name: sens_parameters['NRd_style'][nidx]})
                prog_linestyles.update({prog_name: sens_parameters['LPR_style'][lidx]})
                programs.update({prog_name: new_prog})

    # --- Run Checks ----
    check_ERA5_file(in_dir, programs)
    has_ref = ref_program in programs
    has_base = base_program in programs

    # --- Setup Output folder
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    input_manager.write_parameters(out_dir / 'parameters.yaml')

    # If leak generator is used and there are generated files, user is prompted
    # to use files, If they say no, the files will be removed
    if sim_params['pregenerate_leaks']:
        generator_dir = in_dir / "generator"
        init_generator_files(
            generator_dir, input_manager.simulation_parameters, in_dir, programs[base_program])
    else:
        generator_dir = None
    # --- Create simulations ---
    simulations = create_sims(sim_params, programs, generator_dir, in_dir, out_dir, input_manager)
    sim_out = run_sims(sim_params, ref_program, base_program, prog_colors, prog_linestyles)

    with open(out_dir / 'prog_table.json', 'w') as fp:
        json.dump(sim_out, fp)
