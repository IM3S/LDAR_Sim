# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        site_utilities
# Purpose:     Generic helper functions to rank and slice sites
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

import numpy as np

def haversine_distance (lat1, lon1, lat2, lon2):
    '''
    haversine difference between two lat - long coordinates. This is a simple method to perform this calculation (there
    are more complicated ways if you want to get into it).

    lat1 = latitude 1
    lon1 = longitude 1
    lat2 = latitude 2
    lon2 = longitude 2

    returns distance in kms
    '''
    radius = 6371.0        # km

    dlat = np.radians (lat2 - lat1)
    dlon = np.radians (lon2 - lon1)
    a = (np.sin (dlat / 2.0) * np.sin (dlat / 2.0) +
         np.cos (np.radians (lat1)) * np.cos (np.radians (lat2)) *
         np.sin (dlon / 2.0) * np.sin (dlon / 2.0))
    c = 2.0 * np.arctan2 (np.sqrt (a), np.sqrt (1.0 - a))
    d = radius * c
    return (d)


