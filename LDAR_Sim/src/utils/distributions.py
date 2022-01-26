# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        utils.distributions
# Purpose:     fit leaks to different distributions
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

import json

import numpy as np
# You should have received a copy of the MIT License
# along with this program.  If not, see <https://opensource.org/licenses/MIT>.
#
# ------------------------------------------------------------------------------
from scipy import stats
from copy import deepcopy
from utils.unit_converter import gas_convert


def fit_dist(samples=None, dist_params=None, dist_type="lognorm", loc=0, shape=None, scale=None):
    """Fit a distribution (leak rates) by a distribution type.
    Args:
        samples (list, optional): List of samples (leak rates in g/s)
        dist_type (str, optional): scipy distribution type. Defaults to "lognorm".
        loc (int, optional): scipy loc field - linear shift to dist. Defaults to 0.
        shape (list, float, or string): scipy shape parameters
        scale/mu (float): scipy scale parameters* Except for lognorm. This willbe a mu value,
         scale = exp(mu).
    see distributions in https://docs.scipy.org/doc/scipy/reference/stats.html forname, method,
    and shape /scale purpose.
    Returns:
        Scipy distribution Object: Distribution object, can be called with rvs, pdf,cdf exc.
    """
    params = deepcopy(dist_params)
    if isinstance(params, str):
        # IF shapes a string ie'[2,23.4]', then convert to pyobject (int or list)
        params = json.loads(params)
    dist = getattr(stats, dist_type)
    if samples is not None:
        try:
            param = dist.fit(samples, floc=loc)
        except:  # noqa: E722 - scipy custom error, needs to be imported
            'some distributions cannot take 0 values'
            samples = [s for s in samples if s > 0]
            param = list(dist.fit(samples, floc=loc))
        params = [param[-1]] + param[:-2]
    else:
        if dist_type == 'lognorm':
            params[0] = np.exp(params[0])

    return dist(params[1:], loc=loc, scale=params[0])


def leak_rvs(distribution, max_size=None, gpsec_conversion=None):
    """ Generate A random Leak, convert to g/s then checkit against
        leaks size, run until leak is smaller than max size
    Args:
        distribution (A scipy Distribution): Distribution of leak sizes
        max_size (int, optional): Maximum Leak Size
        gpsec_conversion (array, optional):  Conversion Units [input_metric, input_increment]
    Returns:
        float: leak size in units provided
    """
    if isinstance(gpsec_conversion, str):
        # IF shapes a string ie'[2,23.4]', then convert to pyobject (int or list)
        gpsec_conversion = json.loads(gpsec_conversion.replace("'", '"'))
    while True:
        leaksize = distribution.rvs()  # Get Random Value from Distribution
        if gpsec_conversion and  \
                gpsec_conversion[0].lower() != 'gram' and \
                gpsec_conversion[1].lower() != "second":
            leaksize = gas_convert(leaksize, input_metric=gpsec_conversion[0],
                                   input_increment=gpsec_conversion[1])
        if not max_size or leaksize < max_size:
            break  # Rerun if value is larger than maximum
    return leaksize


def unpackage_dist(program):
    """ Create scipy like leak distributions based on input dists or leak files

    Args:
        program (dict): Program parameter dictionary
        in_dir (pathlib type): input directory of file. Defaults to None.
    """
    # --------- Leak distributions -------------
    for st_idx, subtype in program['subtypes'].items():
        subtype['leak_rate_dist'] = fit_dist(
            dist_type=subtype['dist_type'],
            shape=subtype['dist_shape'],
            scale=subtype['dist_scale'])
