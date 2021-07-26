from datetime import timedelta
import numpy as np
import pandas as pd 
from geography.homebase import find_homebase, find_homebase_opt
from geography.distance import get_distance
from methods.deployment.base import sched_crew as base_sched_crew


class Schedule(base_sched_crew):
    def __init__(self, id, lat, lon, state, config, parameters, deployment_days, home_bases=None):
        self.parameters = parameters
        self.config = config
        self.state = state
        self.deployment_days = deployment_days
        self.crew_lat = lat
        self.crew_lon = lon
        self.home_bases = home_bases
        self.work_hours = None
        self.start_hour = None
        self.end_hour = None
        self.allowed_end_time = None
        self.last_site_travel_home_min = None
        self.rollover = None  # (rollover_site_plan)
        self.travel_all_day = False
        self.scheduling = self.config['scheduling']
        # define a list of home bases for crew and redefine the the initial location of crew
        if self.scheduling['route_planning']:
            hb_file = self.parameters['working_directory'] + \
                self.scheduling['home_bases_files']
            HB = pd.read_csv(hb_file, sep=',')
            self.crew_lon = self.scheduling['LDAR_crew_init_location'][0]
            self.crew_lat = self.scheduling['LDAR_crew_init_location'][1]

            self.home_bases = list(zip(HB['lon'], HB['lat']))

    # --- inherited ---
    # base.crew ->  get_work_hours()

    def plan_visit(self, site, next_site=None):
        """ Check survey and travel times and see if there is enough time
            to go to site. If a site survey was started on a previous day
            the amount of minutes rolled over will be used for survey time.

        Args:
            site (dict): single site

        Returns:
            {
                'site': same as input
                'go_to_site': whether there is enough time to go to site
                'travel_to_mins': travel time in minutes
                'travel_home_mins': travel time in minutes
                'LDAR_mins_onsite': minutes onsite
                'LDAR_mins': travel to and survey time (excludes travel home time)
                'remaining_mins': minutes left in survey
        }
        """
        name = self.config['label']
        site['{}_attempted_today?'.format(name)] = True
        if not self.deployment_days[site['lon_index'], site['lat_index'],
                                    self.state['t'].current_timestep]:
            return None
        if self.rollover:
            if site['facility_ID'] == self.rollover['site']['facility_ID']:
                # Remove facility from rollover list, and retrieve remaining survey minutes
                LDAR_mins = self.rollover['site']['remaining_mins']
            else: 
                LDAR_mins = int(site['{}_time'.format(name)])
        else:
            # Get survey minutes
            LDAR_mins = int(site['{}_time'.format(name)])
        # Get travel time minutes, and check if there is enough time.
        travel_to_plan = self.get_travel_plan(next_loc=site)
        travel_home_plan = self.get_travel_plan(
            next_loc=next_site, homebase=True)
        survey_times = self.check_visit_time(
            LDAR_mins, travel_to_plan['travel_time'],
            travel_home_plan['travel_time'])
        return {
            'site': site,
            'go_to_site': survey_times['go_to_site'],
            'travel_to_mins': travel_to_plan['travel_time'],
            'travel_home_mins': travel_home_plan['travel_time'],
            'LDAR_mins_onsite': survey_times['LDAR_mins_onsite'],
            # mins is LDAR + Travel to time. Home time is called at end of day
            'LDAR_mins': survey_times['LDAR_mins'],
            'remaining_mins': survey_times['remaining_mins'],
        }

    def get_travel_plan(self, next_loc=None, homebase=False):
        """ Get travel time to next location and next homebase

        Args:
            next_loc (dict, optional): next site. Defaults to None.
            homebase (bool, optional): If next site is a homebase. Defaults to False.

        Returns:
            dict: {
                'travel_time': time in minutes to trave between current site and crews
                 current location
                'next_site': next location the crew will travel to.
            }
        """
        if self.config['scheduling']['route_planning']:
            # start day by reading the location of the LDAR team
            # find nearest home base
            if homebase and next_loc:
                next_loc, distance = find_homebase_opt(
                    self.crew_lon, self.crew_lat, next_loc['lon'], next_loc['lat'], self.home_bases)
            elif homebase and not next_loc:
                next_loc, distance = find_homebase(
                    self.crew_lon, self.crew_lat, self.home_bases)
        
            else:
                distance = get_distance(
                    self.crew_lon, self.crew_lat,
                    next_loc['lon'], next_loc['lat'], "Haversine")

            speed = np.random.choice(self.config['scheduling']['speed_list'])
            travel_time = (distance/speed)*60
        # ----------------------------------------------------------
        else:
            travel_time = np.random.choice(self.config['t_bw_sites'])
        # returned dictionary 
        out_dict = {
            'travel_time': travel_time,
            'next_loc': next_loc,
        }
        return out_dict

    def check_visit_time(self, survey_mins, travel_to_mins, travel_home_mins):
        """Check the survey and travel times, determine if there is enough
           time to go to site.

        Args:
            survey_mins (float): minutes required to perform or finish survey
            travel_to_mins (float): minutes required to travel to site
            travel_home_mins (float): minutes required to travel home from site

        Returns:
            dict:   'go_to_site' (boolean): go_to_site,
                    'LDAR_mins_onsite' (minutes): survey time today,
                    'travel_to_mins' (minutes): travel time to site,
                    'travel_home_mins' (minutes): travel time from site,
                    'remaining_mins' (minutes): minutes left in survey that can be rolled over
                     to another day,
        """
        mins_left_in_day = (self.allowed_end_time - self.state['t'].current_date) \
            .total_seconds()/60
        if travel_to_mins >= mins_left_in_day:
            # Not enough time to travel to site
            go_to_site = False
            LDAR_mins_onsite = 0
        elif travel_to_mins + travel_home_mins >= mins_left_in_day:
            # Not enough time to travel to and from site
            # --HBD-- Should consider, splitting up travel, if site is too far to do in a day.
            go_to_site = False
            LDAR_mins_onsite = 0
        elif travel_to_mins + travel_home_mins + survey_mins <= mins_left_in_day:
            # Enough time to travel to site
            go_to_site = True
            LDAR_mins_onsite = survey_mins
        elif travel_to_mins + survey_mins <= mins_left_in_day:
            # Enough time to travel to and from site
            # --HBD-- Right now, Max work day doesnt effect travel_home_mins
            # code could could be added here to prevent overtime hours from
            # travelling home (in some cases this would cause trip to run into
            # the next day)
            go_to_site = True
            LDAR_mins_onsite = survey_mins
        # --HBD-- temporarily removed travel home from rollover calcs.
        # elif (travel_to_mins + travel_home_mins + survey_mins) > mins_left_in_day:
        elif (travel_to_mins + survey_mins) > mins_left_in_day:
            # Enough time to travel, but not enough time to work go, and rollover minutes.
            go_to_site = True
            # --HBD-- temporarily removed travel home from rollover calcs.
            # LDAR_mins_onsite = mins_left_in_day - (travel_to_mins + travel_home_mins)
            LDAR_mins_onsite = mins_left_in_day - travel_to_mins
        else:
            # Enough time to travel and work
            go_to_site = True
            LDAR_mins_onsite = survey_mins
        remaining_mins = survey_mins - LDAR_mins_onsite
        LDAR_mins = travel_to_mins + LDAR_mins_onsite
        if go_to_site:
            self.last_site_travel_home_min = travel_home_mins
        out_dict = {
            'LDAR_mins': LDAR_mins,
            'go_to_site': go_to_site,
            'LDAR_mins_onsite': LDAR_mins_onsite,
            'travel_to_mins': travel_to_mins,
            'travel_home_mins': travel_home_mins,
            'remaining_mins': remaining_mins,
        }
        return out_dict
   # ---------------------------------------------

    def choose_site(self, site_plan_list):
        """Choose the next visit site based on travel time 

        Args:
            site_plan_list: a list of travel plan dictionary output from plan_visit()

        Returns:
            A dictionary (travel plan) of the selected site 
        """
        if self.rollover:
            site_plan = self.rollover

        # route planning -> find the nearest site
        if self.config['scheduling']['route_planning']:
            # sort the list based on travel time
            sorted_site_plan_list = sorted(
                site_plan_list, key=lambda k: k['travel_to_mins'])
            # first site plan in the sorted list has minimum travel time
            site_plan = sorted_site_plan_list[0]

        else:
            # else just need 1st site to visit
            site_plan = site_plan_list[0]
        return site_plan

   # ------------------------------------------------
    def choose_accommodation(self, site=None):
        """choose the home base for crew 

        Args:
            site: if site is defined, then choose the home base that close to both current location and next site
        Returns:

        """
        if self.config['scheduling']['route_planning']:
            if site:
                # today needs to travel all day
                hb = self.get_travel_plan(next_loc=site, homebase=True)

            else:
                # if not means crew need to travel all the way to reach the next site
                hb = self.get_travel_plan(homebase=True)

            self.crew_lon = hb['next_loc'][0]
            self.crew_lat = hb['next_loc'][1]
            self.last_site_travel_home_min = hb['travel_time']
        else:
            # travel time is sampled if not active route_planning
            self.last_site_travel_home_min = np.random.choice(
                self.config['t_bw_sites'])
   # __________________________________________________

    def update_schedule(self, work_mins, next_lat=None, next_lon=None):
        """ Update current time and crew location

        Args:
            work_mins (float): time in minutes
            next_lat (float, optional): Next location to move crew. Defaults to None.
            next_lon (float, optional): Next location to move crew. Defaults to None.
        """
        self.state['t'].current_date += timedelta(minutes=int(work_mins))

    def start_day(self, site_pool):
        """ Initiate work hours and move current time to the crew starting hour
        """
		# obtain locs of crew 
        cur_lon = self.crew_lon
        cur_lat = self.crew_lat
        self.travel_all_day = False
		# get work hour 
        self.get_work_hours()
        self.state['t'].current_date = self.state['t'].current_date.replace(
            hour=int(self.start_hour))  # Set start of work
		# get a estimated remaining time 
        est_mins_remaining = (self.end_hour - self.start_hour)*60
        Plan_list = []
		# while crew still have time today 
        while est_mins_remaining > 0 and len(site_pool) > 0:
			# obtain all travel plans 
            site_plan_list = []
            for site in site_pool:
                site_plan = self.plan_visit(site)
                if site_plan and site_plan['go_to_site']:
                    site_plan_list.append(site_plan)
			
            # if crew at least have a site to go today 
            if len(site_plan_list)>0: 
				# choose a site to visit 
                next_site_plan = self.choose_site(site_plan_list)
				# add that site to the daily site plan 
                Plan_list.append(next_site_plan)
				# update the esitamed mins 
                est_mins_remaining = - next_site_plan['LDAR_mins']
                # pop that site from site list
                site_idx = site_plan_list.index(next_site_plan)
				# update site pool 
                site_pool = site_pool.pop(site_idx)
				# update locations of crew 
                self.crew_lon = next_site_plan['site']['lon']
                self.crew_lat = next_site_plan['site']['lat']
            else:
                break
            
        # add to rollover
        if len(Plan_list)>0: 
            if Plan_list[-1]['remaining_mins'] > 0:
                self.rollover = Plan_list[-1]
        else: 
            self.travel_all_day = True
		# reassign locs of crew 
        self.crew_lon = cur_lon
        self.crew_lat = cur_lat

        return Plan_list

    def end_day(self,site_pool):
        """ Travel home; update time to travel to homebase
        """
        if self.config['scheduling']['route_planning']: 
            if self.travel_all_day:
                self.next_travel_all_day_site = site_pool[0]
                self.choose_accommodation(site=self.next_travel_all_day_site)
            else:
                self.choose_accommodation()
        else:
            self.choose_accommodation()
            self.update_schedule(self.last_site_travel_home_min)
            self.last_site_travel_home_min = None
