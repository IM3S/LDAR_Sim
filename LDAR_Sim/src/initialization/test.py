from initialization.temp_sites import add_sites_to_programs


def create_sims(sim_params, programs, generator_dir, in_dir, out_dir, input_manager):
    # Store params used to generate the pickle files for change detection
    prog_same_sites, reuse_sites, prog_same_leaks = add_sites_to_programs(
        sim_params, programs, generator_dir, in_dir)
    xxx = 10
