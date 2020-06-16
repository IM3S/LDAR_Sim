# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim) 
# File:        LDAR-Sim 
# Purpose:     Primary module of LDAR-Sim
#
# Copyright (C) 2018-2020  Thomas Fox, Mozhou Gao, Thomas Barchyn, Chris Hugenholtz
#    
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------------------

import pandas as pd
import numpy as np
import csv
import os
import datetime
import sys
import random
from sensitivity import *
from operator_agent import *
from plotter import *
from daylight_calculator import *


class LdarSim:
    def __init__(self, state, parameters, timeseries):
        """
        Construct the simulation.
        """

        self.state = state
        self.parameters = parameters
        self.timeseries = timeseries

        # Read in data files
        self.state['empirical_counts'] = np.array(pd.read_csv(self.parameters['working_directory'] +
                self.parameters['count_file']).iloc[:, 0])
        self.state['empirical_leaks'] = np.array(pd.read_csv(self.parameters['working_directory'] +
                self.parameters['leak_file']).iloc[:, 0]) * 86.4  # Convert g/s to kg/day
        self.state['empirical_sites'] = np.array(pd.read_csv(self.parameters['working_directory'] +
                self.parameters['vent_file']).iloc[:, 0]) * 86.4  # Convert g/s to kg/day
        self.state['offsite_times'] = np.array(pd.read_csv(self.parameters['working_directory'] +
                self.parameters['t_offsite_file']).iloc[:, 0])

        # Read in the sites as a list of dictionaries
        with open(self.parameters['working_directory'] + self.parameters['infrastructure_file']) as f:
            self.state['sites'] = [{k: v for k, v in row.items()}
                                   for row in csv.DictReader(f, skipinitialspace=True)]

        # Sample sites
        if self.parameters['site_samples'][0]:
            self.state['sites'] = random.sample(self.state['sites'], self.parameters['site_samples'][1])

        if self.parameters['subtype_times'][0]:
            subtype_times = pd.read_csv(self.parameters['subtype_times'][1])
            cols_to_add = subtype_times.columns[1:].tolist()
            for col in cols_to_add:
                for site in self.state['sites']:
                    site[col] = subtype_times.loc[subtype_times['subtype_code'] ==
                                                  int(site['subtype_code']), col].iloc[0]

        # Shuffle all the entries to randomize order for identical 't_Since_last_LDAR' values
        random.shuffle(self.state['sites'])

        # Additional variable(s) for each site
        for site in self.state['sites']:
            site.update({'total_emissions_kg': 0})
            site.update({'active_leaks': 0})
            site.update({'repaired_leaks': 0})
            site.update({'currently_flagged': False})
            site.update({'flagged_by': None})
            site.update({'date_flagged': None})
            site.update({'lat_index': min(range(len(self.state['weather'].latitude)),
                                          key=lambda i: abs(self.state['weather'].latitude[i] - float(site['lat'])))})
            site.update({'lon_index': min(range(len(self.state['weather'].longitude)),
                                          key=lambda i: abs(
                                              self.state['weather'].longitude[i] - float(site['lon']) % 360))})

            # Check to make sure site is within range of grid-based data
            if float(site['lat']) > max(self.state['weather'].latitude):
                sys.exit(
                    'Simulation terminated: One or more sites is too far North and is outside the spatial bounds of '
                    'your weather data!')
            if float(site['lat']) < min(self.state['weather'].latitude):
                sys.exit(
                    'Simulation terminated: One or more sites is too far South and is outside the spatial bounds of '
                    'your weather data!')
            if float(site['lon']) % 360 > max(self.state['weather'].longitude):
                sys.exit(
                    'Simulation terminated: One or more sites is too far East and is outside the spatial bounds of '
                    'your weather data!')
            if float(site['lon']) % 360 < min(self.state['weather'].longitude):
                sys.exit(
                    'Simulation terminated: One or more sites is too far West and is outside the spatial bounds of '
                    'your weather data!')

        # Configure sensitivity analysis, if requested (code block must remain here -
        # after site initialization and before method initialization)
        if self.parameters['sensitivity']['perform']:
            self.sensitivity = Sensitivity(self.parameters, self.timeseries, self.state)

        # Initialize method(s) to be used; append to state
        for m in self.parameters['methods']:
            try:
                company_name = str(m) + '_company'
                module = __import__(company_name)
                func = getattr(module, company_name)
                self.state['methods'].append(func(self.state,
                                                  self.parameters, self.parameters['methods'][m], timeseries))
            except:
                print('Cannot add this method: ' + m)

        # Generate initial leak count for each site
        for site in self.state['sites']:
            n_leaks = self.state['empirical_counts'][np.random.randint(0, len(self.state['empirical_counts']))]
            if n_leaks < 0:  # This can happen occasionally during sensitivity analysis
                n_leaks = 0
            site.update({'initial_leaks': n_leaks})
            self.state['init_leaks'].append(site['initial_leaks'])

        self.state['max_rate'] = max(self.state['empirical_leaks'])

        # For each leak, create a dictionary and populate values for relevant keys
        for site in self.state['sites']:
            if site['initial_leaks'] > 0:
                for leak in range(site['initial_leaks']):
                    self.state['leaks'].append({
                        'leak_ID': site['facility_ID'] + '_' + str(len(self.state['leaks']) + 1).zfill(10),
                        'facility_ID': site['facility_ID'],
                        'rate': self.state['empirical_leaks'][np.random.randint(0, len(self.state['empirical_leaks']))],
                        'status': 'active',
                        'tagged': False,
                        'days_active': 0,
                        'component': 'unknown',
                        'date_began': self.state['t'].current_date,
                        'date_found': None,
                        'date_repaired': None,
                        'repair_delay': None,
                        'found_by_company': None,
                        'found_by_crew': None,
                        'requires_shutdown': False,
                    })

        # Initialize operator
        if self.parameters['consider_operator']:
            self.state['operator'] = OperatorAgent(self.timeseries, self.parameters, self.state)

        # If working without methods (operator only), need to get the first day going
        if not bool(self.parameters['methods']):
            self.state['t'].current_date = self.state['t'].current_date.replace(hour=1)

        # Initialize daylight 
        if self.parameters['consider_daylight']:
            self.state['daylight'] = DaylightCalculatorAve(self.state, self.parameters)

        # Initialize empirical distribution of vented emissions
        if self.parameters['consider_venting']:
            self.state['empirical_vents'] = []

            # Run Monte Carlo simulations to get distribution of vented emissions
            for i in range(1000):
                n_mc_leaks = self.state['empirical_counts'][np.random.randint(0, len(self.state['empirical_counts']))]
                mc_leaks = []
                for leak in range(n_mc_leaks):
                    mc_leaks.append(
                        self.state['empirical_leaks'][np.random.randint(0, len(self.state['empirical_leaks']))])
                mc_leak_total = sum(mc_leaks)
                mc_site_total = self.state['empirical_sites'][np.random.randint(0, len(self.state['empirical_sites']))]
                mc_vent_total = mc_site_total - mc_leak_total
                self.state['empirical_vents'].append(mc_vent_total)

            # Change negatives to zero
            self.state['empirical_vents'] = [0 if i < 0 else i for i in self.state['empirical_vents']]

        return

    def update(self):
        """
        this rolls the model forward one timestep
        returns nothing
        """

        self.update_state()  # Update state of sites and leaks
        self.add_leaks()  # Add leaks to the leak pool
        self.find_leaks()  # Find leaks
        self.repair_leaks()  # Repair leaks
        self.report()  # Assemble any reporting about model state
        return

    def update_state(self):
        """
        update the state of active leaks
        """
        for leak in self.state['leaks']:
            if leak['status'] == 'active':
                leak['days_active'] += 1

        self.active_leaks = []
        for leak in self.state['leaks']:
            if leak['status'] == 'active':
                self.active_leaks.append(leak)
        self.timeseries['active_leaks'].append(len(self.active_leaks))
        self.timeseries['datetime'].append(self.state['t'].current_date)

    def add_leaks(self):
        """
        add new leaks to the leak pool
        """
        # First, determine whether each site gets a new leak or not
        for site in self.state['sites']:
            n_leaks = np.random.binomial(1, self.parameters['LPR'])
            if n_leaks == 0:
                site.update({'n_new_leaks': 0})
            else:
                site.update({'n_new_leaks': n_leaks})

        # For each leak, create a dictionary and populate values for relevant keys
        for site in self.state['sites']:
            if site['n_new_leaks'] > 0:
                for leak in range(site['n_new_leaks']):
                    self.state['leaks'].append({
                        'leak_ID': site['facility_ID'] + '_' + str(len(self.state['leaks']) + 1).zfill(10),
                        'facility_ID': site['facility_ID'],
                        'rate': self.state['empirical_leaks'][np.random.randint(0, len(self.state['empirical_leaks']))],
                        'status': 'active',
                        'days_active': 0,
                        'tagged': False,
                        'component': 'unknown',
                        'date_began': self.state['t'].current_date,
                        'date_found': None,
                        'date_repaired': None,
                        'repair_delay': None,
                        'found_by_company': None,
                        'found_by_crew': None,
                        'requires_shutdown': False,
                    })

        return

    def find_leaks(self):
        """
        Loop over all your methods in the simulation and ask them to find some leaks.
        """

        for m in self.state['methods']:
            m.find_leaks()

        if self.parameters['consider_operator']:
            if self.state['t'].current_date.weekday() == 0:
                self.state['operator'].work_a_day()

        return

    def repair_leaks(self):
        """
        Repair tagged leaks and remove from tag pool.
        """
        for tag in self.state['tags']:
            if tag['found_by_company'] != 'operator':
                if (self.state['t'].current_date - tag['date_found']).days >= (
                        self.parameters['repair_delay'] + self.parameters['methods'][tag['found_by_company']][
                        'reporting_delay']):
                    tag['status'] = 'repaired'
                    tag['tagged'] = False
                    tag['date_repaired'] = self.state['t'].current_date
                    tag['repair_delay'] = (tag['date_repaired'] - tag['date_found']).days
            elif tag['found_by_company'] == 'operator':
                if (self.state['t'].current_date - tag['date_found']).days >= self.parameters['repair_delay']:
                    tag['status'] = 'repaired'
                    tag['tagged'] = False
                    tag['date_repaired'] = self.state['t'].current_date
                    tag['repair_delay'] = (tag['date_repaired'] - tag['date_found']).days

            self.state['tags'] = [tag for tag in self.state['tags'] if tag['status'] == 'active']

        return

    def report(self):
        """
        Daily reporting of leaks, repairs, and emissions.
        """

        # Update timeseries
        self.timeseries['new_leaks'].append(sum(d['n_new_leaks'] for d in self.state['sites']))
        self.timeseries['cum_repaired_leaks'].append(sum(d['status'] == 'repaired' for d in self.state['leaks']))
        self.timeseries['daily_emissions_kg'].append(sum(d['rate'] for d in self.active_leaks))
        self.timeseries['n_tags'].append(len(self.state['tags']))

        # Optional day tracking through simulation (uncomment following line to enable)
        #        print ('Day ' + str(self.state['t'].current_timestep) + ' complete!')

        return

    def finalize(self):
        """
        Compile and write output files.
        """
        output_directory = os.path.join(self.parameters['working_directory'], 'outputs/', self.parameters['program_name'])
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        if self.parameters['write_data']:

            # Attribute individual leak emissions to site totals
            for leak in self.state['leaks']:
                tot_emissions_kg = leak['days_active'] * leak['rate']
                for site in self.state['sites']:
                    if site['facility_ID'] == leak['facility_ID']:
                        site['total_emissions_kg'] += tot_emissions_kg
                        if leak['status'] == 'active':
                            site['active_leaks'] += 1
                        elif leak['status'] == 'repaired':
                            site['repaired_leaks'] += 1
                        break

            # Generate some dataframes           
            for site in self.state['sites']:
                del site['n_new_leaks']

            leak_df = pd.DataFrame(self.state['leaks'])
            time_df = pd.DataFrame(self.timeseries)
            site_df = pd.DataFrame(self.state['sites'])

            # Create some new variables for plotting
            site_df['cum_frac_sites'] = list(site_df.index)
            site_df['cum_frac_sites'] = site_df['cum_frac_sites'] / max(site_df['cum_frac_sites'])
            site_df['cum_frac_emissions'] = np.cumsum(sorted(site_df['total_emissions_kg'], reverse=True))
            site_df['cum_frac_emissions'] = site_df['cum_frac_emissions'] / max(site_df['cum_frac_emissions'])

            leaks_active = leak_df[leak_df.status == 'active'].sort_values('rate', ascending=False)
            leaks_repaired = leak_df[leak_df.status == 'repaired'].sort_values('rate', ascending=False)

            leaks_active['cum_frac_leaks'] = list(np.linspace(0, 1, len(leaks_active)))
            leaks_active['cum_rate'] = np.cumsum(leaks_active['rate'])
            leaks_active['cum_frac_rate'] = leaks_active['cum_rate'] / max(leaks_active['cum_rate'])

            if len(leaks_repaired) > 0:
                leaks_repaired['cum_frac_leaks'] = list(np.linspace(0, 1, len(leaks_repaired)))
                leaks_repaired['cum_rate'] = np.cumsum(leaks_repaired['rate'])
                leaks_repaired['cum_frac_rate'] = leaks_repaired['cum_rate'] / max(leaks_repaired['cum_rate'])

            leak_df = leaks_active.append(leaks_repaired)

            # Write csv files
            leak_df.to_csv(output_directory + '/leaks_output_' + self.parameters['simulation'] + '.csv', index=False)
            time_df.to_csv(output_directory + '/timeseries_output_' + self.parameters['simulation'] + '.csv',
                           index=False)
            site_df.to_csv(output_directory + '/sites_output_' + self.parameters['simulation'] + '.csv', index=False)

            # Write metadata
            metadata = open(output_directory + '/metadata_' + self.parameters['simulation'] + '.txt', 'w')
            metadata.write(str(self.parameters) + '\n' +
                           str(datetime.datetime.now()))
            metadata.close()

        # Make maps and append site-level DD and MCB data
        if self.parameters['make_maps']:
            for m in self.state['methods']:
                m.make_maps()
                m.site_reports()

        # Make plots
        if self.parameters['make_plots']:
            make_plots(leak_df, time_df, site_df, self.parameters['simulation'], self.parameters['spin_up'],
                       output_directory)

        # Write sensitivity analysis data, if requested
        if self.parameters['sensitivity']['perform']:
            self.sensitivity.write_data()

        # Return to original working directory
        os.chdir(self.parameters['working_directory'])
        os.chdir('..')

        #print('Simulation complete. Thank you for using the LDAR Simulator.')
        return
