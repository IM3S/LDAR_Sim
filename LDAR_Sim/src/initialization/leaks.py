# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        LDAR-Sim initialization.leaks
# Purpose:     Generate Leaks, Generate initial leaks and leak timeseries
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

from datetime import timedelta
from numpy import random
from utils.distributions import leak_rvs


def generate_leak(facility, start_date, leak_count, days_active=0):
    """ Generate a single leak at a site

    Args:
        program (dict): Program parameter dictionary
        site (dict): Site parameter and variable dictionary
        start_date (datetime): Leak start date
        leak_count (integer): Number of leaks at site, used for creating id
        days_active (int, optional): Days the leak has been active. Defaults to 0.

    Returns:
        dict: Leak object
    """
    if facility['empirical_leaks'] and facility['leak_file_use'] == 'sample':
        leak_rate = random.choice(facility['empirical_leaks'])
    else:
        leak_rate = leak_rvs(
            facility['leak_dist'],
            facility['max_leak_rate'],
            facility['units'])
    return {
        'leak_ID': '{}_{}'.format(facility['facility_ID'], str(leak_count).zfill(5)),
        'facility_ID': str(facility['facility_ID']),
        'equipment_group': random.randint(1, int(facility['equipment_groups'])+1),
        'rate': leak_rate,
        'lat': float(facility['lat']),
        'lon': float(facility['lon']),
        'status': 'active',
        'days_active': days_active,
        'days_active_prog_start': days_active,
        'tagged': False,
        'component': 'unknown',
        'date_began': start_date,
        'date_tagged': None,
        'tagged_by_company': None,
        'tagged_by_crew': None,
        'init_detect_by': None,
        'init_detect_date': None,
        'requires_shutdown': False,
        'date_repaired': None,
        'repair_delay': None,
    }


def gen_initial_leaks(facility, start_date, n_leaks=None):
    """ Generate initial leaks at a site

    Args:
        facility (dict): Site parameter and variable dictionary
        n_days (integer): Number of days in timeseries
        n_leaks (integer): Number of leaks to include on first day at site
    Returns:
        list: List of leaks at a site
    """
    if n_leaks is None:
        n_leaks = random.binomial(facility['NRd'], facility['LPR'])
    # Could add logic allowing users to set the number of initial leaks
    initial_leaks = []
    leak_count = 0
    for _ in range(n_leaks):
        leak_count += 1
        days_active = random.randint(0, high=facility['NRd'])
        leak_start_date = start_date - timedelta(days=days_active)
        initial_leaks.append(generate_leak(facility, leak_start_date, leak_count, days_active))
    return initial_leaks


def gen_leak_timeseries(facility, start_date, n_days, initial_leaks=None):
    """ Generate a time series of leaks for a single site

    Args:
        facility (dict): Site parameter and variable dictionary
        start_date(datetime): Start of timeseries
        n_days (integer): Number of days in timeseries
        n_initial_leaks (integer): Number of leaks at site, used for creating id

    Returns:
        list: Timeseries of leaks at a site
    """
    leak_timeseries = initial_leaks
    leak_count = len(initial_leaks)
    for t in range(n_days):
        if random.binomial(1, facility['LPR']):
            # Generate New Leak
            leak_count += 1
            cur_dt = start_date + timedelta(days=t)
            leak_timeseries.append([generate_leak(facility, cur_dt, leak_count)])
    return leak_timeseries
