import pandas as pd
import csv
import random
import numpy as np

from utils.distributions import unpackage_dist
from initialization.leaks import (generate_leak_timeseries,
                                  generate_initial_leaks)


def generate_sites(program, wd):
    # Read in the sites as a list of dictionaries
    with open(wd + program['infrastructure_file']) as f:
        sites = [{k: v for k, v in row.items()}
                 for row in csv.DictReader(f, skipinitialspace=True)]
    empirical_counts = np.array(pd.read_csv(
        wd + program['count_file']).iloc[:, 0])
    # Sample sites
    if program['site_samples'][0]:
        sites = random.sample(
            sites,
            program['site_samples'][1])

    if program['subtype_times'][0]:
        subtype_times = pd.read_csv(wd + program['subtype_times'][1])
        cols_to_add = subtype_times.columns[1:].tolist()
        for col in cols_to_add:
            for site in sites:
                site[col] = subtype_times.loc[subtype_times['subtype_code'] ==
                                              int(site['subtype_code']), col].iloc[0]

    unpackage_dist(program, wd=None)

    # Shuffle all the entries to randomize order for identical 't_Since_last_LDAR' values
    random.shuffle(sites)
    leak_timeseries = {}
    initial_leaks = {}
    # Additional variable(s) for each site
    for site in sites:
        # Add a distribution and unit for each leak
        if not program['subtype_distributions'][0]:
            # If subtypes are not used, set subtype code to 0
            site['subtype_code'] = 0
        site['leak_rate_dist'] = program['dists'][int(site['subtype_code'])]['dist']
        site['leak_rate_units'] = program['dists'][int(site['subtype_code'])]['units']

        n_leaks = random.choice(empirical_counts)
        if n_leaks < 0:  # This can happen occasionally during sensitivity analysis
            n_leaks = 0
        site.update({'initial_leaks': n_leaks})
        initial_site_leaks = generate_initial_leaks(program, site)
        site['cum_leaks'] = len(initial_site_leaks)
        initial_leaks.update({site['facility_ID']: initial_site_leaks})
        site_timeseries = generate_leak_timeseries(program, site)
        leak_timeseries.update({site['facility_ID']: site_timeseries})
    return sites, leak_timeseries, initial_leaks
