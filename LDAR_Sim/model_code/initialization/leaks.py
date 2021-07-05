from numpy import random
from utils.distributions import leak_rvs
from datetime import datetime, timedelta


def generate_leak(program, leak_dist=None, leak_dist_units=None):
    leaksize = None
    if program['use_empirical_rates'] == 'sample':
        leaksize = random.choice(program['empirical_leaks'])
    else:
        leaksize = leak_rvs(
            leak_dist,
            program['max_leak_rate'],
            leak_dist_units)
    return leaksize


def generate_leak_timeseries(program, site, leak_count=0):
    # Get distribit
    n_timesteps = program['timesteps']
    site_timeseries = []
    for t in range(n_timesteps):
        leak_rate = None
        if random.binomial(1, program['LPR']):
            leak_rate = generate_leak(
                program, site['leak_rate_dist'],
                site['leak_rate_units'])
            site['cum_leaks'] += 1
            cur_dt = datetime(program['start_year'], 1, 1) + timedelta(days=t)
            site_timeseries.append({
                'leak_ID': site['facility_ID'] + '_' + str(site['cum_leaks'])
                .zfill(10),
                'facility_ID': site['facility_ID'],
                'equipment_group': random.randint(1, int(site['equipment_groups'])+1),
                'rate': leak_rate,
                'lat': float(site['lat']),
                'lon': float(site['lon']),
                'status': 'active',
                'days_active': 0,
                'tagged': False,
                'component': 'unknown',
                'date_began': cur_dt,
                'date_tagged': None,
                'tagged_by_company': None,
                'tagged_by_crew': None,
                'requires_shutdown': False,
                'date_repaired': None,
                'repair_delay': None,
            })
        else:
            site_timeseries.append(None)
    return site_timeseries


def generate_initial_leaks(program, site,  wd=None):
    # Get distribit
    leak_count = 0
    initial_site_leaks = []
    for leak in range(site['initial_leaks']):
        leak_count += 1
        leak_rate = generate_leak(program, site['leak_rate_dist'], site['leak_rate_units'])
        initial_site_leaks.append({
            'leak_ID': site['facility_ID'] + '_' + str(leak_count)
            .zfill(10),
            'facility_ID': site['facility_ID'],
            'equipment_group': random.randint(1, int(site['equipment_groups'])+1),
            'rate': leak_rate,
            'lat': float(site['lat']),
            'lon': float(site['lon']),
            'status': 'active',
            'tagged': False,
            'days_active': 0,
            'component': 'unknown',
            'date_began': datetime(program['start_year'], 1, 1),
            'date_tagged': None,
            'tagged_by_company': None,
            'tagged_by_crew': None,
            'requires_shutdown': False,
            'date_repaired': None,
            'repair_delay': None,
        })
    return initial_site_leaks
