# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        Truck company
# Purpose:     Company managing truck agents
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

from truck_crew import truck_crew
import math
import numpy as np
from generic_functions import get_prop_rate
import pandas as pd 
from sklearn.cluster import KMeans

class truck_company:
    def __init__(self, state, parameters, config, timeseries):
        """
        Initialize a company to manage the truck crews (e.g. a contracting company).

        """
        self.name = 'truck'
        self.state = state
        self.parameters = parameters
        self.config = config
        self.timeseries = timeseries
        self.crews = []
        self.deployment_days = self.state['weather'].deployment_days(   
            method_name=self.name,
            start_date=self.state['t'].start_date,
            start_work_hour=8,  # Start hour in day
            consider_weather=parameters['consider_weather'])
        self.timeseries['truck_prop_sites_avail'] = []
        self.timeseries['truck_cost'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['truck_eff_flags'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['truck_flags_redund1'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['truck_flags_redund2'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['truck_flags_redund3'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['truck_sites_visited'] = np.zeros(self.parameters['timesteps'])
        self.scheduling  = parameters['methods']['truck']['scheduling']
        
        

        # Assign the correct follow-up threshold
        if self.config['follow_up_thresh'][1] == "absolute":
            self.config['follow_up_thresh'] = self.config['follow_up_thresh'][0]
        elif self.config['follow_up_thresh'][1] == "proportion":
            self.config['follow_up_thresh'] = get_prop_rate(
                self.config['follow_up_thresh'][0],
                self.state['empirical_leaks'])
        else:
            print('Follow-up threshold type not recognized. Must be "absolute" or "proportion".')

        # Additional variable(s) for each site
        for site in self.state['sites']:
            site.update({'truck_t_since_last_LDAR': 0})
            site.update({'truck_surveys_conducted': 0})
            site.update({'attempted_today_truck?': False})
            site.update({'surveys_done_this_year_truck': 0})
            site.update({'truck_missed_leaks': 0})

        # Initialize 2D matrices to store deployment day (DD) counts and MCBs
        self.DD_map = np.zeros(
            (len(self.state['weather'].longitude),
             len(self.state['weather'].latitude)))
        self.MCB_map = np.zeros(
            (len(self.state['weather'].longitude),
             len(self.state['weather'].latitude)))
        
            
        #clustering analysis is applied to assign facilities to each agent, if we have more thane 1 agent 
        if self.parameters['methods']['truck']['n_crews']>1:
            Lats = [] 
            Lons = [] 
            ID = [] 
            for site in self.state['sites']:
                ID.append(site['facility_ID'])
                Lats.append(site['lat'])
                Lons.append(site['lon'])
            sdf = pd.DataFrame({"ID":ID,
                        'lon':Lons,
                        'lat':Lats}) 
            X = sdf[['lat', 'lon']].values
            num = config['n_crews']
            kmeans = KMeans(n_clusters=num, random_state=0).fit(X)
            l = kmeans.labels_
        else: 
            l = np.zeros(len(self.state['sites']))
        
        for i in range(len(self.state['sites'])): 
            self.state['sites'][i]['label'] = l[i]
        
        for i in range(config['n_crews']):
            self.crews.append(truck_crew(state, parameters, config,
                                     timeseries, self.deployment_days, id=i + 1))

        return

    def find_leaks(self):
        """
        The truck company tells all the crews to get to work.
        """
        if self.scheduling['deployment_times'][0]: 
            required_year = self.scheduling['deployment_times'][1]
            required_month = self.scheduling['deployment_times'][2]
        else:
            required_year = list(range(self.state['t'].start_date.year,self.state['t'].end_date.year+1))
            required_month = list(range(1,13))
        
        if self.state['t'].current_date.month in required_month  and self.state['t'].current_date.year in required_year:
            self.candidate_flags = []
            for i in self.crews:
                i.work_a_day(self.candidate_flags)
    
            # Flag sites according to the flag ratio
            if len(self.candidate_flags) > 0:
                self.flag_sites()
    
            # Update method-specific site variables each day
            for site in self.state['sites']:
                site['truck_t_since_last_LDAR'] += 1
                site['attempted_today_truck?'] = False
    
            if self.state['t'].current_date.day == 1 and self.state['t'].current_date.month == 1:
                for site in self.state['sites']:
                    site['surveys_done_this_year_truck'] = 0
    
            # Calculate proportion sites available
            available_sites = 0
            for site in self.state['sites']:
                if self.deployment_days[site['lon_index'],
                                        site['lat_index'],
                                        self.state['t'].current_timestep]:
                    available_sites += 1
            prop_avail = available_sites / len(self.state['sites'])
            self.timeseries['truck_prop_sites_avail'].append(prop_avail)
        else: 
            self.timeseries['truck_prop_sites_avail'].append(0)

        return

    def flag_sites(self):
        """
        Flag the most important sites for follow-up.

        """
        # First, figure out how many sites you're going to choose
        n_sites_to_flag = len(self.candidate_flags) * self.config['follow_up_prop']
        n_sites_to_flag = int(math.ceil(n_sites_to_flag))

        sites_to_flag = []
        measured_rates = []

        for i in self.candidate_flags:
            measured_rates.append(i['measured_rate'])
        measured_rates.sort(reverse=True)
        target_rates = measured_rates[:n_sites_to_flag]

        for i in self.candidate_flags:
            if i['measured_rate'] in target_rates:
                sites_to_flag.append(i)

        for i in sites_to_flag:
            site = i['site']
            leaks_present = i['leaks_present']
            site_cum_rate = i['site_cum_rate']
            venting = i['venting']

            # If the site is already flagged, your flag is redundant
            if site['currently_flagged']:
                self.timeseries['truck_flags_redund1'][self.state['t'].current_timestep] += 1

            elif not site['currently_flagged']:
                # Flag the site for follow up
                site['currently_flagged'] = True
                site['date_flagged'] = self.state['t'].current_date
                site['flagged_by'] = self.config['name']
                self.timeseries['truck_eff_flags'][self.state['t'].current_timestep] += 1

                # Does the chosen site already have tagged leaks?
                redund2 = False
                for leak in leaks_present:
                    if leak['date_tagged'] is not None:
                        redund2 = True

                if redund2:
                    self.timeseries['truck_flags_redund2'][self.state['t'].current_timestep] += 1

                # Would the site have been chosen without venting?
                if self.parameters['consider_venting']:
                    if (site_cum_rate - venting) < self.config['follow_up_thresh']:
                        self.timeseries['truck_flags_redund3'][
                            self.state['t'].current_timestep] += 1

    def site_reports(self):
        """
        Writes site-level deployment days (DDs) and maximum condition blackouts (MCBs)
        for each site.
        """

        for site in self.state['sites']:
            site['truck_prop_DDs'] = self.DD_map[site['lon_index'], site['lat_index']]
            site['truck_MCB'] = self.MCB_map[site['lon_index'], site['lat_index']]

        return
