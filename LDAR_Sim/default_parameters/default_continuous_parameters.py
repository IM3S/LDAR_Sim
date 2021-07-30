# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        default_continuous_parameters
# Purpose:     Default continuous parameters
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

continuous_parameters = {
    'label': 'Cont',
    'module': 'dummy',
    'deployment_type': 'stationary',
    'measurement_scale': "equipment",
    'sensor': 'default',
    'is_follow_up': False,
    'n_crews': 1,
    'min_temp': -30,
    'max_wind': 10,
    'max_precip': 1,
    'up_front_cost': 500,
    'cost_per_day': 1,
    'follow_up_thresh': [0, "absolute"],
    'follow_up_ratio': 1,
    'time_to_detection': 7,
    'reporting_delay': 2,
    'MDL': 0.01,
    'QE': 0,
    'consider_daylight': False,
    'scheduling': {
        'route_planning': False,
        'home_bases_files': '',
        'speed_list': [],
        'LDAR_crew_init_location': [],
        'deployment_years': [],
        'deployment_months': [],
    }
}