import os
import fnmatch
import pickle
from copy import deepcopy

from initialization.sites import generate_sites, regenerate_sites
from initialization.preseed import gen_seed_timeseries


def check_for_generator(input_directory):
    # If leak generator is used and there are generated files, user is prompted
    # to use files, If they say no, the files will be removed
    generator_folder = input_directory / "generator"
    if not os.path.exists(generator_folder):
        os.mkdir(generator_folder)
    gen_files = fnmatch.filter(os.listdir(generator_folder), '*.p')
    if len(gen_files) > 0:
        print('\n --- \n pregenerated data exists, do you want to use (y/n)?' +
              ' "n" will remove contents of generated data folder.')
        gen_prompt = input()
        if gen_prompt.lower() == 'n':
            for file in gen_files:
                os.remove(generator_folder / file)
    return generator_folder


def build_sims(programs, sim_params, gen_dir, in_dir, out_dir):
    simulations = []
    pregen = sim_params['pregenerate_leaks']
    for i in range(sim_params['n_simulations']):
        if pregen:
            file_loc = gen_dir / "pregen_{}_{}.p".format(i, 0)
            # If there is no pregenerated file for the program
            if not os.path.isfile(file_loc):
                sites, leak_timeseries, initial_leaks = generate_sites(programs[0], in_dir)
        else:
            sites, leak_timeseries, initial_leaks = [], [], []
        if sim_params['preseed_random']:
            seed_timeseries = gen_seed_timeseries(sim_params)
        else:
            seed_timeseries = None

        for j in range(len(programs)):
            if pregen:
                file_loc = gen_dir / "pregen_{}_{}.p".format(i, j)
                if os.path.isfile(file_loc):
                    # If there is a  pregenerated file for the program
                    generated_data = pickle.load(open(file_loc, "rb"))
                    sites = generated_data['sites']
                    leak_timeseries = generated_data['leak_timeseries']
                    initial_leaks = generated_data['initial_leaks']
                    seed_timeseries = generated_data['seed_timeseries']
                else:
                    # Different programs can have different site level parameters ie survey
                    # frequency,so re-evaluate selected sites with new parameters
                    sites = regenerate_sites(programs[j], sites, in_dir)
                    pickle.dump({
                        'sites': sites, 'leak_timeseries': leak_timeseries,
                        'initial_leaks': initial_leaks, 'seed_timeseries': seed_timeseries},
                        open(file_loc, "wb"))
            else:
                sites = []

            opening_message = "Simulating program {} of {} ; simulation {} of {}".format(
                j + 1, len(programs), i + 1, sim_params['n_simulations']
            )
            simulations.append(
                [{'i': i, 'program': deepcopy(programs[j]),
                  'globals':sim_params,
                  'input_directory': in_dir,
                  'output_directory':out_dir,
                  'opening_message': opening_message,
                  'pregenerate_leaks': pregen,
                  'print_from_simulation': sim_params['print_from_simulations'],
                  'sites': sites,
                  'leak_timeseries': leak_timeseries,
                  'initial_leaks': initial_leaks,
                  'seed_timeseries': seed_timeseries,
                  }])
    return simulations
