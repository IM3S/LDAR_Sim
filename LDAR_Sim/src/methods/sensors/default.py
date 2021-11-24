# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        methods.sensor.default
# Purpose:     Detect emissions with a single value MDL threshold.
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

# You should have received a copy of the MIT License
# along with this program.  If not, see <https://opensource.org/licenses/MIT>.
#
# ------------------------------------------------------------------------------
from method_functions import measured_rate
from utils.attribution import update_tag


def detect_emissions(self, site, covered_leaks, covered_equipment_rates, covered_site_rate,
                     site_rate, venting, equipment_rates):

    equip_measured_rates = []
    site_measured_rate = 0
    found_leak = False

    if self.config["measurement_scale"] == "site":
        if (covered_site_rate > self.config['sensor']['MDL'][0]):
            found_leak = True
            site_measured_rate = measured_rate(covered_site_rate, self.config['sensor']['QE'])
        else:
            site[self.config['label'] + '_missed_leaks'] += 1
    elif self.config["measurement_scale"] == "equipment":
        for rate in covered_equipment_rates:
            m_rate = measured_rate(rate, self.config['sensor']['QE'])
            if (m_rate > self.config['sensor']['MDL'][0]):
                found_leak = True
            else:
                site[self.config['label'] + '_missed_leaks'] += 1
                m_rate = 0
            equip_measured_rates.append(m_rate)
            site_measured_rate += m_rate

    elif self.config["measurement_scale"] == "component":
        # If measurement scale is a leak, all leaks will be tagged
        for leak in covered_leaks:
            if (leak['rate'] > self.config['sensor']['MDL'][0]):
                found_leak = True
                is_new_leak = update_tag(leak, site, self.timeseries, self.state['t'],
                                         self.state['campaigns'], self.config['label'], self.id)
                # Add these leaks to the 'tag pool'
                if is_new_leak:
                    site_measured_rate += measured_rate(leak['rate'], self.config['sensor']['QE'])
            else:
                site[self.config['label'] + '_missed_leaks'] += 1

    # Put all necessary information in a dictionary to be assessed at end of day
    site_dict = {
        'site': site,
        'leaks_present': covered_leaks,
        'site_true_rate': site_rate,
        'site_measured_rate': site_measured_rate,
        'equip_measured_rates': equip_measured_rates,
        'vent_rate': venting,
        'found_leak': found_leak,
    }
    return site_dict
