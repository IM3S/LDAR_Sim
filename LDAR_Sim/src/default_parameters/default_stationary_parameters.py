# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        default_continuous_parameters
# Purpose:     Default continuous parameters
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

default_stationary_parameters = {
    'version': '2.0',
    'parameter_level': 'method',
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
    'cost': {
        'upfront': 500,
        'per_day': 1,
        'per_hour': 0,
        'per_site': 0,

    },
    'follow_up': {
        'threshold': 0,
        'threshold_type': 'absolute',   	# 'absolute' or 'relative'
        'proportion': 1,
        'interaction_priority': 'threshold',  # 'threshold' or 'proportion'
        'redundancy_filter': 'recent',			# 'recent' or 'average' or 'max'
        'delay': 0,  # min. age of oldest candidate flag before flagging
        'instant_threshold': None,
        'instant_threshold_type': 'absolute', 	# 'absolute' or 'relative'
    },
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