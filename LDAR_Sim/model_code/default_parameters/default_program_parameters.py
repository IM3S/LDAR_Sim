# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        default_program_parameters
# Purpose:     Default program parameters
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

default_program_parameters = {
    'version': '2.0',
    'parameter_level': 'program',
    'methods': {},
    'method_labels': [],
    'program_name': 'default',
    'UTC_offset': -6,
    'weather_file': "ERA5_AB_1x1_hourly_2015_2019.nc",
    'weather_is_hourly': False,
    'infrastructure_file': 'facility_list_template.csv',
    'site_samples': [True, 500],
    'subtype_times': [False, 'subtype_times.csv'],
    'consider_weather': True,
    'repair_delay': 14,
    'repair_cost': 200,
    'leaks': {
        'LPR': 0.0065,
        'empirical_leak_rates': True,
        'fit_empirical_to_dist': False,
        'leak_file': 'leak_rates.csv',
        'count_file': 'leak_counts.csv',
        'use_subtype_distributions': False,
        'subtype_distribution_file': 'subtype_distributions.csv',
        'distribution_type': 'lognorm',
        'distribution_params': [-2.776, 1.462],
        'units': ["kilogram", "hour"],
        'max_rate': 100},
    'vents': {
        'consider_venting': False,
        'empirical_vent_rates': True,
        'fit_empirical_to_dist': False,
        'vent_file': 'site_rates.csv',
        'use_subtype_distributions': False,
        'subtype_distribution_file': 'subtype_distributions.csv',
        'distribution_type': 'lognorm',
        'distribution_params': [-2.776, 1.462],
        'units': ["kilogram", "hour"],
        'max_rate': 100,
    },
    'operator': {
        'consider_operator': False,
        'NRd': 150,
        'max_det_op': 0.00,
        'operator_strength': 0,
    },
    'verification_cost': 25,
    'sensitivity': {'perform': False,
                    'program': 'OGI',
                    'batch': [True, 2],
                    }
}
