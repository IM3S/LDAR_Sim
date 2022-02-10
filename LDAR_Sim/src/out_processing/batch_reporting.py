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
import math
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotnine as pn
from mizani.formatters import date_format

warnings.simplefilter(action='ignore', category=FutureWarning)


class BatchReporting:

    def __init__(self, output_directory, start_date, ref_program, base_program):
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
        self.site_data = [[pd.read_csv(Path(f)) for f in os.scandir(fldr)
                          if f.is_file() and 'sites_output' in f.name]
                          for fldr in os.scandir(output_directory) if fldr.is_dir()]

        # Delete any empty lists (to enable additional folders, e.g. for sensitivity analysis)
        # Get vector of dates

        dates = pd.to_datetime(self.all_data[0][0].datetime)
        mask = (dates > start_date)
        self.dates_trunc = dates.loc[mask]

        # Figure out the number of sites used in the simulation
        # (have to do it this way because n can be sampled or not)
        self.n_sites = len(self.site_data[0][0])

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

        # ------- Build list of repaired leak dataframes ------- #
        self.repair_leak_dfs = [[] for i in range(len(self.all_data))]
        for i in range(len(self.all_data)):
            for j in self.all_data[i]:
                self.repair_leak_dfs[i].append(j["cum_repaired_leaks"])
            self.repair_leak_dfs[i] = pd.concat(self.repair_leak_dfs[i], axis=1,
                                                keys=[i for i in range(len(self.all_data[i]))])

            # New columns
            self.repair_leak_dfs[i]['program'] = self.directories[i]

            # Add dates
        for i in range(len(self.repair_leak_dfs)):
            self.repair_leak_dfs[i] = pd.concat([self.repair_leak_dfs[i], dates], axis=1)

            # Axe spinup year
            self.repair_leak_dfs[i]['datetime'] = pd.to_datetime(
                self.repair_leak_dfs[i]['datetime'])
            mask = (self.repair_leak_dfs[i]['datetime'] > start_date)
            self.repair_leak_dfs[i] = self.repair_leak_dfs[i].loc[mask]

        # ------- Build list of cost dataframes ------- #
        self.cost_dfs = [[] for i in range(len(self.all_data))]
        for i in range(len(self.all_data)):
            for j in self.all_data[i]:
                self.cost_dfs[i].append(j["rolling_cost_estimate"])
            self.cost_dfs[i] = pd.concat(self.cost_dfs[i], axis=1, keys=[
                                         i for i in range(len(self.all_data[i]))])
            self.cost_dfs[i] = self.cost_dfs[i]

            # New columns
            self.cost_dfs[i]['program'] = self.directories[i]

        # Add dates
        for i in range(len(self.cost_dfs)):
            self.cost_dfs[i] = pd.concat([self.cost_dfs[i], dates], axis=1)

            # Axe spinup
            self.cost_dfs[i]['datetime'] = pd.to_datetime(self.cost_dfs[i]['datetime'])
            mask = (self.cost_dfs[i]['datetime'] > start_date)
            self.cost_dfs[i] = self.cost_dfs[i].loc[mask]

        return

    def program_report(self):
        '''
        Output a spreadsheet for each program with descriptive statistics.
        '''
        for i in range(len(self.active_leak_dfs)):
            data = [
                {'mean': self.active_leak_dfs[i].describe().loc['50%'].mean(),
                 'median': self.active_leak_dfs[i].describe().loc['50%'].median(),
                 'std': self.active_leak_dfs[i].describe().loc['50%'].std(),
                 'min': self.active_leak_dfs[i].describe().loc['50%'].min(),
                 'max': self.active_leak_dfs[i].describe().loc['50%'].max()},
                {'mean': self.emission_dfs[i].describe().loc['50%'].mean(),
                 'median': self.emission_dfs[i].describe().loc['50%'].median(),
                 'std': self.emission_dfs[i].describe().loc['50%'].std(),
                 'min': self.emission_dfs[i].describe().loc['50%'].min(),
                 'max': self.emission_dfs[i].describe().loc['50%'].max()},
                {'mean': self.repair_leak_dfs[i].describe().loc['50%'].mean(),
                 'median': self.repair_leak_dfs[i].describe().loc['50%'].median(),
                 'std': self.repair_leak_dfs[i].describe().loc['50%'].std(),
                 'min': self.repair_leak_dfs[i].describe().loc['50%'].min(),
                 'max': self.repair_leak_dfs[i].describe().loc['50%'].max()}
            ]
            output_df = pd.DataFrame(data)
            output_df.rename(
                index={0: 'median active leaks',
                       1: 'median daily emissions',
                       2: 'cumulative repaired leaks'},
                inplace=True)
            output_df.to_csv(
                self.output_directory / '{}_descriptives.csv'.format(
                    self.active_leak_dfs[i]['program'].iloc[0]), index=True)

        return

    def batch_report(self):
        '''
        Output a spreadsheet comparing programs.
        '''
        # Read in all the descriptive files
        descriptive_files = {}
        for i in os.listdir():
            if i.endswith('_descriptives.csv'):
                descriptive_files[i[:-17]] = pd.read_csv(i, index_col=0)

        # Separate the reference program and the programs to compare to it
        ref = None
        alts = {}
        for i in descriptive_files:
            if i == self.ref_program:
                ref = descriptive_files[i]
            else:
                alts[i] = descriptive_files[i]

        output_df = pd.DataFrame()

        for i in alts:
            dif = alts[i] - ref
            dif['alt program'] = i
            dif['reference'] = self.ref_program
            dif['comparison'] = 'difference (alt-ref)'

            rat = alts[i] / ref
            rat['alt program'] = i
            rat['reference'] = self.ref_program
            rat['comparison'] = 'ratio (alt/ref)'

            output_df = output_df.append([dif, rat])

        output_df.to_csv(self.output_directory / 'program_comparisons.csv', index=True)

        return

    def batch_plots(self):

        # First, put together active leak data and output for live plotting functionality
        # (no AL plot here currently)
        dfs = self.active_leak_dfs

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
        df_p1.to_csv(self.output_directory / 'mean_active_leaks.csv', index=True)

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
                 pn.geom_line(df_p1, pn.aes(
                     'datetime', 'value', group='var_prog', colour='program'), size=0.1) +
                 pn.geom_line(df_p1, pn.aes('datetime', 'mean', colour='program'), size=1) +
                 pn.ylab('Daily emissions (kg/site)') + pn.xlab('') +
                 pn.scale_colour_hue(h=0.15, l=0.25, s=0.9) +
                 pn.scale_x_datetime(labels=date_format('%Y')) +
                 pn.scale_y_continuous() +
                 pn.aes(ymin=0) +
                 pn.labs(color='Program', fill='Program') +
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

        boxplot = (pn.ggplot(None) + pn.aes('program', 'mean') +
                   pn.geom_boxplot(df_p1, pn.aes('program', 'mean', fill='program')) +
                   pn.ylab('Daily Emissions (kg/site)') +
                   pn.scale_fill_hue(h=0.15, l=0.25, s=0.9) +
                   pn.labs(color='program', fill='program') +
                   pn.theme(panel_border=pn.element_rect(colour="black", fill=None, size=2),
                            panel_grid_minor_x=pn.element_blank(),
                            panel_grid_major_x=pn.element_blank(),
                            panel_grid_minor_y=pn.element_line(
                       colour='black', linewidth=0.5, alpha=0.3),
            panel_grid_major_y=pn.element_line(
                       colour='black', linewidth=1, alpha=0.5))
                   )
        boxplot.save(self.output_directory / 'emissions_boxplot.png', dpi=900, verbose=False)

        # ---------------------------------------
        # ------ Figure to compare costs  ------
        dfs = self.cost_dfs

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
        df_p1.to_csv(self.output_directory / 'cost_estimate_temporal.csv', index=True)

        # Make plots from list of dataframes - one entry per dataframe
        pn.theme_set(pn.theme_linedraw())
        plot1 = (pn.ggplot(None) + pn.aes('datetime', 'value', group='program') +
                 pn.geom_ribbon(df_p1, pn.aes(ymin='low', ymax='high', fill='program'), alpha=0.2) +
                 pn.geom_line(df_p1, pn.aes('datetime', 'mean', colour='program'), size=1) +
                 pn.ylab('Estimated cost per facility') + pn.xlab('') +
                 pn.scale_colour_hue(h=0.15, l=0.25, s=0.9) +
                 pn.scale_x_datetime(labels=date_format('%Y')) +
                 # pn.scale_y_continuous(trans='log10') +
                 pn.labs(color='Program', fill='Program') +
                 pn.theme(panel_border=pn.element_rect(colour="black", fill=None, size=2),
                          panel_grid_minor_x=pn.element_blank(),
                          panel_grid_major_x=pn.element_blank(),
                          panel_grid_minor_y=pn.element_line(
                              colour='black', linewidth=0.5, alpha=0.3),
                          panel_grid_major_y=pn.element_line(
                              colour='black', linewidth=1, alpha=0.5))
                 )
        plot1.save(self.output_directory / 'cost_estimate_temporal.png',
                   width=7, height=3, dpi=900, verbose=False)

        ########################################
        # Cost breakdown by program and method
        method_lists = []
        for i in range(len(self.directories)):
            df = pd.read_csv(
                self.output_directory / self.directories[i] / "timeseries_output_0.csv")
            df = df.filter(regex='cost$', axis=1)
            df = df.drop(columns=["total_daily_cost"])
            method_lists.append(list(df))

        costs = [[] for i in range(len(self.all_data))]
        for i in range(len(self.all_data)):
            for j in range(len(self.all_data[i])):
                simcosts = []
                for k in range(len(method_lists[i])):
                    timesteps = len(self.all_data[i][j][method_lists[i][k]])
                    simcosts.append(
                        (sum(self.all_data[i][j][method_lists[i][k]])/timesteps/self.n_sites)*365)
                costs[i].append(simcosts)

        rows_list = []
        for i in range(len(costs)):
            df_temp = pd.DataFrame(costs[i])
            for j in range(len(df_temp.columns)):
                dict = {}
                dict.update({'Program': self.directories[i]})
                dict.update({'Mean Cost': round(df_temp.iloc[:, j].mean())})
                dict.update({'St. Dev.': df_temp.iloc[:, j].std()})
                dict.update({'Method': method_lists[i][j].replace('_cost', '')})
                rows_list.append(dict)
        df = pd.DataFrame(rows_list)

        # Output Emissions df for other uses
        df.to_csv(self.output_directory / 'cost_comparison.csv', index=True)

        plot = (
            pn.ggplot(
                df, pn.aes(
                    x='Program', y='Mean Cost', fill='Method', label='Mean Cost')) +
            pn.geom_bar(stat="identity") + pn.ylab('Cost per Site per Year') + pn.xlab('Program') +
            pn.scale_fill_hue(h=0.15, l=0.25, s=0.9) +
            # pn.geom_text(size=15, position=pn.position_stack(vjust=0.5)) +
            pn.theme(
                panel_border=pn.element_rect(colour="black", fill=None, size=2),
                panel_grid_minor_x=pn.element_blank(),
                panel_grid_major_x=pn.element_blank(),
                panel_grid_minor_y=pn.element_line(
                    colour='black', linewidth=0.5, alpha=0.3),
                panel_grid_major_y=pn.element_line(
                    colour='black', linewidth=1, alpha=0.5)))
        plot.save(self.output_directory / 'cost_comparison.png',
                  width=7, height=3, dpi=900, verbose=False)

        return
