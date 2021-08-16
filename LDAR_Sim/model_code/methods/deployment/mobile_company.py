# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        methods.deployment.mobile_company
# Purpose:     Mobile company specific deployment classes and methods (ie. Scheduling)
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

import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
import math
from methods.deployment._base import SchedCompany as BaseSchedCompany
from methods.crew import BaseCrew


def make_crews(crews, config, state, parameters, timeseries, deployment_days):
    """ Generate crews using BaseCrew class.

    Args:
        crews (list): List of crews
        config (dict): Method parameters
        state (dict): Current state of LDAR-Sim
        parameters (dict): Program parameters
        timeseries (dict): Timeseries
        deployment_days (list): days method can be deployed based on weather

    --- Required in module.company.BaseCompany ---
    """
    for i in range(config['n_crews']):
        crews.append(BaseCrew(state, parameters, config,
                              timeseries, deployment_days, id=i + 1))


class Schedule(BaseSchedCompany):
    def __init__(self, config, parameters, state):
        self.parameters = parameters
        self.config = config
        self.state = state

    # --- inherited methods ---
    # base.company ->  get_deployment_dates()
    # base.company ->  can_deploy_today()

    def assign_agents(self):
        """ If route planning is enabled, use k-means clustering to split site into N clusters
            N equals to the number of crews.

            The goal is to improve the coordiation of LDAR crews when there are
            more than one crew. The crews will only visit the site corresponding to their IDs.
            e.g., crew_ID 0 will only visit site in cluter 0

            This functionality is only used when geography and route_planning are both enabled.

            Returns:
                create a crew_ID related label for each site
        """
        if self.config['scheduling']['route_planning']:
            # Use clustering analysis to assign facilities to each agent,
            # if 2+ agents are available
            if self.config['n_crews'] > 1:
                lats = []
                lons = []
                ID = []
                for site in self.state['sites']:
                    ID.append(site['facility_ID'])
                    lats.append(site['lat'])
                    lons.append(site['lon'])
                # a temporary dataframe creafed for storing ID, coordiates of sites
                sdf = pd.DataFrame({"ID": ID, 'lon': lons, 'lat': lats})
                locs = sdf[['lat', 'lon']].values
                num = self.config['n_crews']
                #  run K-means clustering by using dataframe
                kmeans = KMeans(n_clusters=num, random_state=0).fit(locs)
                label = kmeans.labels_
            else:
                label = np.zeros(len(self.state['sites']))

            for i in range(len(self.state['sites'])):
                self.state['sites'][i]['crew_ID'] = label[i]

    def get_due_sites(self, site_pool):
        """ Retrieve a site list of sites due for screen / survey

            If the method is a followup, return sites that have passed
            that have passed the reporting delay window.

            If the method is not followup return sites that have passed
            the minimum survey interval, and that still require surveys
            in the current year.

        Args:
            site_pool (dict): List of sites
        Returns:
            site_pool (dict): List of sites ready for survey.
        """
        name = self.config['label']
        days_since_LDAR = '{}_t_since_last_LDAR'.format(name)
        survey_done_this_year = '{}_surveys_done_this_year'.format(name)
        survey_min_interval = '{}_min_int'.format(name)
        survey_frequency = '{}_RS'.format(name)
        meth = self.parameters['methods']

        if self.config['follow_up']['is_follow_up']:
            filt_sites = filter(
                lambda s, : (
                    self.state['t'].current_date - s['date_flagged']).days
                >= meth[s['flagged_by']]['reporting_delay'],
                site_pool)
        else:
            days_since_LDAR = '{}_t_since_last_LDAR'.format(name)
            filt_sites = filter(
                lambda s: s[survey_done_this_year] < int(s[survey_frequency]) and
                s[days_since_LDAR] >= int(s[survey_min_interval]), site_pool)

        sort_sites = sorted(
            list(filt_sites), key=lambda x: x[days_since_LDAR], reverse=True)
        return sort_sites

    def get_working_crews(self, site_pool, n_crews, sites_per_crew=3):
        """ Get number of working crews that day. Based on estimate
            that a crew can do 3 sites per day.
        Args:
            site_pool (dict): List of sites
            n_crews (int): Number of crews
            sites_per_crew (int, optional): Number of sites a crew can survey in a day.
            Defaults to 3.

        Returns:
            int: Number of crews to deploy that day.
        """
        n_sites = len(site_pool)
        n_crews = math.ceil(n_sites/(n_crews*sites_per_crew))
        # cap working crews at max number of crews
        if n_crews > self.config['n_crews']:
            n_crews = self.config['n_crews']
        return n_crews

    def get_crew_site_list(self, site_pool, crew_ID, n_crews, crews=None):
        """ This function divies the site pool among all crews. Ordering
            of sites is not changed by function.
        Args:
            site_pool (dict): List of sites
            crew_num (int): Integer index of crew
            n_crews (int): Number of crews
            crews (dict): List of crew instances- not used in mobile but
                          required for other methods

        Returns:
            dict: Crew site list (subset of site_pool)
        """
        if self.config['scheduling']['route_planning']:
            # divies the site pool based on clustering analysis
            crew_site_list = [site for site in site_pool if site['crew_ID'] == crew_ID]
        else:
            # This offsets by the crew number and increments by the
            # number of crews, n_crews= 3 ,  site_pool = [site[0], site[3], site[6]...]
            if len(site_pool) > 0:
                crew_site_list = site_pool[crew_ID::n_crews]
        return crew_site_list
