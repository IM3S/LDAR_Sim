def cost_mitigation(simulation_dfs, ref_program, base_program):
    total_emissions = [[df['program_name'], df['timeseries']['daily_emissions_kg'].sum()]
                       for df in simulation_dfs]
    total_daily_cost = [[df['program_name'], df['timeseries']['total_daily_cost'].sum()]
                        for df in simulation_dfs]

    # base_dfs = [df for df in simulation_dfs if df['program_name'] == base_program]
    # ref_dfs = [df for df in simulation_dfs if df['program_name'] == ref_program]

    for list in total_emissions:
        total = list[1][0].sum()
        sim_average = total / (len(total_emissions) / len(total_emissions[].unique()))
        print(sim_average)

        # total_emissions = ((total_emissions / 1000) * 28)  # covert to tonnes CO2e (GWP 28)

    #cost_mitigation_ratios = []
    # for row in total_daily_cost:
        #cost_mitigation_ratio = total_daily_cost / total_emissions
        # cost_mitigation_ratios.append(cost_mitigation_ratio)

    # print(cost_mitigation_ratios)
