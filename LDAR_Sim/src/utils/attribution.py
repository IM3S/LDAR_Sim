# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        utils.attribute_leaks
# Purpose:     When a leak is observed, Identify who 'found' a leak and if the leak is new
#
# Copyright (C) 2018-2021  Intelligent Methane Monitoring and Management System (IM3S) Group
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the MIT License as published
# by the Free Software Foundation, version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.

def update_tag(leak, site, timeseries, time_obj, campaigns, company, crew_id=1):
    """ Updates the tag on a leak. If a leak is not tagged
        This funciton will tag. If it is already tagged, the
        leak will be added as a redundant tag.

    Args:
        leak (leak obj): Leak object. See initialization.leaks for details
        site (dict): site object
        timeseries (timeseries obj): ie self.timeseries
        time_obj (current time obj): current time state. ie self.state['t']
        company (str): Company responsible for detecting leak
        crew_id (int, optional): [int]. Defaults to 1. crew responsible for detecting

    Returns:
        [bool]: Is the leak new?
    """
    if leak['tagged']:
        if company == 'natural':
            # natural can still repair a tagged leak
            leak['date_tagged'] = time_obj.current_date
            leak['tagged_by_company'] = company
        elif leak['tagged_by_company'] == company:
            timeseries['{}_redund_tags'.format(company)][
                time_obj.current_timestep] += 1
        return False

    elif not leak['tagged']:
        # Add these leaks to the 'tag pool'
        leak['tagged'] = True
        leak['date_tagged'] = time_obj.current_date
        leak['tagged_by_company'] = company
        leak['tagged_by_crew'] = crew_id
        campaign = campaigns[site['subtype_code']][company]
        campaign['n_tags'][campaign['current_campaign']-1] += 1
        # if initially flagged give credit to flagging company
        if site['currently_flagged'] and site['flagged_by'] is not None:
            leak['init_detect_by'] = site['flagged_by']
            leak['init_detect_date'] = site['date_flagged']
        else:
            leak['init_detect_by'] = company
            leak['init_detect_date'] = leak['date_tagged']
        # timeseries['{}_tags'.format(company)][time_obj.current_timestep] += 1
    return True


def update_flag(config, site, timeseries, time_obj, campaigns,  company, consider_venting):
    """ Updates the flag on a site. If a site is not flagged
        This funciton will flag. If it is already flagged, the
        site will be marked as either"
            redundant: if the site is already flagged
            redundant 2: if The site is not tagged by is not site has active tagged leaks
            flag w/o venting: Would the site have been flagged without venting
    Args:
        config (dict): Method parameters
        site (dict): Site output from screening survey
        timeseries (timeseries obj): ie self.timeseries
        time_obj (current time obj): current time state. ie self.state['t']
        company (str): Company responsible for detecting leak
        consider_venting (bool): is venting enabled in method?
    """
    site_obj = site['site']
    site_true_rate = site['site_measured_rate']
    venting = site['vent_rate']
    if site_obj['currently_flagged']:
        timeseries['{}_flags_redund1'.format(company)][time_obj.current_timestep] += 1
    else:
        # Flag the site for follow-up
        site_obj['currently_flagged'] = True
        site_obj['date_flagged'] = time_obj.current_date
        site_obj['flagged_by'] = company
        campaign = campaigns[site_obj['subtype_code']][company]
        campaign['n_flags'][campaign['current_campaign']-1] += 1
        timeseries['{}_eff_flags'.format(company)][time_obj.current_timestep] += 1

        # Check to see if the site has any leaks that are active and tagged
        site_leaks = len([lk for lk in site_obj['active_leaks'] if lk['tagged']])

        if site_leaks > 0:
            timeseries['{}_flags_redund2'.format(company)][time_obj.current_timestep] += 1

        # Would the site have been chosen without venting?
        if consider_venting:
            if (site_true_rate - venting) < config['follow_up']['thresh']:
                timeseries['{}_flag_wo_vent'.format(company)][time_obj.current_timestep] += 1
