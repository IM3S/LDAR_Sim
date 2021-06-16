# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        OGI crew
# Purpose:     Initialize each OGI crew under OGI company
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
import math
import pandas as pd 
from generic_functions import find_homebase , get_distance, find_homebase_opt

class OGI_crew:
    def __init__(self, state, parameters, config, timeseries, deployment_days, id):
        """
        Constructs an individual OGI crew based on defined configuration.
        """
        self.state = state
        self.parameters = parameters
        self.config = config
        self.timeseries = timeseries
        self.deployment_days = deployment_days
        self.crewstate = {'id': id}
        # self.crewstate['lat'] = 0.0
        # self.crewstate['lon'] = 0.0
        self.worked_today = False
        self.rollover = []
        self.worked_today = False
        self.scheduling  = parameters['methods']['OGI']['scheduling']
        
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

    def work_a_day(self):
        """
        Go to work and find the leaks for a given day
        """
        self.worked_today = False
        work_hours = None
        max_work = self.parameters['methods']['OGI']['max_workday']

        if self.parameters['methods']['OGI']['consider_daylight']:
            daylight_hours = self.state['daylight'].get_daylight(self.state['t'].current_timestep)
            if daylight_hours <= max_work:
                work_hours = daylight_hours
            elif daylight_hours > max_work:
                work_hours = max_work
        elif not self.parameters['methods']['OGI']['consider_daylight']:
            work_hours = max_work

        if work_hours < 24 and work_hours != 0:
            start_hour = (24 - work_hours) / 2
            end_hour = start_hour + work_hours
        else:
            print(
                'Unreasonable number of work hours specified for OGI crew ' +
                str(self.crewstate['id']))

        self.allowed_end_time = self.state['t'].current_date.replace(
            hour=int(end_hour), minute=0, second=0)
        self.state['t'].current_date = self.state['t'].current_date.replace(
            hour=int(start_hour))  # Set start of work day

        
        if self.scheduling['geography']:
            # start day by reading the location of the LDAR team 
            x_LDAR = self.state['current_x']
            y_LDAR = self.state['current_y']
            Home,DIST = find_homebase(x_LDAR,y_LDAR,self.HX,self.HY) 
            x_LDAR = Home[0]
            y_LDAR = Home[1]
            self.state['current_x'] = x_LDAR
            self.state['current_y'] = y_LDAR
            drive_home =timedelta(minutes=(DIST/80)*60) 

        # Check if there is a partially finished site from yesterday
        if len(self.rollover) > 0:
            # Check to see if the remainder of this site can be finished today
            # (if not, this one is huge!) projection includes the time it would
            #  time to drive back to the home base
            projected_end_time = self.state['t'].current_date + \
                timedelta(minutes=int(self.rollover[1]))
            
            if self.scheduling['geography']:
                # start day by reading the location of the LDAR team 
                x_LDAR = self.state['current_x']
                y_LDAR = self.state['current_y']
                Home,DIST = find_homebase(x_LDAR,y_LDAR,self.HX,self.HY) 
                x_LDAR = Home[0]
                y_LDAR = Home[1]
                self.state['current_x'] = x_LDAR
                self.state['current_y'] = y_LDAR
                drive_home =timedelta(minutes=(DIST/80)*60)
            else:
                
                drive_home = timedelta(
                    minutes=int(
                        self.state['offsite_times']
                        [np.random.randint(0, len(self.state['offsite_times']))]))
            

            if (projected_end_time + drive_home) > self.allowed_end_time:
                # There's not enough time left for that site today -
                #  get started and figure out how much time remains
                minutes_remaining = (projected_end_time - self.allowed_end_time).total_seconds()/60
                self.rollover = []
                self.rollover.append(self.rollover[0])
                self.rollover.append(minutes_remaining)
                self.state['t'].current_date = self.allowed_end_time
                self.worked_today = True
            elif (projected_end_time + drive_home) <= self.allowed_end_time:
                # Looks like we can finish off that site today
                self.visit_site(self.rollover[0])
                self.rollover = []
                self.worked_today = True

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
                    
                if found_site:
                    projected_end_time = self.state['t'].current_date + \
                        timedelta(minutes=int(site['OGI_time']))
                    
                self.state['t'].current_date += timedelta(minutes= travel_time)
                
                if self.state['t'].current_date.hour > int(end_hour):
                    x_temp = np.float(site['lon'])
                    y_temp = np.float(site['lat'])
                    x_cut = self.state['current_x'] 
                    y_cut = self.state['current_y']
                    Home,DIST = find_homebase_opt(x_temp,y_temp,x_cut,y_cut,self.HX,self.HY)
                    
                    self.state['current_x'] = Home[0]
                    self.state['current_y'] = Home[1]
                    minutes_remaining = (
                            projected_end_time - self.allowed_end_time).total_seconds()/60
                    self.rollover = []
                    self.rollover.append(site)
                    self.rollover.append(minutes_remaining)
                    self.state['t'].current_date = self.allowed_end_time
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
            while self.state['t'].current_date < self.allowed_end_time:
                facility_ID, found_site, site = self.choose_site(0,0)
                if not found_site:
                    break  # Break out if no site can be found
    
                # Check to make sure there's enough time left in the day to do this site
                # This projection includes the time it would time to drive back to the home base
                if found_site:
                    projected_end_time = self.state['t'].current_date + \
                        timedelta(minutes=int(site['OGI_time']))
                    drive_home = timedelta(
                        minutes=int(
                            self.state['offsite_times']
                            [np.random.randint(0, len(self.state['offsite_times']))]))
                    if (projected_end_time + drive_home) > self.allowed_end_time:
                        # There's not enough time left for that site today
                        # - get started and figure out how much time remains
                        minutes_remaining = (
                            projected_end_time - self.allowed_end_time).total_seconds()/60
                        self.rollover = []
                        self.rollover.append(site)
                        self.rollover.append(minutes_remaining)
                        self.state['t'].current_date = self.allowed_end_time
    
                    # There's enough time left in the day for this site
                    elif (projected_end_time + drive_home) <= self.allowed_end_time:
                        self.visit_site(site)
                    self.worked_today = True

        if self.worked_today:
            self.timeseries['OGI_cost'][self.state['t'].current_timestep] += \
                self.parameters['methods']['OGI']['cost_per_day']
            self.timeseries['total_daily_cost'][self.state['t'].current_timestep] += \
                self.parameters['methods']['OGI']['cost_per_day']

        return

    def choose_site(self,x_LDAR,y_LDAR):
        """
        Choose a site to survey.

        """

        # Sort all sites based on a neglect ranking
        self.state['sites'] = sorted(
            self.state['sites'],
            key=lambda k: k['OGI_t_since_last_LDAR'],
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
                if not site['attempted_today_OGI?']:
    
                    # If the site is 'unripened' (i.e. hasn't met the minimum interval),
                    # break out - no LDAR today
                    if site['OGI_t_since_last_LDAR'] < int(site['OGI_min_int']):
                        self.state['t'].current_date = self.state['t'].current_date.replace(hour=23)
                        break
    
                    # Else if site-specific required visits have not been met for the year
                    elif site['surveys_done_this_year_OGI'] < int(site['OGI_RS']):
    
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
                                    site['OGI_surveys_conducted'] += 1
                                    site['surveys_done_this_year_OGI'] += 1
                                    site['OGI_t_since_last_LDAR'] = 0
                                    break
                            else:
                                # The site passes all the tests! Choose it!
                                facility_ID = site['facility_ID']
                                found_site = True
        
                                # Update site
                                site['OGI_surveys_conducted'] += 1
                                site['surveys_done_this_year_OGI'] += 1
                                site['OGI_t_since_last_LDAR'] = 0
                                break
    
                        else:
                            site['attempted_today_OGI?'] = True
        
        if self.scheduling['route_planning']:
            if len(Site_T) > 0: 
                j = Site_T.index(min(Site_T))
                site = s_list[j]
                facility_ID = site['facility_ID']
                travel_time = min(Site_T)*60
                found_site = True
        
                # Update site
                site['OGI_surveys_conducted'] += 1
                site['surveys_done_this_year_OGI'] += 1
                site['OGI_t_since_last_LDAR'] = 0


        if self.scheduling['geography'] or self.scheduling['route_planning']:        
            return (facility_ID, found_site, site, travel_time)
        else:
            return (facility_ID, found_site, site)

    def visit_site(self, site):
        """
        Look for leaks at the chosen site.
        """

        # Identify all the leaks at a site
        leaks_present = []
        for leak in self.state['leaks']:
            if leak['facility_ID'] == site['facility_ID']:
                if leak['status'] == 'active':
                    leaks_present.append(leak)

        # Detection module from Ravikumar et al 2018
        for leak in leaks_present:
            k = np.random.normal(4.9, 0.3)
            x0 = np.random.normal(self.config['MDL'][0], self.config['MDL'][1])
            x0 = math.log10(x0 * 3600)  # Convert from g/s to g/h and take log

            if leak['rate'] == 0:
                prob_detect = 0
            else:
                x = math.log10(leak['rate'] * 3600)  # Convert from g/s to g/h
                prob_detect = 1 / (1 + math.exp(-k * (x - x0)))
            detect = np.random.binomial(1, prob_detect)

            if detect:
                if leak['tagged']:
                    self.timeseries['OGI_redund_tags'][self.state['t'].current_timestep] += 1

                    # Add these leaks to the 'tag pool'
                elif not leak['tagged']:
                    leak['tagged'] = True
                    leak['date_tagged'] = self.state['t'].current_date
                    leak['tagged_by_company'] = self.config['name']
                    leak['tagged_by_crew'] = self.crewstate['id']
                    self.state['tags'].append(leak)

            elif not detect:
                site['OGI_missed_leaks'] += 1

        self.state['t'].current_date += timedelta(minutes=int(site['OGI_time']))
        self.state['t'].current_date += timedelta(
            minutes=int(
                self.state['offsite_times']
                [np.random.randint(0, len(self.state['offsite_times']))]))
        self.timeseries['OGI_sites_visited'][self.state['t'].current_timestep] += 1

        return
