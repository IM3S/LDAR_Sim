# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        OGI company
# Purpose:     Company managing OGI agents.
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

from OGI_crew import OGI_crew
import numpy as np
import pandas as pd 
from sklearn.cluster import KMeans

class OGI_company:
    def __init__(self, state, parameters, config, timeseries):
        """
        Initialize a company to manage the OGI crews (e.g. a contracting company).

        """
        self.name = 'OGI'
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
        self.timeseries['OGI_prop_sites_avail'] = []
        self.timeseries['OGI_cost'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['OGI_redund_tags'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['OGI_sites_visited'] = np.zeros(self.parameters['timesteps'])
        self.scheduling  = parameters['methods']['OGI']['scheduling']
        

        # Additional variable(s) for each site
        for site in self.state['sites']:
            site.update({'OGI_t_since_last_LDAR': 0})
            site.update({'OGI_surveys_conducted': 0})
            site.update({'attempted_today_OGI?': False})
            site.update({'surveys_done_this_year_OGI': 0})
            site.update({'OGI_missed_leaks': 0})

        # Initialize 2D matrices to store deployment day (DD) counts and MCBs
        self.DD_map = np.zeros(
            (len(self.state['weather'].longitude),
             len(self.state['weather'].latitude)))
        self.MCB_map = np.zeros(
            (len(self.state['weather'].longitude),
             len(self.state['weather'].latitude)))

        # # Initialize the individual OGI crews (the agents)
        # for i in range(config['n_crews']):
        #     self.crews.append(OGI_crew(state, parameters, config,
        #                                timeseries, self.deployment_days, id=i + 1))
        # clustering analysis is applied to assign facilities to each agent, if we have more thane 1 agent 
        if self.parameters['methods']['OGI']['n_crews']>1:
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
            self.crews.append(OGI_crew(state, parameters, config,
                                     timeseries, self.deployment_days, id=i + 1))
        return

    def find_leaks(self):
        """
        The OGI company tells all the crews to get to work.
        """
        if self.scheduling['deployment_times'][0]: 
            required_year = self.scheduling['deployment_times'][1]
            required_month = self.scheduling['deployment_times'][2]
        else:
            required_year = list(range(self.state['t'].start_date.year,self.state['t'].end_date.year+1))
            required_month = list(range(1,13))
        
        if self.state['t'].current_date.month in required_month  and self.state['t'].current_date.year in required_year:

            for i in self.crews:
                i.work_a_day()
    
            # Update method-specific site variables each day
            for site in self.state['sites']:
                site['OGI_t_since_last_LDAR'] += 1
                site['attempted_today_OGI?'] = False
    
            if self.state['t'].current_date.day == 1 and self.state['t'].current_date.month == 1:
                for site in self.state['sites']:
                    site['surveys_done_this_year_OGI'] = 0
    
            # Calculate proportion sites available
            available_sites = 0
            for site in self.state['sites']:
                if self.deployment_days[site['lon_index'],
                                        site['lat_index'],
                                        self.state['t'].current_timestep]:
                    available_sites += 1
            prop_avail = available_sites / len(self.state['sites'])
            self.timeseries['OGI_prop_sites_avail'].append(prop_avail)
        else:
            self.timeseries['OGI_prop_sites_avail'].append(0)

        return

    def site_reports(self):
        """
        Writes site-level deployment days (DDs) and maximum condition blackouts
        (MCBs) for each site.
        """

        for site in self.state['sites']:
            site['OGI_prop_DDs'] = self.DD_map[site['lon_index'], site['lat_index']]
            site['OGI_MCB'] = self.MCB_map[site['lon_index'], site['lat_index']]

        return
