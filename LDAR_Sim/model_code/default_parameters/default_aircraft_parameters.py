# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        default_aircraft_parameters
# Purpose:     Default aircraft parameters
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

default_aircraft_parameters = {
    'version': '2.0',
    'parameter_level': 'method',
    'label': 'aircraft',
    'module': 'dummy',  # TEMPORARY for backwards compatibility
    'deployment_type': 'mobile',
    'measurement_scale': "equipment",
    'sensor': {
        'type': 'default',
        'MDL': 0.01,
        'QE': 0,
    },
    'weather_limits': {
        'temp': [-30.0, 40.0],
        'wind': [0.0, 10.0],
        'precip': [0.0, 1.0],
    },
    'follow_up': {
        'is_follow_up': False,
        'threshold_type': "absolute",
        'threshold': 0.0,
        'ratio': 1.0,
    },
    't_bw_sites': 10,
    'n_crews': 1,
    'max_workday': 8,
    'cost_per_day': 10000,
    'reporting_delay': 2,
    'consider_daylight': False,
    'scheduling': {
        'route_planning': False,
        'home_bases_files': 'Airport_AB_Coordinates.csv',
        'speed_list': [],
        'LDAR_crew_init_location': [-114.062019, 51.044270],
        'deployment_years': [],
        'deployment_months': [],
    }
}
