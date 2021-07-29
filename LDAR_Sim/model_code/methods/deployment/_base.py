# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        methods.deployment._base
# Purpose:     Commonly used schedule class methods for crew and companies
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
from datetime import timedelta


class SchedCrew:
    """ Crew schedule base class. Can be inherited by crew deployments
    """

    def update_schedule(self, work_mins):
        """ Update current time and crew location

        Args:
            work_mins (float): time in minutes
        """
        self.state['t'].current_date += timedelta(minutes=int(work_mins))

    def get_work_hours(self):
        """ Get hours in day the crew is able to work
        """
        if self.config['consider_daylight']:
            daylight_hours = self.state['daylight'].get_daylight(
                self.state['t'].current_timestep)
            if daylight_hours <= self.config['max_workday']:
                self.work_hours = daylight_hours
            elif daylight_hours > self.config['max_workday']:
                self.work_hours = self.config['max_workday']
        elif not self.config['consider_daylight']:
            self.work_hours = self.config['max_workday']

        if self.work_hours < 24 and self.work_hours != 0:
            self.start_hour = (24 - self.work_hours) / 2
            self.end_hour = self.start_hour + self.work_hours
        else:
            print(
                'Unreasonable number of work hours specified for crew ' +
                str(self.crewstate['id']))

        self.allowed_end_time = self.state['t'].current_date.replace(
            hour=int(self.end_hour), minute=0, second=0)


class SchedCompany:
    """ Company schedule base class. Can be inherited by company deployments
    """

    def get_deployment_dates(self):
        """ Using input parameters get the range of years and months available
            for company/ crew deployment. If non are specified, set to the
            number of years within simulation and all months.
        """
        # if user does not specify deployment interval, set to all months/years
        if len(self.config['scheduling']['deployment_years']) > 0:
            self.deployment_years = self.config['scheduling']['deployment_years']
        else:
            self.deployment_years = list(
                range(self.state['t'].start_date.year, self.state['t'].end_date.year+1))

        if len(self.config['scheduling']['deployment_months']) > 0:
            self.deployment_months = self.config['scheduling']['deployment_months']
        else:
            self.deployment_months = list(range(1, 13))

    def in_deployment_period(self, date):
        """ If the current day is within the deployment month and years window
        Args:
            date (datetime): Current date

        Returns:
            Boolean: If date passed is in deployment month and year
        """
        return date.month in self.deployment_months and date.year in self.deployment_years