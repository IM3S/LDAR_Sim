# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim) 
# File:        Aircraft company
# Purpose:     Company managing aircraft agents
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

from aircraft_crew import *
from weather_lookup import *
from generic_functions import gap_calculator
import numpy as np
import os
from osgeo import gdal
from osgeo import osr


class aircraft_company:
    def __init__(self, state, parameters, config, timeseries):
        """
        Initialize a company to manage the aircraft crews (e.g. a contracting company).

        """
        #print('Initializing aircraft company...')
        self.state = state
        self.parameters = parameters
        self.config = config
        self.timeseries = timeseries
        self.crews = []
        self.deployment_days = self.state['weather'].deployment_days('aircraft')
        self.timeseries['aircraft_prop_sites_avail'] = []
        self.timeseries['aircraft_cost'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['aircraft_eff_flags'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['aircraft_flags_redund1'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['aircraft_flags_redund2'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['aircraft_flags_redund3'] = np.zeros(self.parameters['timesteps'])
        self.timeseries['aircraft_sites_visited'] = np.zeros(self.parameters['timesteps'])

        # Additional variable(s) for each site       
        for site in self.state['sites']:
            site.update({'aircraft_t_since_last_LDAR': 0})
            site.update({'aircraft_surveys_conducted': 0})
            site.update({'attempted_today_aircraft?': False})
            site.update({'surveys_done_this_year_aircraft': 0})
            site.update({'aircraft_missed_leaks': 0})

        # Initialize 2D matrices to store deployment day (DD) counts and MCBs
        self.DD_aircraft_map = np.zeros((len(self.state['weather'].longitude), len(self.state['weather'].latitude)))
        self.MCB_aircraft_map = np.zeros((len(self.state['weather'].longitude), len(self.state['weather'].latitude)))

        # Initialize the individual aircraft crews (the agents)
        for i in range(config['n_crews']):
            self.crews.append(aircraft_crew(state, parameters, config, timeseries, self.deployment_days, id=i + 1))

        return

    def find_leaks(self):
        """
        The aircraft company tells all the crews to get to work.
        """

        for i in self.crews:
            i.work_a_day()

        # Update method-specific site variables each day
        for site in self.state['sites']:
            site['aircraft_t_since_last_LDAR'] += 1
            site['attempted_today_aircraft?'] = False

        if self.state['t'].current_date.day == 1 and self.state['t'].current_date.month == 1:
            for site in self.state['sites']:
                site['surveys_done_this_year_aircraft'] = 0

        # Calculate proportion sites available
        available_sites = 0
        for site in self.state['sites']:
            if self.deployment_days[site['lon_index'], site['lat_index'], self.state['t'].current_timestep]:
                available_sites += 1
        prop_avail = available_sites / len(self.state['sites'])
        self.timeseries['aircraft_prop_sites_avail'].append(prop_avail)

        return

    def make_maps(self):
        """
        If requested, makes maps of proportion of timesteps that are deployment days.
        Also outputs a map of MCB (maximum condition blackout) over period of analysis.
        """

        #print('Generating aircraft maps...')

        # For each cell, sum the total number of deployment days and divide by total number of days        
        for lon in range(len(self.state['weather'].longitude)):
            for lat in range(len(self.state['weather'].latitude)):
                self.DD_aircraft_map[lon, lat] = (self.deployment_days[lon, lat, :].sum()) / self.parameters[
                    'timesteps']

        # Calculate MCB for each cell
        for lon in range(len(self.state['weather'].longitude)):
            for lat in range(len(self.state['weather'].latitude)):
                self.MCB_aircraft_map[lon, lat] = gap_calculator(self.deployment_days[lon, lat, :])

        # Set variables necessary for writing map files
        DD_aircraft_output = np.swapaxes(self.DD_aircraft_map, axis1=0, axis2=1)
        MCB_aircraft_output = np.swapaxes(self.MCB_aircraft_map, axis1=0, axis2=1)
        lon, lat = self.state['weather'].longitude, self.state['weather'].latitude
        xmin, ymin, xmax, ymax = [lon.min(), lat.min(), lon.max(), lat.max()]
        nrows, ncols = np.shape(DD_aircraft_output)
        xres = (xmax - xmin) / float(ncols)
        yres = (ymax - ymin) / float(nrows)
        geotransform = (xmin, xres, 0, ymax, 0, -yres)

        # Set output directory
        output_directory = os.path.join(self.parameters['working_directory'], 'outputs/', self.parameters['program_name'])
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        os.chdir(output_directory)

        # Export 2D proportions matrix as map
        output_raster = gdal.GetDriverByName('GTiff').Create(
            'DD_aircraft_map_' + self.parameters['simulation'] + '.tif', ncols, nrows, 1, gdal.GDT_Float32)
        output_raster.SetGeoTransform(geotransform)  # Specify file coordinates
        srs = osr.SpatialReference()  # Establish coordinate encoding
        srs.ImportFromEPSG(4326)  # Specify WGS84 lat/long
        output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system to the file
        output_raster.GetRasterBand(1).WriteArray(DD_aircraft_output)  # Writes my array to the raster
        output_raster = None

        # Export 2D MCB matrix as map
        output_raster = gdal.GetDriverByName('GTiff').Create(
            'MCB_aircraft_map_' + self.parameters['simulation'] + '.tif', ncols, nrows, 1, gdal.GDT_Float32)
        output_raster.SetGeoTransform(geotransform)  # Specify file coordinates
        srs = osr.SpatialReference()  # Establish coordinate encoding
        srs.ImportFromEPSG(4326)  # Specify WGS84 lat/long
        output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system to the file
        output_raster.GetRasterBand(1).WriteArray(MCB_aircraft_output)  # Writes my array to the raster
        output_raster = None

        return

    def site_reports(self):
        """
        Writes site-level deployment days (DDs) and maximum condition blackouts (MCBs) for each site.
        """

        #print('Generating site-level reports for aircraft company...')

        for site in self.state['sites']:
            site['aircraft_prop_DDs'] = self.DD_aircraft_map[site['lon_index'], site['lat_index']]
            site['aircraft_MCB'] = self.MCB_aircraft_map[site['lon_index'], site['lat_index']]

        return
