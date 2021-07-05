# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        distributions
# Purpose:     fit leaks to different distributions
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
import scipy
import json
import pandas as pd
import numpy as np
from utils.unit_converter import gas_convert


def fit_dist(samples=None, dist_type="lognorm", loc=0, shape=None, scale=None):
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
    dist = getattr(scipy.stats, dist_type)
    if samples is not None:
        try:
            param = dist.fit(samples, floc=loc)
        except:  # noqa: E722 - scipy custom error, needs to be imported
            'some distributions cannot take 0 values'
            samples = [s for s in samples if s > 0]
            param = dist.fit(samples, floc=loc)
        loc = param[-2],
        scale = param[-1]
        shape = param[:-2]
    if isinstance(shape, str):
        # IF shapes a string ie'[2,23.4]', then convert to pyobject (int or list)
        shape = json.loads(shape)
    if not isinstance(shape, list):
        # If the shape is not a list, convert to a list
        shape = [shape]
    return dist(*shape, loc=loc, scale=scale)


def leak_rvs(distribution, max_size=None, gpsec_conversion=None):
    """ Generate A random Leak, convert to g/s then checkit against
        leaks size, run until leak is smaller than max size

    Args:
        distribution (A scipy Distribution): Distribution of leak sizes
        max_size (int, optional): Maximum Leak Size
        gpsec_conversion (array, optional):  Conversion Units [input_metric, input_increment]

    Returns:
        [type]: [description]
    """

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


def unpackage_dist(program, wd=None):
    # --------- Leak distributions -------------
    program['dists'] = {}
    _temp_dists = {}
    # Use subtype_distributions file if true

    if program['use_empirical_rates'] in ['fit', 'sample']:
        program['empirical_leaks'] = np.array(pd.read_csv(
            wd + program['leak_file']).iloc[:, 0])

    if program['use_empirical_rates'] == 'fit':
        program['dists'][0] = {
            'dist': fit_dist(
                samples=program['empirical_leaks'],
                dist_type='lognorm'),
            'units': ['gram', 'second']}

    # If use_empirical_rates is false then use distributions
    elif not program['use_empirical_rates']:
        if program['subtype_distributions'][0]:
            subtype_dists = pd.read_csv(
                program['working_directory'] + program['subtype_distributions'][1])
            col_headers = subtype_dists.columns[1:].tolist()
            for row in subtype_dists.iterrows():
                subtype_dist = {}
                # Generate A temp Distribution dict of dists in file
                for col in col_headers:
                    subtype_dist[col] = row[1][col]
                _temp_dists[row[1][0]] = subtype_dist

        if len(_temp_dists) > 1:  # If there are sub_type dists
            for key, dist in _temp_dists.items():
                if dist['dist_type'] == 'lognorm':
                    scale = np.exp(dist['dist_mu'])
                else:
                    scale = dist['dist_mu']
                program['dists'][key] = {
                    'dist': fit_dist(dist_type=dist['dist_type'],
                                     shape=dist['dist_sigma'],
                                     scale=scale),
                    'units': [dist['dist_metric'], dist['dist_increment']]}
        elif "leak_rate_dist" in program:
            program['dist_type'] = program['leak_rate_dist'][0]
            program['dist_scale'] = program['leak_rate_dist'][1]
            program['dist_shape'] = program['leak_rate_dist'][2:-2]
            program['leak_rate_units'] = program['leak_rate_dist'][-2:]
            # lognorm is a common special case. used often for leaks. Mu is is commonly
            # provided to discribe leak which is ln(dist_scale). For this type the model
            # accepts mu in place of scale.
            if program['dist_type'] == 'lognorm':
                program['dist_scale'] = np.exp(program['dist_scale'])
            # Use a subtype distribution code of zero if not using subtype distributions.
            program['dists'][0] = {
                'dist': fit_dist(dist_type=program['dist_type'],
                                 shape=program['dist_shape'],
                                 scale=program['dist_scale']),
                'units': program['leak_rate_units']}
            #  Empirical Leaks can be fit with the following
