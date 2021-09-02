from numpy.random import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def cost_mitigation(simulation_dfs, ref_program, base_program, output_directory):
    economics_outputs = [{'program_name': df['program_name'],
                          'total_program_emissions_kg': df['timeseries']['daily_emissions_kg'].sum(),
                          'sale_price_natgas': df['p_params']['economics']['sale_price_natgas'],
                          'GWP_CH4': df['p_params']['economics']['GWP_CH4'],
                          'carbon_price_tonnesCO2e': df['p_params']['economics']['carbon_price_tonnesCO2e'],
                          'social_cost_CH4_tonnes': df['p_params']['economics']['social_cost_CH4_tonnes'],
                          'total_program_cost': df['timeseries']['total_daily_cost'].sum()}
                         for df in simulation_dfs]
    economics_outputs_df = pd.DataFrame(economics_outputs)

    economics_df = economics_outputs_df.groupby(by='program_name').mean()

    economics_df['total_emissions_mcf'] = (((economics_df['total_program_emissions_kg']
                                             / 0.678) * 35.3147) / 1000)
    economics_df['simulation_avg_emissions_tonnesCO2e'] = ((economics_df
                                                            ['total_program_emissions_kg'] / 1000) * economics_df['GWP_CH4'])

    base_value = economics_df.loc['P_base', 'total_emissions_mcf']

    economics_df['difference_baseline_mcf'] = (economics_df['total_emissions_mcf'] - base_value)

    economics_df['value_gas_sold'] = (
        abs(economics_df['difference_baseline_mcf']) * economics_df['sale_price_natgas'])

    economics_df['difference_baseline_tonnesCO2e'] = (((((abs(economics_df
                                                              ['difference_baseline_mcf']) * 1000) / 35.3147) * 0.678) / 1000) * economics_df['GWP_CH4'])  # convert to tonnes CO2e
    economics_df['cost_mitigation_ratio'] = np.divide(economics_df['total_program_cost'],
                                                      economics_df['difference_baseline_tonnesCO2e'], out=np.zeros_like(
                                                          economics_df['total_program_cost']),
                                                      where=economics_df['difference_baseline_tonnesCO2e'] != 0)

    economics_df.reset_index(inplace=True)

    programs = economics_df['program_name']
    x = np.arange(len(programs))

    plt.xticks(x, programs)
    plt.scatter(x, economics_df['cost_mitigation_ratio'], marker='o',
                c=np.random.rand(len(x)), s=100),
    plt.axhline(y=economics_df['carbon_price_tonnesCO2e'][1],
                color="darkgreen", linestyle='dotted', label="Carbon Price"),
    plt.ylabel("$/tonne CO2e"),
    plt.xlabel("Program"),
    plt.title("Comparing LDAR Program Cost Mitigation Ratios"),
    plt.legend(),
    plt.savefig(output_directory / 'cost_mitigation_plot.png')

    n_sites = len(simulation_dfs[0]['sites'])
    timesteps = len(simulation_dfs[0]['timeseries'])

    df1 = pd.DataFrame(df['timeseries'].filter(regex='cost$', axis=1).sum()
                       for df in simulation_dfs)
    df1['program_name'] = [df['program_name'] for df in simulation_dfs]
    cost_df = df1.groupby(by='program_name').mean()
    cost_df.reset_index(inplace=True)
    cost_method_df = cost_df.drop(columns='total_daily_cost')
    cost_method_df['value_gas_sold'] = economics_df['value_gas_sold'] * -1

    def cost_site_year(x):
        return (((x / n_sites) / timesteps) * 365)

    for column in cost_method_df.columns:
        if column != 'program_name':
            cost_method_df[column] = cost_method_df[column].map(cost_site_year)

    cost_method_df['adjusted_program_cost'] = cost_method_df.sum(axis=1)

    second_column = cost_method_df.pop('verification_cost')
    cost_method_df.insert(1, 'verification_cost', second_column)
    cost_method_site_year = cost_method_df.set_index('program_name')

    cost_method_site_year.loc[:, 'verification_cost':'value_gas_sold'].plot.bar(stacked=True)
    plt.scatter(programs, cost_method_site_year['adjusted_program_cost'], marker='o',
                color='black', zorder=2,
                label='costs - gas sold')
    plt.xticks(rotation=0)
    plt.axhline(y=0, color="black", linestyle='solid')
    plt.ylabel("Cost/Benefit ($/site/year)")
    plt.xlabel("Program")
    plt.title("Cost and Benefits of LDAR Programs")
    plt.legend()
    plt.savefig(output_directory / 'cost_method_plot.png')

    economics_df.to_csv(output_directory / 'economics_outputs.csv', index=True)

    cost_method_site_year.to_csv(
        output_directory / 'annual_cost_method_site.csv', index=True)

    return economics_df
