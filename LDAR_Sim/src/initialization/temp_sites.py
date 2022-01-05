from copy import deepcopy
from datetime import datetime
import os
import pickle
import pandas as pd
from numpy.random import binomial
import random


def load_subtypes(program, loc):


def check_previous_subtypes():


def check_previous_sites(sites, program, prev_program, start_date, end_date, generator_dir):
    cp_prog = deepcopy(program)
    cp_prog = deepcopy(program)


def load_previous_sites(sites, programs, prev_programs, start_date, end_date, generator_dir):
    cp_progs = deepcopy(programs)
    cp_prev_progs = deepcopy(prev_programs)
    prog_tracker = {}
    for pidx in cp_progs:
        same_NRd = False
        same_LPR = False
        same_emis = False
        has_prog = False
        if pidx in cp_prev_progs:
            LPR = cp_progs[pidx]['emissions'].pop('LPR')
            prev_LPR = cp_prev_progs[pidx]['emissions'].pop('LPR')
            NRd = cp_progs[pidx]['emissions'].pop('NRd')
            prev_NRd = cp_prev_progs[pidx]['emissions'].pop('NRd')
            emis = cp_progs[pidx]['emissions']
            prev_emis = cp_prev_progs[pidx]['emissions']
            has_prog = True
            same_LPR = LPR == prev_LPR
            same_NRd = NRd == prev_NRd
            same_emis = emis == prev_emis
        prog_tracker.update({
            'has_prog': has_prog,
            'same_LPR': same_LPR,
            'same_NRd': same_NRd,
            'same_emis': same_emis
        })

    prev_sites = prev_programs['sites']
    prev_LPR = prev_programs['LPR']
    prev_NRd = prev_site_params['NRd']
    prev_start_date = prev_site_params['start_date']
    prev_end_date = prev_site_params['end_date']
    prev_site_IDs = [s['facility_ID'] for s in prev_sites]
    site_IDs = [s['facility_ID'] for s in sites]

    if ((site_samples is not None and len(prev_sites) == site_samples)
            or (site_samples is None and len(prev_sites) == len(sites))) \
            and set(site_IDs).intersection(set(prev_site_IDs)) \
            and (prev_LPR == LPR and prev_NRd == NRd) \
            and (prev_start_date == start_date and prev_end_date == end_date):
        print("    Previous parameters match parameters, applying to simulations")
        gen_sites = deepcopy(prev_sites)
        reuse_sites = True
    else:
        gen_sites = None
        reuse_sites = False
    return gen_sites, reuse_sites


def add_sites_to_programs(sim_params, programs, generator_dir, in_dir):
    def _sample_sites(n_samples, sites):
        if n_samples is None:
            n_samples = len(sites)
        return random.sample(sites, n_samples)  # Sample or shuffle

    def _gen_leak_cnt_ts(start_date, end_date, LPR, NRd):
        n_timesteps = (end_date-start_date).days
        return binomial(1, LPR, size=n_timesteps), binomial(1, LPR, size=NRd)

    print("--- Initializing Sites ---")
    reuse_sites = False
    baseline_prog = deepcopy(programs[sim_params['baseline_program']])
    site_samples = baseline_prog['site_samples']
    infrastructure_file = baseline_prog['infrastructure_file']
    sites = pd.read_csv(in_dir / infrastructure_file).to_dict('records')

    emis = baseline_prog['emissions']
    NRd = emis['NRd']
    LPR = emis['LPR']
    multi_LPR = len([p for _, p in programs.items() if p['emissions']['LPR'] != LPR]) > 0
    multi_NRd = len([p for _, p in programs.items() if p['emissions']['NRd'] != NRd]) > 0
    multi_emis = len([p for _, p in programs.items() if p['emissions'] != emis]) > 0

    start_date = datetime(*sim_params['start_date'])
    end_date = datetime(*sim_params['end_date'])

    for pidx in programs:
        prog = programs[pidx]
        if prog['facility_subtypes'] is not None:
            facility_subtypes = pd.read_csv(
                in_dir / prog['facility_subtypes'],
                index_col='subtype_code').to_dict('index')
        else:
            facility_subtypes = {
                0: {
                    'subtype_code': 0,
                    'leak_dist_type': prog['emissions']['leak_dist_type'],
                    'leak_dist_params': prog['emissions']['leak_dist_params'],
                    'LPR': prog['emissions']['LPR'],
                    'NRd': prog['emissions']['NRd'],
                    'emissions_units': prog['emissions']['units']}}

        for site in sites:
            subtype_time = subtypes_times[site['subtype_code']]
            site.update(subtype_time)
        if sim_params['pregenerate_leaks'] and os.path.isfile(generator_dir / "programs.p"):
            print("    Previous sim parameters found in {}".format(generator_dir))
            prev = load_previous_subtypes(programs[prog], generator_dir)

    if sim_params['pregenerate_leaks']:
        prog_same_sites = True
        if not os.path.isfile(generator_dir / "programs.p"):
            print("    No previous sim parameters were found in {}".format(generator_dir))
        else:

            prev_progs = pickle.load(open(generator_dir / "programs.p", "rb"))
            gen_sites, reuse_sites = load_previous_sites(programs, prev_progs, start_date,
                                                         end_date, generator_dir)
            if not reuse_sites:
                print("    Previous parameters do not match parameters, reinitializing sites")

    if sim_params['pregenerate_leaks']:
        prog_same_sites = True
        if not os.path.isfile(generator_dir / "site_params.p"):
            print("    No previous sim parameters were found in {}".format(generator_dir))
        else:
            gen_sites, reuse_sites = load_previous_sites(sites, NRd, LPR, start_date,
                                                         end_date, site_samples, generator_dir)
            if not reuse_sites:
                print("    Previous parameters do not match parameters, reinitializing sites")

    # If pregenerated leaks are not used check to see if single leak dist is used
    elif len(set([p['site_samples'] for _, p in programs.items()])) == 1 \
            and len(set([p['infrastructure_file'] for _, p in programs.items()])) == 1:
        prog_same_sites = True
        print("    Generating single set of sites for all programs")
    else:
        print("    Generating sets of sites for each program")
        prog_same_sites = False

    # If sites are not reused but have the same sites for each program
    if not reuse_sites and prog_same_sites:
        gen_sites = _sample_sites(site_samples, sites)
        if not multi_LPR and not multi_NRd:
            print("    Same LPR and NRD, generating single leak time series")
            for site in gen_sites:
                leak_cnt_ts, init_leak_cnt_ts = _gen_leak_cnt_ts(start_date, end_date, LPR, NRd)
                site.update({'leak_cnt_ts': leak_cnt_ts, 'init_leak_cnt_ts': init_leak_cnt_ts})
                if not multi_emis:
                    site.update({
                        'leak_ts': leak_cnt_ts,
                        'init_leak_ts': init_leak_cnt_ts})

    # Go through each program and populate sites
    for p in programs:
        pNRd, pLPR = p['emissions']['NRd'], p['emissions']['LPR']
        if not prog_same_sites:
            gen_sites = _sample_sites(site_samples, sites)
        for site in gen_sites:
            if multi_LPR and multi_NRd:
                leak_cnt_ts, init_leak_cnt_ts = _gen_leak_cnt_ts(start_date, end_date, pLPR, pNRd)
                site.update({'leak_cnt_ts': leak_cnt_ts, 'init_leak_cnt_ts': init_leak_cnt_ts})

        programs[p].update({'sites': gen_sites})

    if not multi_LPR and not multi_NRd and prog_same_sites:
        site_params = {'sites': gen_sites, 'NRd': NRd, 'LPR': LPR, 'emis': emis,
                       'start_date': start_date, 'end_date': end_date}
        pickle.dump(site_params, open(generator_dir / 'site_params.p', "wb"))

        pickle.dump(programs, open(generator_dir / 'programs.p', "wb"))
    return prog_same_sites, reuse_sites, not multi_LPR and not multi_NRd
    # Sample sites If sites are not reused from a previous program set
