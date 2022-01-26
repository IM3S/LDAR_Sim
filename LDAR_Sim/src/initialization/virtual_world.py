from datetime import datetime
from copy import deepcopy
from pandas import read_csv
from math import floor
from numpy import asarray, abs, reshape, roll, zeros
from utils.distributions import fit_dist
from initialization.leaks import gen_initial_leaks, gen_leak_timeseries
import json
from datetime import (datetime as dt,
                      timedelta as tdelt)
from netCDF4 import Dataset
import pytz
from timezonefinder import TimezoneFinder


def gen_facil_type_emis_profiles(sim_params, in_dir):
    vw_params = sim_params['virtual_world']
    params_emis_cols = list(vw_params['emissions'].keys())

    # --- Load Facility types ---
    if vw_params['infrastructure']['facility_type_file']:
        ft_file = vw_params['infrastructure']['facility_type_file']
        facility_types_pd = read_csv(in_dir / ft_file, index_col='type_code')
        facility_types_pd.index = facility_types_pd.index.astype(dtype='string')
        facility_types = facility_types_pd.to_dict('index')
        facility_types_emis = {}
        for facil_type in facility_types:
            facility_types_emis.update({facil_type: {}})
            for col in params_emis_cols:
                col_type = type(vw_params['emissions'][col])
                if col not in facility_types[facil_type]:
                    facility_types_emis[facil_type][col] = vw_params['emissions'][col]
                elif not isinstance(facility_types[facil_type][col], col_type):
                    facility_types_emis[facil_type][col] = json.loads(
                        facility_types[facil_type][col].replace("'", '"'))
                else:
                    facility_types_emis[facil_type][col] = facility_types[facil_type][col]

    else:
        facility_types_emis = {'not_assigned': deepcopy(vw_params['emissions'])}

    # --- Iterate through facility types, generate emissions distributions and/or empirical leaks
    for fac_type in facility_types_emis:
        type_params = facility_types_emis[fac_type]
        # If leak file leaks are from a file
        if type_params['leak_file']:
            type_params['empirical_leaks'] = list(read_csv(
                in_dir / type_params['leak_file']).iloc[:, 0])
            if type_params['leak_file_use'] == 'fit':
                type_params['leak_dist'] = fit_dist(
                    samples=type_params['empirical_leaks'],
                    dist_type=type_params['leak_dist_type'])
            else:
                type_params['leak_dist'] = None
        else:
            type_params['leak_dist'] = fit_dist(
                dist_params=type_params['leak_dist_params'],
                dist_type=type_params['leak_dist_type'])
            type_params['empirical_leaks'] = None
    return facility_types_emis, params_emis_cols + ['empirical_leaks', 'leak_dist']


def find_nearest(value, array):
    array = asarray(array)
    return (abs(array - value)).argmin()


def get_UTC_offset(location):
    '''
    get UTC offset based on average site lat longs

    Uses current (now()) offset
    '''
    timezone_str = TimezoneFinder().timezone_at(lng=location[1], lat=location[0])
    # This uses the current time to estimate offset, so if running
    # software during DST, the the offset will include DST. Fix this
    # someday, by keeping timezone as a site variable and localizing
    # very year.
    tz_now = datetime.now(pytz.timezone(timezone_str))
    return tz_now.utcoffset().total_seconds()/60/60


def prepare_weather(weather_data, UTC_offset):
    ignore_cols = ['time', 'latitude', 'longitude']
    weather_cols = [key for key in weather_data.variables.keys()
                    if key not in ignore_cols]
    start_date = dt(1900, 1, 1) + tdelt(hours=int(weather_data['time'][:][0]))
    end_date = dt(1900, 1, 1) + tdelt(hours=int(weather_data['time'][:][-1]))
    num_days = (end_date - start_date).days
    num_years = int(floor(num_days/365))  # Remove Leap Days
    num_days = 365*num_years,  # Remove Leap Days
    num_hours = num_years*365*24

    weather_out = {
        'start_date': start_date,
        'UTC_ofset': UTC_offset,
        'num_days': num_days,
        'weather_cols': weather_cols,
        'latitude': weather_data.variables['latitude'][:],
        'longitude': weather_data.variables['longitude'][:],
    }
    for var in weather_cols:
        tmp = zeros(shape=(
            len(weather_data['latitude']), len(weather_data['longitude']),
            365*num_years, 24
        ))
        for lat_idx, _ in enumerate(weather_data['latitude']):
            for lon_idx, _ in enumerate(weather_data['longitude']):
                hrly = roll(weather_data[var][0: num_hours, lat_idx, lon_idx], -int(UTC_offset))
                if var == "t2m":
                    hrly = hrly - 273.15
                tmp[lat_idx, lon_idx] = reshape(hrly, (365*num_years, 24))
        weather_out[var] = tmp
    return weather_out


def get_weather_idx(site, weather_data):
    lat_idx = (abs(weather_data['latitude']-site['lat'])).argmin()
    lon_idx = (abs(weather_data['longitude']-site['lon'])).argmin()
    return [lat_idx, lon_idx]


def gen_world(sim_params, in_dir):
    print('Generating sites', end='...')
    # --- Initialize variables --
    vw_params = sim_params['virtual_world']
    start_date = datetime(*sim_params['start_date'])
    end_date = datetime(*sim_params['end_date'])
    n_days = (end_date - start_date).days
    n_samples = vw_params['infrastructure']['facility_samples']

    print('[done]')

    # --- Load Facilites ---
    print('Loading Facilities', end='...')
    sim_facilites = read_csv(in_dir / vw_params['infrastructure']['facility_file'])
    sim_facilites['facility_ID'] = sim_facilites['facility_ID'].astype(dtype='string')
    sim_facilites['type_code'] = sim_facilites['type_code'].astype(dtype='string')
    sim_facilites['weather'] = None
    if n_samples is None:
        n_samples = len(sim_facilites)
    sim_facilites = sim_facilites.sample(n_samples)
    facil_geo_mid_point = [sim_facilites['lat'].mean(), sim_facilites['lon'].mean()]
    sim_facilites = sim_facilites.to_dict('records')
    print('[done]')

    # --- Get facility type emissions profiles ---
    print('Loading facility type parameters', end='...')
    facility_types_emis, fac_type_cols = gen_facil_type_emis_profiles(sim_params, in_dir)
    print('[done]')

    # --- Load Weather ---
    print('Loading Weather', end='...')
    if vw_params['weather_file'] is not None:
        weather_data = Dataset(in_dir / vw_params['weather_file'], 'r+')
        weather_data.set_auto_mask(False)
        weather_clean = prepare_weather(weather_data, get_UTC_offset(facil_geo_mid_point))
    print('[done]')

    # --- Adding weather to facilites ---
    print('Getting Weather At sites', end='...')
    if vw_params['weather_file'] is not None:
        for site in sim_facilites:
            site['weather_idx'] = get_weather_idx(site, weather_clean)
    print('[done]')

    # --- Load Facility Emissions profiles ---
    print('Assigning facility type parameters to facilities', end='...')
    for facil in sim_facilites:
        for col in fac_type_cols:
            if col not in sim_facilites:
                if 'type_code' in facil and facil['type_code'] in facility_types_emis:
                    facil[col] = facility_types_emis[facil['type_code']][col]
                else:
                    facil[col] = facility_types_emis['not_assigned'][col]
    print('[done]')

    # --- Load Facility leak timeseries ---
    # (Keep seperate from the loop above for future functionality)
    print('Generating leaks at site', end='...')
    for facil in sim_facilites:
        facil['leak_timeseries'] = []
        for _ in range(sim_params['n_simulations']):
            # Generate Leaks
            initial_leaks = gen_initial_leaks(facil, start_date)
            facil['leak_timeseries'].append(gen_leak_timeseries(
                facil, start_date, n_days, initial_leaks))
        facil.pop('leak_dist')  # Object does not transfer well to starmap
    print('[done]')

    return sim_facilites, weather_clean
