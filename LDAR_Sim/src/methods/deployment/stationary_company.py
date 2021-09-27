# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        methods.deployment.stationary_company
# Purpose:     Stationary_company company specific deployment classes and
#              methods (ie. Scheduling)
#
# Copyright (C) 2018-2021  Thomas Fox, Mozhou Gao, Thomas Barchyn, Chris Hugenholtz
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
    m_name = config['label']
    for sidx, site in state['sites'].items():
        if config['measurement_scale'] == "equipment":  # This may change in the future
            # n_fixed = int(site['fixed_sensors'])
            pass
        else:
            pass
            # n_fixed = int(site['fixed_sensors'])
        # HBD right now this can only handle one crew per site
        n_fixed = 1
        for i in range(n_fixed):
            crew_ID = sidx + '-' + str(i + 1)
            # Will only accept the first crew assigned to site
            if not site['crew_ID']:
                # assign agents
                site.update({'crew_ID': crew_ID})
            crews.append(
                BaseCrew(
                    state,
                    parameters,
                    config,
                    timeseries,
                    deployment_days,
                    id=crew_ID,
                    site=site
                ))
            timeseries['{}_cost'.format(m_name)][state['t'].current_timestep] += \
                config['cost']['upfront']


class Schedule(BaseSchedCompany):
    # --- inherited methods ---
    # base.company ->  get_deployment_dates()
    # base.company ->  can_deploy_today()

    def __init__(self, config, parameters, state):
        self.parameters = parameters
        self.config = config
        self.state = state

    def assign_agents(self):
        """ assign agents to sites.
            Stationary agents are assigned in make crew function

        --- Required in module.company.BaseCompany ---
        """
        pass

    def get_due_sites(self, site_pool):
        """ Retrieve a site list of sites due for screen / survey.
            Stationary companies
        Args:
            site_pool (dict): List of sites
        Returns:
            site_pool (dict): List of sites ready for survey.

        --- Required in module.company.BaseCompany ---
        """
        return site_pool

    def get_crew_site_list(self, site_pool, crew_idx, n_crews, crews=None):
        """ Allocates site pool among all crews. Ordering of sites is not
            changed by function. Stationary sites return only sites that
            have are assigned the crew id.
        Args:
            site_pool (dict): List of sites
            crew_num (int): Integer index of crew
            n_crews (int): Number of crews

        Returns:
            dict: Crew site list (subset of site_pool)

        --- Required in module.company.BaseCompany ---
        """
        return [crews[crew_idx].site]
