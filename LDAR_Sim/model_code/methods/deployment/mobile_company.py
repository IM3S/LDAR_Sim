import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
import math
from methods.deployment.base import sched_company as base_sched_company


class Schedule(base_sched_company):
    def __init__(self, config, parameters, state):
        self.parameters = parameters
        self.config = config
        self.state = state

    # --- inherited ---
    # base.company ->  get_deployment_dates()
    # base.company ->  can_deploy_today()

    def assign_agents(self):
        """[summary]
                ---HBD MO!!!  Describe what happens hear ---
        """
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
            # HBD - What is sdf?
            sdf = pd.DataFrame({"ID": ID,
                                'lon': lons,
                                'lat': lats})
            locs = sdf[['lat', 'lon']].values
            num = self.config['n_crews']
            kmeans = KMeans(n_clusters=num, random_state=0).fit(locs)
            label = kmeans.labels_
        else:
            label = np.zeros(len(self.state['sites']))

        for i in range(len(self.state['sites'])):
            self.state['sites'][i]['crew_id'] = label[i]

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

        if self.config['is_follow_up']:
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
        # cap workuing crews at max number of crews
        if n_crews > self.config['n_crews']:
            n_crews = self.config['n_crews']
        return n_crews

    def get_crew_site_list(self, site_pool, crew_id, n_crews):
        """ This function divies the site pool among all crews. Ordering
            of sites is not changed by function.
        Args:
            site_pool (dict): List of sites
            crew_num (int): Integer index of crew
            n_crews (int): Number of crews

        Returns:
            dict: Crew site list (subset of site_pool)
        """
        if self.config['scheduling']['geography']:
            # divies the site pool based on clustering analysis
            crew_site_list = [site for site in site_pool if site['crew_id'] == crew_id]
        else:
            # This offsets by the crew number and increments by the
            # number of crews, n_crews= 3 ,  site_pool = [site[0], site[3], site[6]...]
            if len(site_pool) > 0:
                crew_site_list = site_pool[crew_id::n_crews]
        return crew_site_list
