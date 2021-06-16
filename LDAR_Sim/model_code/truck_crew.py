# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        Truck crew
# Purpose:     Initialize each truck crew under truck company
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
from datetime import timedelta
from generic_functions import find_homebase , get_distance, find_homebase_opt
import pandas as pd 

class truck_crew:
    def __init__(self, state, parameters, config, timeseries, deployment_days, id):
        """
        Constructs an individual truck crew based on defined configuration.
        """
        self.state = state
        self.parameters = parameters
        self.config = config
        self.timeseries = timeseries
        self.deployment_days = deployment_days
        self.crewstate = {'id': id}  # Crewstate is unique to this agent
        # self.crewstate['lat'] = 0.0
        # self.crewstate['lon'] = 0.0
        self.worked_today = False
        self.scheduling  = parameters['methods']['truck']['scheduling']
        
        # Read in the homebases as a list of dictionaries 
        homebases = parameters['working_directory'] + self.scheduling['home_bases']
        HB = pd.read_csv(homebases,sep=',')
        self.state['homebases'] = HB
        # get lat & lon of all homebases 
        self.HX = self.state['homebases']['lon']
        self.HY = self.state['homebases']['lat']
        
        # initiate the location of LDAR crew  
        self.state['current_x']= self.scheduling['LDAR_crew_init_location'][0]
        self.state['current_y']= self.scheduling['LDAR_crew_init_location'][1]
    
        return 
    

    def work_a_day(self, candidate_flags):
        """
        Go to work and find the leaks for a given day
        """
        # check deployment years and months 
        # year = self.state['t'].current_date.year
        # month  = self.state['t'].current_date.month
        # if  year in self.deployment_years and month in self.deployment_months:
        self.worked_today = False
        self.candidate_flags = candidate_flags
        work_hours = None
        max_work = self.parameters['methods']['truck']['max_workday']

        if self.parameters['methods']['truck']['consider_daylight']:
            daylight_hours = self.state['daylight'].get_daylight(self.state['t'].current_timestep)
            if daylight_hours <= max_work:
                work_hours = daylight_hours
            elif daylight_hours > max_work:
                work_hours = max_work
        elif not self.parameters['methods']['truck']['consider_daylight']:
            work_hours = max_work

        if work_hours < 24 and work_hours != 0:
            start_hour = (24 - work_hours) / 2
            end_hour = start_hour + work_hours
        else:
            print(
                'Unreasonable number of work hours specified for truck crew ' +
                str(self.crewstate['id']))

        self.state['t'].current_date = self.state['t'].current_date.replace(
            hour=int(start_hour))  # Set start of work day
        
        if self.scheduling['geography']:
            # start day by reading the location of the LDAR team 
            x_LDAR = self.state['current_x']
            y_LDAR = self.state['current_y']
    
            while self.state['t'].current_date.hour < int(end_hour):
                facility_ID, found_site, site, travel_time = self.choose_site(x_LDAR,y_LDAR)
                if not found_site:
                    Home,DIST = find_homebase(x_LDAR,y_LDAR,self.HX,self.HY) 
                    x_LDAR = Home[0]
                    y_LDAR = Home[1]
                    self.state['current_x'] = x_LDAR
                    self.state['current_y'] = y_LDAR
                    break  # Break out  
                
                self.state['t'].current_date += timedelta(minutes= travel_time)
                
                if self.state['t'].current_date.hour > int(end_hour):
                    x_temp = np.float(site['lon'])
                    y_temp = np.float(site['lat'])
                    x_cut = self.state['current_x'] 
                    y_cut = self.state['current_y']
                    Home,DIST = find_homebase_opt(x_temp,y_temp,x_cut,y_cut,self.HX,self.HY)
                    
                    self.state['current_x'] = Home[0]
                    self.state['current_y'] = Home[1]
                    break 
                else:
                    x_LDAR = np.float(site['lon'])
                    y_LDAR = np.float(site['lat'])
                    self.visit_site(facility_ID, site)
                self.worked_today = True
        else:
            # Start day with random "offsite time" required for driving to first site
            self.state['t'].current_date += timedelta(
                minutes=int(
                    self.state['offsite_times']
                    [np.random.randint(0, len(self.state['offsite_times']))]))
    
            while self.state['t'].current_date.hour < int(end_hour):
                facility_ID, found_site, site = self.choose_site(0,0)
                if not found_site:
                    break  # Break out if no site can be found
                self.visit_site(facility_ID, site)
            self.worked_today = True

        
        if self.worked_today:
            self.timeseries['truck_cost'][self.state['t'].current_timestep] += \
                self.parameters['methods']['truck']['cost_per_day']
            self.timeseries['total_daily_cost'][self.state['t'].current_timestep] += \
                self.parameters['methods']['truck']['cost_per_day']

        return

    def choose_site(self,x_LDAR,y_LDAR):
        """
        Choose a site to survey.
        """
        # Sort all sites based on a neglect ranking
        self.state['sites'] = sorted(
            self.state['sites'],
            key=lambda k: k['truck_t_since_last_LDAR'],
            reverse=True)
        
        facility_ID = None  # The facility ID gets assigned if a site is found
        found_site = False  # The found site flag is updated if a site is found
        travel_time = None
        site = None
        Site_T = [] 
        s_list = []
        speed = np.random.choice([70,80,90,100])
        # Then, starting with the most neglected site, check if conditions are suitable for LDAR
        for site in self.state['sites']:
            s_list.append(site)
            x_site = np.float(site['lon'])
            y_site = np.float(site['lat'])
            
            # if the site was assigned to this agent
            if site['label'] + 1 == self.crewstate['id']:
            
                # If the site hasn't been attempted yet today
                if not site['attempted_today_truck?']:
        
                    # If the site is 'unripened' (i.e. hasn't met the minimum interval),
                    # break out - no LDAR today
                    if site['truck_t_since_last_LDAR'] < int(site['truck_min_int']):
                        self.state['t'].current_date = self.state['t'].current_date.replace(hour=23)
                        break
    
                    # Else if site-specific required visits have not been met for the year
                    elif site['surveys_done_this_year_truck'] < int(site['truck_RS']):
    
                        # Check the weather for that site
                        if self.deployment_days[site['lon_index'],
                                                site['lat_index'],
                                                self.state['t'].current_timestep]:
                            
                            if self.scheduling['geography']: 
                                d = get_distance(x_LDAR,y_LDAR,x_site,y_site,"Euclidian")
                                wt = d/speed * 60
                                Site_T.append(wt)
                                
                                if not self.scheduling['route_planning']: 
                                    # The site passes all the tests! Choose it!
                                    travel_time = wt
                                    facility_ID = site['facility_ID']
                                    found_site = True
        
                                    # Update site
                                    site['truck_surveys_conducted'] += 1
                                    site['surveys_done_this_year_truck'] += 1
                                    site['truck_t_since_last_LDAR'] = 0
                                    break
                            else:
                                # The site passes all the tests! Choose it!
                                facility_ID = site['facility_ID']
                                found_site = True
        
                                # Update site
                                site['truck_surveys_conducted'] += 1
                                site['surveys_done_this_year_truck'] += 1
                                site['truck_t_since_last_LDAR'] = 0
                                break
    
                        else:
                            site['attempted_today_truck?'] = True
                        
        
        if self.scheduling['route_planning']:
            if len(Site_T) > 0: 
                j = Site_T.index(min(Site_T))
                site = s_list[j]
                facility_ID = site['facility_ID']
                travel_time = min(Site_T)*60
                found_site = True
                
                # Update site
                site['truck_surveys_conducted'] += 1
                site['surveys_done_this_year_truck'] += 1
                site['truck_t_since_last_LDAR'] = 0
                    
        if self.scheduling['geography'] or self.scheduling['route_planning']:        
            return (facility_ID, found_site, site, travel_time)
        else:
            return (facility_ID, found_site, site)
    
            

    def visit_site(self, facility_ID, site):
        """
        Look for emissions at the chosen site.
        """

        # Sum all the emissions at the site
        leaks_present = []
        site_cum_rate = 0
        for leak in self.state['leaks']:
            if leak['facility_ID'] == facility_ID:
                if leak['status'] == 'active':
                    leaks_present.append(leak)
                    site_cum_rate += leak['rate']

                    # Add vented emissions
        venting = 0
        if self.parameters['consider_venting']:
            venting = self.state['empirical_vents'][
                np.random.randint(0, len(self.state['empirical_vents']))]
            site_cum_rate += venting

        # Simple binary detection module
        detect = False
        if site_cum_rate > (self.config['MDL']):
            detect = True

        if detect:
            # If source is above follow-up threshold, calculate measured rate using
            # quantification error
            quant_error = np.random.normal(0, self.config['QE'])
            measured_rate = None
            if quant_error >= 0:
                measured_rate = site_cum_rate + site_cum_rate*quant_error
            if quant_error < 0:
                denom = abs(quant_error - 1)
                measured_rate = site_cum_rate/denom

            # If source is above follow-up threshold
            if measured_rate > self.config['follow_up_thresh']:
                # Put all necessary information in a dictionary to be assessed at end of day
                site_dict = {
                    'site': site,
                    'leaks_present': leaks_present,
                    'site_cum_rate': site_cum_rate,
                    'measured_rate': measured_rate,
                    'venting': venting
                }

                self.candidate_flags.append(site_dict)

        elif not detect:
            site['truck_missed_leaks'] += len(leaks_present)

        self.state['t'].current_date += timedelta(minutes=int(site['truck_time']))
        self.state['t'].current_date += timedelta(
            minutes=int(
                self.state['offsite_times']
                [np.random.randint(0, len(self.state['offsite_times']))]))
        self.timeseries['truck_sites_visited'][self.state['t'].current_timestep] += 1

        return
