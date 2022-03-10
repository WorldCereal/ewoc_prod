#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Tuple
from osgeo import ogr

from ewoc_prod.utils import conversion_doy_to_date

def get_tiles_from_tile(tile_id: str)->List[str]:
    """
    Get s2 tiles list from tile chosen by user
    :param tile_id: tile id (e.g. '31TCJ' Toulouse)
    """
    tiles_id = []
    tiles_id.append(tile_id)
    return tiles_id

def get_tiles_from_aez(s2tiles_layer: str, aez_id: str)->List[str]:
    """
    Get s2 tiles list from aez chosen by user
    :param s2tiles_layer: MGRS grid that contains for each included tile
         the associated aez information
    :param aez_id: aez id (e.g. '46172')
    """
    tiles_id = []
    for tile in s2tiles_layer:
        if int(tile.GetField('zoneID')) == aez_id:
            tiles_id.append(tile.GetField('tile'))
    return tiles_id

def get_tiles_from_aoi(s2tiles_layer: str, aoi_geom: str)->List[str]:
    """
    Get s2 tiles list from aoi provided by user
    :param s2tiles_layer: MGRS grid that contains for each included tile
        the associated aez information
    :param aoi_geom: area of interest geometry
    """
    tiles_id = []
    s2tiles_layer.SetSpatialFilter(aoi_geom)
    for tile in s2tiles_layer:
        tiles_id.append(tile.GetField('tile'))
    s2tiles_layer.SetSpatialFilter(None)
    return tiles_id

def get_tiles_from_date(s2tiles_layer: str, prod_start_date: date)->List[str]:
    """
    Get s2 tiles list from date provided by user
    :param s2tiles_layer: MGRS grid that contains for each included tile
        the associated aez information
    :param prod_start_date: production start date
    """
    end_doy = prod_start_date.strftime("%j")
    tiles_id = []
    for tile in s2tiles_layer:
        if int(tile.GetField("wweos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
        elif int(tile.GetField("m1eos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
        elif int(tile.GetField("m2eos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
    return tiles_id

def extract_s2tiles_list(s2tiles_aez_file: str,
                        tile_id: str,
                        aez_id: str,
                        user_aoi: str,
                        prod_start_date: date)->List[str]:
    """
    Extraction of s2 tiles list from different input provided by user
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tile_id: tile id (e.g. '31TCJ' Toulouse)
    :param aez_id: aez id (e.g. '46172')
    :param user_aoi: area of interest (geojson file)
    :param prod_start_date: production start date
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Identify the tiles of interest from the info provided by the user
    if tile_id is not None:
        logging.info("Extract tile : %s", tile_id)
        tiles_id = get_tiles_from_tile(tile_id)
    elif aez_id is not None:
        logging.info("Extract tiles corresponding to the aez region id: %s", aez_id)
        tiles_id = get_tiles_from_aez(s2tiles_layer, aez_id)
    elif user_aoi is not None:
        logging.info("Extract tiles corresponding to the user aoi: %s", user_aoi)
        tiles_id = []
        driver = ogr.GetDriverByName('GeoJSON')
        data_source2 = driver.Open(user_aoi, 1)
        aoi_layer = data_source2.GetLayer()
        for aoi in aoi_layer:
            aoi_geom = aoi.GetGeometryRef()
            tiles_id_geom = get_tiles_from_aoi(s2tiles_layer, aoi_geom)
            tiles_id.extend(tiles_id_geom)
        logging.info("Number of tiles selected = %s", len(tiles_id))
    else:
        logging.info("Extract tiles corresponding to the production date requested: %s",
             prod_start_date)
        tiles_id = get_tiles_from_date(s2tiles_layer, prod_start_date)
    return tiles_id

def check_number_of_aez_for_selected_tiles(s2tiles_aez_file: str, tiles_id: str)->List[str]:
    """
    Check the number of aez corresponding to the s2 tiles selected
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tiles_id: list of s2 tiles selected
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    tiles_id_str = '(' + ','.join(f"'{tile_id}'" for tile_id in tiles_id) + ')'
    s2tiles_layer.SetAttributeFilter(f"tile IN {tiles_id_str}")
    #Get aez list
    aez_list = []
    for tile in s2tiles_layer:
        aez_list.append(tile.GetField('zoneID'))
    aez_list = list(set(aez_list))
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return aez_list

def extract_s2tiles_list_per_aez(s2tiles_aez_file: str, tiles_id: str, aez_id: str)->List[str]:
    """
    Extraction of s2 tiles list for each aez
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tiles_id: list of s2 tiles selected
    :param aez_id: aez id (e.g. '46172')
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    tiles_id_str = '(' + ','.join(f"'{tile_id}'" for tile_id in tiles_id) + ')'
    s2tiles_layer.SetAttributeFilter(f"tile IN {tiles_id_str}")
    #Get s2 tiles list
    tiles_id_subset = []
    for tile in s2tiles_layer:
        if int(tile.GetField('zoneID')) == int(aez_id):
            tiles_id_subset.append(tile.GetField('tile'))
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return tiles_id_subset

def get_aez_season_type_from_date(s2tiles_aez_file: str, aez_id: str, prod_start_date: date)->str:
    """
    Get the season type from date provided by user
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param aez_id: aez id (e.g. '46172')
    :param prod_start_date: production start date
    """
    end_doy = prod_start_date.strftime("%j")
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    s2tiles_layer.SetAttributeFilter(f"zoneID = {aez_id}")
    aez = s2tiles_layer.GetNextFeature()
    if int(aez.GetField("wweos_max")) == int(end_doy):
        season_type = "winter"
    elif int(aez.GetField("m1eos_max")) == int(end_doy):
        season_type = "summer1"
    elif int(aez.GetField("m2eos_max")) == int(end_doy):
        season_type = "summer2"
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return season_type

def get_aez_dates_from_season_type(season_type: str)->Tuple[str,str]:
    """
    Get the start/end dates for the aez
    :param season_type: season type (winter, summer1, summer2)
    """
    aez_start_date_key=None
    aez_end_date_key=None
    if season_type == "winter":
        aez_start_date_key = "wwsos_min"
        aez_end_date_key = "wweos_max"
    elif season_type == "summer1":
        aez_start_date_key = "m1sos_min"
        aez_end_date_key = "m1eos_max"
    elif season_type == "summer2":
        aez_start_date_key = "m2sos_min"
        aez_end_date_key = "m2eos_max"
    else:
        raise ValueError
    return aez_start_date_key, aez_end_date_key

def add_buffer_to_dates(season_type: str,
                        start_doy: int,
                        year: date = date.today().year)->Tuple[int,date]:
    """
    Add buffer before crop season
    :param season_type: season type (winter, summer1, summer2)
    :param start_doy: day of year corresponding to the crop emergence
    :param year: year of the crop emergence
    """
    season_buffer = {
    'winter': 15,
    'summer1': 15,
    'summer2': 15,
    }
    start_processing_doy = start_doy - season_buffer.get(season_type)
    year_processing_date = year
    #Manage specific case (e.g. : wwsos = 15 for AEZ 46172)
    if start_processing_doy == 0:
        start_date = conversion_doy_to_date(start_doy, year) - \
            relativedelta(days=season_buffer.get(season_type))
        start_processing_doy = start_date.strftime("%j")
        year_processing_date = year-1
    return start_processing_doy, year_processing_date

def get_detector_set_from_season_type(season_type: str,
                                    enable_sw: bool,
                                    tile: str)->Optional[List[str]]:
    """
    Get detector_set according to season_type
    :param season_type: season type (winter, summer1, summer2)
    :param enable_sw: if True, spring wheat map will be produced
    :param tile: first tile of the AEZ (all tiles have similar information)
    """
    if season_type == "winter":
        detector_set = ['winterwheat', 'irrigation']
    elif season_type == "summer1":
        detector_set = ['maize', 'irrigation']
        if int(tile.GetField("m2sos_min")) == int(tile.GetField("m2eos_max")) == 0:
            detector_set.extend(['cropland'])
        if enable_sw:
            detector_set.extend(['springwheat'])
    elif season_type == "summer2":
        detector_set = ['cropland', 'maize', 'irrigation']
    else:
        raise ValueError
    detector_set = ', '.join(detector_set)
    return detector_set

def get_tiles_infos_from_tiles(s2tiles_aez_file: str,
                                tiles_id: str,
                                season_type: str,
                                prod_start_date: date)-> \
                                    Tuple[date,date,date,date,date,date,date,date,bool,bool,str]:
    """
    Get some tiles informations (dates, l8_sr)
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tiles_id: list of s2 tiles selected
    :param season_type: season type (winter, summer1, summer2)
    :param prod_start_date: production start date
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    tiles_id_str = '(' + ','.join(f"'{tile_id}'" for tile_id in tiles_id) + ')'
    s2tiles_layer.SetAttributeFilter(f"tile IN {tiles_id_str}")
    tile = s2tiles_layer.GetNextFeature()
    #Get dates
    aez_start_date_key, aez_end_date_key = get_aez_dates_from_season_type(season_type)
    season_start_doy = int(tile.GetField(aez_start_date_key))
    season_end_doy = int(tile.GetField(aez_end_date_key))
    if season_start_doy == season_end_doy == 0:
        season_start = None
        season_end = None
        season_processing_start = None
        season_processing_end = None
        annual_processing_start = None
        annual_processing_end = None
    else:
        if season_start_doy > season_end_doy:
            year_start_date = prod_start_date.year - 1
        else:
            year_start_date = prod_start_date.year

        season_start = conversion_doy_to_date(season_start_doy, year_start_date)
        season_end = conversion_doy_to_date(season_end_doy, prod_start_date.year)
        season_processing_start_doy, year_processing_start_date = \
            add_buffer_to_dates(season_type, season_start_doy, year_start_date)
        season_processing_start = conversion_doy_to_date(season_processing_start_doy, \
            year_processing_start_date)
        season_processing_end = season_end
        annual_processing_start = season_end - relativedelta(years=1)
        annual_processing_end = season_end
    #Get L8 info
    if tile.GetField('L8')==0:
        l8_enable_sr = False
    elif tile.GetField('L8')==1:
        l8_enable_sr = True
    else:
        raise ValueError
    #Get spring wheat info
    if tile.GetField('trigger_sw')==0:
        enable_sw = False
    elif tile.GetField('trigger_sw')==1:
        enable_sw = True
    else:
        raise ValueError
    #Get detector_set
    detector_set = get_detector_set_from_season_type(season_type, enable_sw, tile)
    #Get wp_processing_dates
    if 'cropland' in detector_set:
        wp_processing_start = annual_processing_start
        wp_processing_end = annual_processing_end
    else:
        wp_processing_start = season_processing_start
        wp_processing_end = season_processing_end
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return season_start, season_end, season_processing_start, season_processing_end, \
        annual_processing_start, annual_processing_end, wp_processing_start, wp_processing_end,\
            l8_enable_sr, enable_sw, detector_set

def get_tiles_metaseason_infos_from_tiles(s2tiles_aez_file: str,
                                tiles_id: str,
                                year: int)-> \
                                    Tuple[str,str,str,str,str,str,str,date,date,bool,bool,str]:
    """
    Get some tiles informations for metaseason (dates, l8_sr)
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tiles_id: list of s2 tiles selected
    :param year: season to process (e.g. 2021 to process 2020/2021)
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    tiles_id_str = '(' + ','.join(f"'{tile_id}'" for tile_id in tiles_id) + ')'
    s2tiles_layer.SetAttributeFilter(f"tile IN {tiles_id_str}")
    tile = s2tiles_layer.GetNextFeature()
    #Get L8 info
    if tile.GetField('L8')==0:
        l8_enable_sr = False
    elif tile.GetField('L8')==1:
        l8_enable_sr = True
    else:
        raise ValueError
    #Get spring wheat info
    enable_sw = True
    #Get detector_set
    detector_set = 'None'
    #Get wp_processing_dates
    wp_processing_start, wp_processing_end, m2_exists = \
                retrieve_custom_dates(tile, year)
    #Get dates
    season_start = wp_processing_start
    season_end = wp_processing_end
    season_processing_start = wp_processing_start
    season_processing_end = wp_processing_end
    annual_processing_start = wp_processing_start
    annual_processing_end = wp_processing_end
    #Season type
    if m2_exists == 1:
        season_type = 'metaseason, winter, summer1, summer2'
    else:
        season_type = 'metaseason, winter, summer1'
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return season_type, season_start, season_end, season_processing_start, season_processing_end, \
        annual_processing_start, annual_processing_end, wp_processing_start, wp_processing_end,\
            l8_enable_sr, enable_sw, detector_set

def retrieve_custom_dates(tile: str, year: int)->List[str]:
    """
    Get custom dates that will encompass all the seasons
    :param tile: aez representative tile with the associated aez information
    :param year: season to process (e.g. 2021 to process 2020/2021)
    """
    #Get field names
    ww_start_date_key = "wwsos_min"
    ww_end_date_key = "wweos_max"
    m1_start_date_key = "m1sos_min"
    m1_end_date_key = "m1eos_max"
    m2_start_date_key = "m2sos_min"
    m2_end_date_key = "m2eos_max"
    #Get dates
    ww_start_doy = int(tile.GetField(ww_start_date_key))
    ww_end_doy = int(tile.GetField(ww_end_date_key))
    m1_start_doy = int(tile.GetField(m1_start_date_key))
    m1_end_doy = int(tile.GetField(m1_end_date_key))
    m2_start_doy = int(tile.GetField(m2_start_date_key))
    m2_end_doy = int(tile.GetField(m2_end_date_key))
    m2_exists = 1
    if m2_start_doy == m2_end_doy == 0:
        m2_exists = 0
    #Get crops end dates
    ww_end = conversion_doy_to_date(ww_end_doy, year)
    m1_end = conversion_doy_to_date(m1_end_doy, year)
    if m2_exists!=0:
        m2_end = conversion_doy_to_date(m2_end_doy, year)
    #Get custom dates
    if m2_exists!=0:
        wp_processing_end = max(ww_end, m1_end, m2_end)
        wp_processing_start = m2_end - relativedelta(years=1)
    else:
        wp_processing_end = max(ww_end, m1_end)
        wp_processing_start = m1_end - relativedelta(years=1)
    #Modify custom start date if it does not include all seasons
    if ww_start_doy > ww_end_doy:
        ww_year_start_date = year - 1
    else:
        ww_year_start_date = year
    ww_start_doy, ww_year_start_date = \
        add_buffer_to_dates('winter', ww_start_doy, ww_year_start_date)
    ww_start = conversion_doy_to_date(ww_start_doy, ww_year_start_date)
    if ww_start < wp_processing_start:
        wp_processing_start = ww_start
    if m1_start_doy > m1_end_doy:
        m1_year_start_date = year - 1
    else:
        m1_year_start_date = year
    m1_start_doy, m1_year_start_date = \
        add_buffer_to_dates('summer1', m1_start_doy, m1_year_start_date)
    m1_start = conversion_doy_to_date(m1_start_doy, m1_year_start_date)
    if m1_start < wp_processing_start:
        wp_processing_start = m1_start
    if m2_exists!=0:
        if m2_start_doy > m2_end_doy:
            m2_year_start_date = year - 1
        else:
            m2_year_start_date = year
        m2_start_doy, m2_year_start_date = \
            add_buffer_to_dates('summer2', m2_start_doy, m2_year_start_date)
        m2_start = conversion_doy_to_date(m2_start_doy, m2_year_start_date)
        if m2_start < wp_processing_start:
            wp_processing_start = m2_start
    return wp_processing_start, wp_processing_end, m2_exists
