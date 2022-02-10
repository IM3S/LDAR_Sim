# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        Batch reporting
# Purpose:     Creates outputs across multiple programs and simulations
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

import datetime
import os
import warnings
from pathlib import Path
import pandas as pd
import plotnine as pn
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from mizani.formatters import date_format
from out_processing.clean_results import clean_sim_df

warnings.simplefilter(action='ignore', category=FutureWarning)

SMALL_SIZE = 8
MEDIUM_SIZE = 12
BIGGER_SIZE = 16
mpl.rcParams['font.family'] = 'Arial'
plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
plt.rcParams["figure.figsize"] = [8.00, 5.00]


def gen_active_leak_cnt(res, out_dir):
    prog_ts = clean_sim_df(res, 'timeseries', index='ts', params=[
        {'in': 'active_leaks', 'out': 'active_leaks', 'type': int},
        {'in': 'daily_emissions_kg', 'out': 'daily_emissions_kg', 'type': float},
    ], aggregate=True)

    xticks = np.arange(len(prog_ts['program_name']))
    fig, ax = plt.subplots(1, 2)
    ax[0].bar(xticks, prog_ts['active_leaks'],
              edgecolor='dimgray', color='cornflowerblue')
    ax[0].set_ylabel('Average active leaks per day')
    ax[0].yaxis.grid(True, which='major', alpha=0.6)
    # ax[0].set_xlabel('Program')
    ax[0].set_xticks(xticks)
    ax[0].set_xticklabels(prog_ts['program_name'], rotation=45, ha='right', rotation_mode='anchor')
    ax[1].bar(xticks, prog_ts['daily_emissions_kg'],
              edgecolor='dimgray', color='cornflowerblue')
    ax[1].set_ylabel('Average daily emissions (kg/day)')
    # ax[1].set_xlabel('Program')
    ax[1].set_xticks(xticks)
    ax[1].set_xticklabels(prog_ts['program_name'], rotation=45, ha='right', rotation_mode='anchor')
    ax[1].yaxis.grid(True, which='major', alpha=0.6)
    plt.tight_layout(w_pad=5)
    fig.savefig(out_dir / 'emis_leak_bar.png')   # save the figure to file
    plt.close(fig)    # close the figure window
    prog_ts.to_csv(out_dir / 'bar_data.csv')


class BatchReporting:

    def __init__(self, output_directory, start_date, ref_program, base_program, n_sites):
        """
        Prepare output csv files to glean summary statistics and plotting data.
        """
        self.output_directory = output_directory
        self.start_date = start_date
        self.ref_program = ref_program
        start_date = datetime.datetime(*start_date).strftime("%m-%d-%Y")

        self.directories = [f.name for f in os.scandir(output_directory) if f.is_dir()]

        # For each folder, build a dataframe combining all necessary files
        self.all_data = [[pd.read_csv(Path(f)) for f in os.scandir(fldr)
                          if f.is_file() and 'timeseries' in f.name]
                         for fldr in os.scandir(output_directory) if fldr.is_dir()]

        # Delete any empty lists (to enable additional folders, e.g. for sensitivity analysis)
        # Get vector of dates

        dates = pd.to_datetime(self.all_data[0][0].datetime)
        mask = (dates > start_date)
        self.dates_trunc = dates.loc[mask]

        # Figure out the number of sites used in the simulation
        # (have to do it this way because n can be sampled or not)
        self.n_sites = n_sites

        # ------- Build list of emissions dataframes ------ #
        self.emission_dfs = [[] for i in range(len(self.all_data))]
        for i in range(len(self.all_data)):
            for j in self.all_data[i]:
                self.emission_dfs[i].append(j["daily_emissions_kg"])
            self.emission_dfs[i] = pd.concat(self.emission_dfs[i],
                                             axis=1, keys=[i for i in range(len(self.all_data[i]))])
            self.emission_dfs[i] = self.emission_dfs[i] / self.n_sites

            # New columns
            self.emission_dfs[i]['program'] = self.directories[i]

        # Add dates
        for i in range(len(self.emission_dfs)):
            self.emission_dfs[i] = pd.concat([self.emission_dfs[i], dates], axis=1)

            # Axe spinup year
            self.emission_dfs[i]['datetime'] = pd.to_datetime(self.emission_dfs[i]['datetime'])
            mask = (self.emission_dfs[i]['datetime'] > start_date)
            self.emission_dfs[i] = self.emission_dfs[i].loc[mask]

        # ------- Build list of active leak dataframes ------- #
        self.active_leak_dfs = [[] for i in range(len(self.all_data))]
        for i in range(len(self.all_data)):
            for j in self.all_data[i]:
                self.active_leak_dfs[i].append(j["active_leaks"])
            self.active_leak_dfs[i] = pd.concat(self.active_leak_dfs[i], axis=1,
                                                keys=[i for i in range(len(self.all_data[i]))])

            # New columns
            self.active_leak_dfs[i]['program'] = self.directories[i]

        # Add dates
        for i in range(len(self.active_leak_dfs)):
            self.active_leak_dfs[i] = pd.concat([self.active_leak_dfs[i], dates], axis=1)

            # Axe spinup year
            self.active_leak_dfs[i]['datetime'] = pd.to_datetime(
                self.active_leak_dfs[i]['datetime'])
            mask = (self.active_leak_dfs[i]['datetime'] > start_date)
            self.active_leak_dfs[i] = self.active_leak_dfs[i].loc[mask]
        return

    def batch_plots(self, prog_colors, prog_linestyles):

        # Now repeat for emissions (which will actually be used for batch plotting)
        dfs = self.emission_dfs

        for i in range(len(dfs)):
            n_cols = dfs[i].shape[1]
            dfs[i]['mean'] = dfs[i].iloc[:, 0:n_cols].mean(axis=1)
            dfs[i]['std'] = dfs[i].iloc[:, 0:n_cols].std(axis=1)
            dfs[i]['low'] = dfs[i].iloc[:, 0:n_cols].quantile(0.025, axis=1)
            dfs[i]['high'] = dfs[i].iloc[:, 0:n_cols].quantile(0.975, axis=1)
            dfs[i]['program'] = self.directories[i]

            # Move reference program to the top of the list
        for i, df in enumerate(dfs):
            if df['program'].iloc[0] == self.ref_program:
                dfs.insert(0, dfs.pop(i))

        # Arrange dfs for plot 1
        dfs_p1 = dfs.copy()
        for i in range(len(dfs_p1)):
            # Reshape
            dfs_p1[i] = pd.melt(dfs_p1[i], id_vars=['datetime', 'mean',
                                                    'std', 'low', 'high', 'program'])

        # Combine dataframes into single dataframe for plotting
        df_p1 = dfs_p1[0]
        for i in dfs_p1[1:]:
            df_p1 = df_p1.append(i, ignore_index=True)

        # Output Emissions df for other uses (e.g. live plot)
        df_p1.to_csv(self.output_directory / 'mean_emissions.csv', index=True)

        df_p1["var_prog"] = df_p1['variable'].astype(str) + df_p1['program'].astype(str)

        # Make plots from list of dataframes - one entry per dataframe
        pn.theme_set(pn.theme_linedraw())
        plot1 = (pn.ggplot(None) +
                 pn.aes('datetime', 'value', group='program') +
                 #  pn.geom_line(df_p1, pn.aes(
                 #      'datetime', 'value', group='var_prog',
                 #      linetype='program', colour='program'), size=0.1) +
                 pn.geom_line(df_p1, pn.aes(
                     'datetime', 'mean', linetype='program', colour='program'), size=0.7) +
                 pn.ylab('Daily emissions (kg/site)') + pn.xlab('') +
                 pn.scale_color_manual(values=prog_colors) +
                 pn.scale_linetype_manual(values=prog_linestyles) +
                 pn.scale_x_datetime(labels=date_format('%Y')) +
                 pn.scale_y_continuous() +
                 pn.aes(ymin=0) +
                 pn.labs(color='Program', fill='Program', linetype='Program') +
                 pn.theme(panel_border=pn.element_rect(colour="black", fill=None, size=2),
                          panel_grid_minor_x=pn.element_blank(),
                          panel_grid_major_x=pn.element_blank(),
                          panel_grid_minor_y=pn.element_line(
                     colour='black', linewidth=0.3, alpha=0.3),
            panel_grid_major_y=pn.element_line(
                colour='black', linewidth=1, alpha=0.5))
        )
        plot1.save(self.output_directory / 'emissions_timeseries.png', width=7,
                   height=3, dpi=900, verbose=False)
        return
