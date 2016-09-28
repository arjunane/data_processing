import pandas as pd
from workalendar.europe import Germany
from datetime import time as settime
import time

from demandlib import bdew as bdew, particular_profiles as profiles
from data_processing.tools import io, metadata
from oemof.db import tools


def get_load_areas_table(schema, table, index_col, conn, columns=None):
    r"""Retrieve load areas intermediate results table from oedb
    """

    # retrieve table with processed input data
    load_areas = pd.read_sql_table(table, conn, schema=schema,
                                    index_col=index_col, columns=columns)

    return load_areas


def add_sectoral_peak_load(load_areas, **kwargs):
    r"""Add peak load per sector based on given annual consumption
    """

    # define data year
    # TODO: in the future get this from somewhere else
    year = 2013

    # call demandlib
    # TODO: change to use new demandlib
    tmp_peak_load = dm.electrical_demand(method='calculate_profile',
                                     year=year,
                                     ann_el_demand_per_sector= {
                                         'h0':
                                             load_areas['sector_consumption_residential'],
                                         'g0':
                                             load_areas['sector_consumption_retail'],
                                         'i0':
                                             load_areas['sector_consumption_industrial'],
                                        'l0':
                                            load_areas['sector_consumption_agricultural']}
                                     ).elec_demand
    # hack correct industrial profile into dataframe
    # print(load_areas['sector_consumption_industrial'])

    if load_areas['sector_consumption_industrial'] == 0:
        load_areas['sector_consumption_industrial'] = 0.1

    demand_industry = eb.IndustrialLoadProfile('simple_industrial_profile',
        **{'annual_demand': load_areas['sector_consumption_industrial'],
        'year': year,
        'am': settime(6, 0, 0),
        'pm': settime(22, 0, 0),
        'profile_factors':
            {'week': {'day': 0.8, 'night': 0.6},
            'weekend': {'day': 0.6, 'night': 0.6}}
        })
    ind_demand = demand_industry.profile
    tmp_peak_load['i0'] = ind_demand

    peak_load = tmp_peak_load.max(axis=0)

    return peak_load


if __name__ == '__main__':

    la_index_col = 'id'

    schema = 'calc_ego_loads'
    table = 'ego_deu_consumption'
    target_table = 'calc_ego_peak_load_test'
    year = 2013
    db_group = 'oeuser'

    cal = Germany()
    holidays = dict(cal.holidays(2010))

    # get database connection object
    conn = io.oedb_session(section='oedb')

    # retrieve load areas table
    columns = [la_index_col,
               'sector_consumption_residential',
               'sector_consumption_retail',
               'sector_consumption_industrial',
               'sector_consumption_agricultural']

    load_areas = get_load_areas_table(schema, table, la_index_col, conn,
                                      columns=columns)

    names_dc = {'sector_consumption_residential': 'h0',
                'sector_consumption_retail': 'g0',
                'sector_consumption_agricultural': 'l0',
                'sector_consumption_industrial': 'i0',}

    # rename columns to demandlib compatible names
    load_areas.rename(columns=names_dc, inplace=True)

    # iterate over substation retrieving sectoral demand at each of it
    for it, row in load_areas.iterrows():
        row = row.fillna(0)
        # read standard load profiles
        e_slp = bdew.ElecSlp(year, holidays=holidays)

        # multiply given annual demand with timeseries
        elec_demand = e_slp.get_profile(row.to_dict())

        # Add the slp for the industrial group
        ilp = profiles.IndustrialLoadProfile(e_slp.date_time_index,
                                             holidays=holidays)

        # Beginning and end of workday, weekdays and weekend days, and scaling factors
        # by default
        elec_demand['i0'] = ilp.simple_profile(
            row['i0'],
            am=settime(6, 0, 0),
            pm=settime(22, 0, 0),
            profile_factors=
            {'week': {'day': 0.8, 'night': 0.6},
             'weekend': {'day': 0.6, 'night': 0.6}})

        # Resample 15-minute values to hourly values and sum across sectors
        elec_demand = elec_demand.resample('H').mean().fillna(0).max().to_frame().T#.max(axis=0)#.to_frame().unstack()#.\
            # to_frame(name='peak_load')
        elec_demand['id'] = it
        elec_demand.set_index('id', inplace=True)

        # write results to new database table
        elec_demand.to_sql(target_table,
                             conn,
                             schema=schema,
                             index=True,
                             if_exists='append')

    # grant access to db_group
    tools.grant_db_access(conn, schema, target_table, db_group)

    # change owner of table to db_group
    tools.change_owner_to(conn, schema, target_table, db_group)

    # add primary key constraint on id column
    tools.add_primary_key(conn, schema, target_table, la_index_col)

    # create metadata json str
    json_str = metadata.create_metadata_json(
        'Peak load per load area',
        '',
        '2011',
        time.strftime("%d.%m.%Y"),
        'Open Energy Database, schema: {0}, table: {1}'.format(schema,
                                                               target_table),
        'Germany',
        'Sectoral peak of single load areas based on synthetic standard load ' +
        'profiles.',
        [{'Name': 'id',
          'Description': 'Unique identifier',
          'Unit': '-'},
         {'Name': 'g0',
          'Description': 'Peak demand of retail sector',
          'Unit': 'GW'},
         {'Name': 'h0',
          'Description': 'Peak demand of household sector',
          'Unit': 'GW'},
         {'Name': 'l0',
          'Description': 'Peak demand of agricultural sector',
          'Unit': 'GW'},
         {'Name': 'i0',
          'Description': 'Peak demand of industrial sector',
          'Unit': 'GW'}
         ],
        {'Name': 'Guido Pleßmann',
         'Mail': 'guido.plessmann@rl-institut.de',
         'Date': time.strftime("%d.%m.%Y"),
         'Comment': 'Initial creation of dataset'},
        'Be aware of applicability. Data bases on synthetic load profiles',
        '',
        ''
    )

    metadata.submit_comment(conn, json_str, schema, target_table)