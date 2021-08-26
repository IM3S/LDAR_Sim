import pandas as pd
import matplotlib.pyplot as plt


def cost_mitigation(simulation_dfs, ref_program, base_program):
    total_emissions = [[df['program_name'], df['timeseries']['daily_emissions_kg'].sum()]
                       for df in simulation_dfs]
    total_daily_cost = [[df['program_name'], df['timeseries']['total_daily_cost'].sum()]
                        for df in simulation_dfs]

    total_emissions_df = pd.DataFrame(total_emissions,
                                      columns=['program_name', 'total_emissions_kg'])

    avg_emissions_prg = total_emissions_df.groupby(by='program_name').mean()
    avg_emissions_df = pd.DataFrame(avg_emissions_prg)
    avg_emissions_df['total_emissions_mcf'] = (((avg_emissions_df['total_emissions_kg']
                                                 / 0.678) * 35.3147) / 1000)
    avg_emissions_df['simulation_avg_emissions_tonnesCO2e'] = ((avg_emissions_df
                                                                ['total_emissions_kg'] / 1000) * 28)

    total_cost_df = pd.DataFrame(total_daily_cost,
                                 columns=['program_name', 'total_program_cost'])

    avg_cost_prg = total_cost_df.groupby(by='program_name').mean()
    avg_cost_df = pd.DataFrame(avg_cost_prg)
    avg_cost_df = avg_cost_df.rename(
        columns={'total_daily_cost': 'simulation_avg_total_cost'})

    cost_mitigation_df = pd.merge(avg_emissions_df, avg_cost_df, on='program_name')
    base_value = cost_mitigation_df.loc['P_base', 'total_emissions_mcf']
    cost_mitigation_df['difference_baseline_mcf'] = (
        cost_mitigation_df['total_emissions_mcf'] - base_value)
    cost_mitigation_df['value_gas_sold'] = (
        abs(cost_mitigation_df['difference_baseline_mcf']) * 3.0)
    cost_mitigation_df['difference_baseline_tonnesCO2e'] = ((
        (((abs(cost_mitigation_df['difference_baseline_mcf']) * 1000) / 35.3147) * 0.678) / 1000) * 28)  # convert to tonnes CO2e
    cost_mitigation_df['cost_mitigation_ratio'] = cost_mitigation_df['total_program_cost'] / \
        cost_mitigation_df['difference_baseline_tonnesCO2e']

    print(cost_mitigation_df)

    return cost_mitigation_df

    # print(program, emissions)

    # for program, cost in total_daily_cost:
    # print(program, cost)

    # base_dfs = [df for df in simulation_dfs if df['program_name'] == base_program]
    # ref_dfs = [df for df in simulation_dfs if df['program_name'] == ref_program]

    # for program, emissions in total_emissions:

    # total_emissions = ((total_emissions / 1000) * 28)  # covert to tonnes CO2e (GWP 28)

    # cost_mitigation_ratios = []
    # for row in total_daily_cost:
    # cost_mitigation_ratio = total_daily_cost / total_emissions
    # cost_mitigation_ratios.append(cost_mitigation_ratio)

    # print(cost_mitigation_ratios)
