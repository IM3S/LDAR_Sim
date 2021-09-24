# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim)
# File:        geography.vector
# Purpose:     Various vector operations
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

import pandas as pd
import numpy as np
from geography.homebase import find_homebase
import matplotlib.pyplot as plt
import matplotlib.animation as animation


def build_crew_trajectories(fp, schedule):
    """ create a dataframe to make sure all crews have same amount of trajectories

    Args:
        fp (dataframe column from timeseries): record footprint (latitude and longitude) of crew 
        schedule (dictionary):a list that includes if the program activated the route planning,
                              home bases csv file, and initial locations of crews.  

    Returns:
        trajectories (organized dataframe that has 5 columns): timestep - records timestep (days) of simulation
                                                'lat' and 'lon' - cooridnates of crews 
                                                'id' - id of crews 
                                                'type' - 0 for screening and 1 for follow .
    """
    # check scheduling
    if schedule['route_planning']:
        HB = schedule['homebase']
        homebases = list(zip(HB['lon'], HB['lat']))
        init_lon = schedule['init_loc'][0]
        init_lat = schedule['init_loc'][1]
    else:
        # if initial locations is not defined
        # use coordinates of Calgary as the initial location
        init_lon = -114.052338
        init_lat = 51.006476

    # Extract crew's footprint from timeseries
    movement = {
        'timestep': [],
        'lon': [],
        'lat': [],
        'id': [],
        'type': []
    }
    i = 0
    for e in fp:
        if len(e) != 0:
            for s in e:
                movement['timestep'].append(i)
                movement['lon'].append(s[0])
                movement['lat'].append(s[1])
                movement['id'].append(s[2])
                movement['type'].append(s[3])
        else:
            movement['timestep'].append(i)
            movement['lon'].append(0)
            movement['lat'].append(0)
            movement['id'].append(1)
            movement['type'].append(0)
        i += 1

    df = pd.DataFrame(movement)

    # Count screening crew and follow up crew
    screen = df[df.type == 0]
    n_line_screen = len(screen.id.unique())
    followup = df[df.type == 1]
    n_line_followup = len(followup.id.unique())
    # number of crew equals the number of dependent trajectory
    N_line = n_line_screen + n_line_followup

    Last_coors = []
    for n in range(N_line):
        Last_coors.append([init_lon, init_lat])

    # create a temporary dictionary to store coordinates
    adjust_move = {
        'timestep': [],
        'lon': [],
        'lat': [],
        'id': [],
        'type': [],
    }

    Timestep = df.timestep.unique()
    # for each time step
    for t in Timestep:
        stepdf = df[df.timestep == t]
        # determine the maximum updates of coordinates per day
        # find the crew who moves most today
        Num_moves = 0
        # count number of moves for screening crews per timestep
        if n_line_screen > 0:
            s_screen_df = stepdf[stepdf.type == 0]
            for n in range(n_line_screen):
                s_crew = s_screen_df[s_screen_df.id == n+1]
                if len(s_crew) > Num_moves:
                    Num_moves = len(s_crew)
        # count number of moves for follow-up crews per timestep
        if n_line_followup > 0:
            s_followup_df = stepdf[stepdf.type == 1]
            for n in range(n_line_followup):
                f_crew = s_followup_df[s_followup_df.id == n+1]
                if len(f_crew) > Num_moves:
                    Num_moves = len(f_crew)

        # If the number of moves per day is 1, then append last locations
        if Num_moves == 1:
            if n_line_screen > 0:
                for n in range(n_line_screen):
                    adjust_move['timestep'].append(t)
                    adjust_move['lon'].append(Last_coors[n][0])
                    adjust_move['lat'].append(Last_coors[n][1])
                    adjust_move['id'].append(n+1)
                    adjust_move['type'].append(0)
            if n_line_followup > 0:
                for n in range(n_line_followup):
                    adjust_move['timestep'].append(t)
                    adjust_move['lon'].append(Last_coors[n+n_line_screen][0])
                    adjust_move['lat'].append(Last_coors[n+n_line_screen][1])
                    adjust_move['id'].append(n+1)
                    adjust_move['type'].append(1)

        else:
            # check for screening crew
            for n in range(n_line_screen):
                # extract time specific dataframe
                temp_df = s_screen_df[s_screen_df.id == n+1]
                length1 = len(temp_df)
                # if the crew doesn't move today, append the coordinate of last move
                if length1 == 0:
                    for c in range(Num_moves):
                        adjust_move['timestep'].append(t)
                        adjust_move['type'].append(0)
                        adjust_move['id'].append(n+1)
                        adjust_move['lon'].append(Last_coors[n][0])
                        adjust_move['lat'].append(Last_coors[n][1])
                # if crew moved today but not reach the maximum number of moves
                # append coordinates and update the last coordinates
                elif length1 < Num_moves:
                    for c in range(Num_moves):
                        adjust_move['timestep'].append(t)
                        adjust_move['type'].append(0)
                        adjust_move['id'].append(n+1)
                        if c == 0:
                            adjust_move['lon'].append(Last_coors[n][0])
                            adjust_move['lat'].append(Last_coors[n][1])
                        elif 0 < c < length1-1:
                            row = temp_df.iloc[c]
                            if row.lon == 0:
                                adjust_move['lon'].append(Last_coors[n][0])
                                adjust_move['lat'].append(Last_coors[n][1])
                            else:
                                adjust_move['lon'].append(row.lon)
                                adjust_move['lat'].append(row.lat)
                                Last_coors[n][0] = row.lon
                                Last_coors[n][1] = row.lat
                        elif c == length1-1:
                            # if route_planning is activated last coordiates of the day
                            # should be a homebase
                            if schedule['route_planning']:
                                homeloc, distance = find_homebase(
                                    Last_coors[n][0], Last_coors[n][1], homebases)
                                Last_coors[n][0] = homeloc[0]
                                Last_coors[n][1] = homeloc[1]
                            adjust_move['lon'].append(Last_coors[n][0])
                            adjust_move['lat'].append(Last_coors[n][1])
                        else:
                            adjust_move['lon'].append(Last_coors[n][0])
                            adjust_move['lat'].append(Last_coors[n][1])
                else:
                    # if crew moved most today, apppend coordinates
                    for index, row in temp_df.iterrows():
                        adjust_move['timestep'].append(row['timestep'])
                        adjust_move['type'].append(row['type'])
                        adjust_move['id'].append(row['id'])
                        if row['lon'] == 0:
                            adjust_move['lon'].append(Last_coors[n][0])
                            adjust_move['lat'].append(Last_coors[n][1])
                        else:
                            adjust_move['lon'].append(row.lon)
                            adjust_move['lat'].append(row.lat)
                            Last_coors[n][0] = row.lon
                            Last_coors[n][1] = row.lat
                    # add one more row to dataframe to record the locations of crew at homebase
                    adjust_move['timestep'].append(t)
                    adjust_move['type'].append(0)
                    adjust_move['id'].append(n+1)
                    if schedule['route_planning']:
                        homeloc, distance = find_homebase(
                            Last_coors[n][0], Last_coors[n][1], homebases)
                        Last_coors[n][0] = homeloc[0]
                        Last_coors[n][1] = homeloc[1]
                    adjust_move['lon'].append(Last_coors[n][0])
                    adjust_move['lat'].append(Last_coors[n][1])

            # Checking for follow up crews, same as above
            for n in range(n_line_followup):
                temp_df = s_followup_df[s_followup_df.id == n+1]
                length1 = len(temp_df)
                if length1 == 0:
                    for c in range(Num_moves):
                        adjust_move['timestep'].append(t)
                        adjust_move['type'].append(1)
                        adjust_move['id'].append(n+1)
                        adjust_move['lon'].append(
                            Last_coors[n+n_line_screen][0])
                        adjust_move['lat'].append(
                            Last_coors[n+n_line_screen][1])
                elif length1 < Num_moves:
                    for c in range(Num_moves):
                        adjust_move['timestep'].append(t)
                        adjust_move['type'].append(1)
                        adjust_move['id'].append(n+1)
                        if c == 0:
                            adjust_move['lon'].append(
                                Last_coors[n+n_line_screen][0])
                            adjust_move['lat'].append(
                                Last_coors[n+n_line_screen][1])
                        elif 0 < c < length1-1:
                            row = temp_df.iloc[c]
                            if row.lon == 0:
                                adjust_move['lon'].append(
                                    Last_coors[n+n_line_screen][0])
                                adjust_move['lat'].append(
                                    Last_coors[n+n_line_screen][1])
                            else:
                                adjust_move['lon'].append(row.lon)
                                adjust_move['lat'].append(row.lat)
                                Last_coors[n+n_line_screen][0] = row.lon
                                Last_coors[n+n_line_screen][1] = row.lat
                        elif c == length1-1:
                            if schedule['route_planning']:
                                homeloc, distance = find_homebase(
                                    Last_coors[n][0], Last_coors[n][1], homebases)
                                Last_coors[n+n_line_screen][0] = homeloc[0]
                                Last_coors[n+n_line_screen][1] = homeloc[1]
                            adjust_move['lon'].append(
                                Last_coors[n+n_line_screen][0])
                            adjust_move['lat'].append(
                                Last_coors[n+n_line_screen][1])
                        else:
                            adjust_move['lon'].append(
                                Last_coors[n+n_line_screen][0])
                            adjust_move['lat'].append(
                                Last_coors[n+n_line_screen][1])
                else:
                    n = 0
                    for index, row in temp_df.iterrows():
                        adjust_move['timestep'].append(row['timestep'])
                        adjust_move['type'].append(row['type'])
                        adjust_move['id'].append(row['id'])

                        if row['lon'] == 0:
                            adjust_move['lon'].append(
                                Last_coors[n+n_line_screen][0])
                            adjust_move['lat'].append(
                                Last_coors[n+n_line_screen][1])
                        else:
                            adjust_move['lon'].append(row.lon)
                            adjust_move['lat'].append(row.lat)
                            Last_coors[n+n_line_screen][0] = row.lon
                            Last_coors[n+n_line_screen][1] = row.lat
                    # add one more row to dataframe to record the locations of crew at homebase
                    adjust_move['timestep'].append(t)
                    adjust_move['type'].append(1)
                    adjust_move['id'].append(n+1)
                    if schedule['route_planning']:
                        homeloc, distance = find_homebase(
                            Last_coors[n][0], Last_coors[n][1], homebases)
                        Last_coors[n+n_line_screen][0] = homeloc[0]
                        Last_coors[n+n_line_screen][1] = homeloc[1]
                    adjust_move['lon'].append(Last_coors[n+n_line_screen][0])
                    adjust_move['lat'].append(Last_coors[n+n_line_screen][1])

    trajectories = pd.DataFrame(data=adjust_move)

    return trajectories


def map_trajectories(trajectories, schedule, Allsites):
    """ create an animation of trajectories

    Args:
        trajectories (dataframe): It records trjectories of crews 
        schedule (dictionary):a list that includes if the program activated the route planning,
                              home bases csv file, and initial locations of crews.  
        Allsites (dataframe): It includes coordinates of all sampled sites.

    Returns:
        ani: animation object
   
    """
    fig, ax = plt.subplots()
    # read site coordinates
    site_lons = list(Allsites.lon)
    site_lons = [float(i) for i in site_lons]
    site_lats = list(Allsites.lat)
    site_lats = [float(i) for i in site_lats]
    # plot site scatters
    Scatter = ax.plot(site_lons, site_lats, '+', markersize=2, label= 'Sites' )
    # check scheduling
    if schedule['route_planning']:
        HB = schedule['homebase']
        # read home bases coordinates
        home_lons = list(HB.lon)
        home_lats = list(HB.lat)
        # plot home bases scatters
        Scatter2 = ax.plot(home_lons, home_lats, 'o', markersize=2, label = 'Home bases')

        all_lons = site_lons + home_lons
        all_lats = site_lats + home_lats
    else: 
        all_lons = site_lons
        all_lats = site_lats

    # find the site coodinates limits
    llon = min(all_lons)
    ulon = max(all_lons)

    llat = min(all_lats)
    ulat = max(all_lats)
    # set limits 
    plt.xlim(llon - 0.2, ulon + 0.2)
    plt.ylim(llat - 0.2, ulat + 0.2)

    # Count screening crew and follow up crew
    screen = trajectories[trajectories.type == 0]
    n_line_screen = len(screen.id.unique())
    followup = trajectories[trajectories.type == 1]
    n_line_followup = len(followup.id.unique())
    # number of crew equals the number of dependent trajectory
    N_line = n_line_screen + n_line_followup

    Ani_lon = []
    Ani_lat = []
    X_data = []
    Y_data = []
    Line = []
    # Create line indicator (indicate the id of lines)
    n_screen = trajectories[trajectories.type == 0]
    Line_indicator = []
    for ns in n_screen.id.unique():
        crew_screen = n_screen[n_screen.id == ns]
        Ani_lon.append(np.array(crew_screen.lon))
        Ani_lat.append(np.array(crew_screen.lat))
        Line_indicator.append((0, ns))

    n_followup = trajectories[trajectories.type == 1]
    for nf in n_followup.id.unique():
        crew_follow = n_followup[n_followup.id == nf]
        Ani_lon.append(np.array(crew_follow.lon))
        Ani_lat.append(np.array(crew_follow.lat))
        Line_indicator.append((1, nf))
    # color pool 
    colors = ['blue', 'green', 'red', 'magenta', 'black', 'grey']
    # Create a line object, label for each crew 
    for n in range(N_line):
        X_data.append([])
        Y_data.append([])

        if Line_indicator[n][0] == 0:
            line = ax.plot(
                0, 0, label="Screening - Crew No.{}".format(int(Line_indicator[n][1])))
        else:
            line = ax.plot(0, 0, '--', color=np.random.choice(colors, 1)
                           [0], label="Followup - Crew No.{}".format(Line_indicator[n][1]))
        Line.append(line[0])
        ax.legend(loc='best')
        
    # get the timestep
    Days = np.array(crew_screen.timestep)
    #TL = n_screen[n_screen.id == 1]
    # frame is set to 365 for now 
    frame = range(365)

    def animation_func(i):

        for j in range(len(Line)):
            l = Line[j]
            lon = Ani_lon[j]
            lat = Ani_lat[j]
            x = X_data[j]
            y = Y_data[j]

            lo = lon[i]
            la = lat[i]
            if len(x) > 4:
                x.pop(0)
                y.pop(0)

            x.append(lo)
            y.append(la)

            l.set_xdata(x)
            l.set_ydata(y)

        ax.set_title("Day: {}".format(int(Days[i]+1)))
        return l

    # create animation, write animation, and output animation
    ani = animation.FuncAnimation(fig, animation_func, frames=frame, interval=50,
                                  blit=False,  save_count=100, repeat=False)

    return ani
