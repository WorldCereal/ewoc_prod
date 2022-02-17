#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import argparse
import logging
import sys
from datetime import date, datetime
from typing import List, Tuple
from dateutil.relativedelta import relativedelta
from osgeo import ogr

from ewoc_work_plan.workplan import WorkPlan

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
        logging.info('Extract tile : %s', tile_id)
        tiles_id = get_tiles_from_tile(tile_id)
    elif aez_id is not None:
        logging.info('Extract tiles corresponding to the aez region id: %s', aez_id)
        tiles_id = get_tiles_from_aez(s2tiles_layer, aez_id)
    elif user_aoi is not None:
        logging.info('Extract tiles corresponding to the user aoi: %s', user_aoi)
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
        logging.info('Extract tiles corresponding to the production date requested: %s',
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

def conversion_doy_to_date(doy: int, year: date = date.today().year)->date:
    """
    Convert day of year to date YYYY-mm-dd
    :param doy: day of year
    :param year: year
    """
    year = str(year)
    str(doy).rjust(3 + len(str(doy)), '0')
    date_string = datetime.strptime(year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
    date_format = datetime.strptime(date_string, "%Y-%m-%d").date()
    return date_format

def get_tiles_infos_from_tiles(s2tiles_aez_file: str,
                                tiles_id: str,
                                season_type: str,
                                prod_start_date: date)-> \
                                    Tuple[date,date,date,date,date,date,bool,bool]:
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
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return season_start, season_end, season_processing_start, season_processing_end, \
        annual_processing_start, annual_processing_end, l8_enable_sr, enable_sw

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

def parse_date(date_str: str)->date:
    """
    Parse date string to datetime object
    """
    try:
        # With python 3.7 it could be replaced by
        # return date.isoformat(date_str)
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        msg = f"Not a valid date: '{date_str}'"
        raise argparse.ArgumentTypeError(msg)

def parse_args(args: List[str])->argparse.Namespace:
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-in',
                        "--s2tiles_aez_file",
                        help="MGRS grid that contains for each included tile \
                            the associated aez information (geojson file)")
    parser.add_argument('-pd', "--prod_start_date",
                        help="Production start date - format YYYY-MM-DD",
                        type=parse_date,
                        default=date.today())
    parser.add_argument('-t',"--tile_id",
                        help="Tile id for production (e.g. '31TCJ')",
                        type=str)
    parser.add_argument('-aid', "--aez_id",
                        help="AEZ region id for production (e.g. '46172')",
                        type=int)
    parser.add_argument('-aoi', "--user_aoi",
                        help="User AOI for production (geojson file)",
                        type=str)
    parser.add_argument('-season', "--season_type",
                        help="Season type (winter, summer1, summer2)",
                        type=str,
                        default=None)
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)

def setup_logging(loglevel: int)->None:
    """Setup basic logging
    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

def main(args: List[str])->None:
    '''Main script'''
    args = parse_args(args)
    setup_logging(args.loglevel)

    #Extract list of s2 tiles
    s2tiles_list = extract_s2tiles_list(args.s2tiles_aez_file, \
        args.tile_id, args.aez_id, args.user_aoi, args.prod_start_date)
    # logging.info("Tiles = %s", s2tiles_list)

    if not s2tiles_list:
        logging.info("No tile found")
        sys.exit(0)

    #Check number of AEZ
    aez_list = check_number_of_aez_for_selected_tiles(args.s2tiles_aez_file, s2tiles_list)

    #Get tiles info for each AEZ
    if len(aez_list) > 1:
        for aez_id in aez_list:
            s2tiles_list_subset = extract_s2tiles_list_per_aez(args.s2tiles_aez_file, \
                s2tiles_list, aez_id)

            if all(arg is None for arg in (args.tile_id, args.aez_id, args.user_aoi)):
                if args.season_type:
                    logging.info('Argument season_type is not used, \
                        value retrieved from the date provided')
                season_type = get_aez_season_type_from_date(args.s2tiles_aez_file, \
                 aez_id, args.prod_start_date)
            elif not args.season_type:
                raise ValueError("Argument season_type is missing")
            else:
                season_type = args.season_type

            season_start, season_end, season_processing_start, season_processing_end, \
                annual_processing_start, annual_processing_end, l8_enable_sr, enable_sw = \
                    get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
                        s2tiles_list_subset, season_type, args.prod_start_date)

            logging.info("AEZ = %s", int(aez_id))
            if all(arg is None for arg in (season_start, season_end)):
                logging.info("No %s season", season_type)
            else:
                logging.info("Season start date = %s", season_start)
                logging.info("Season end date = %s", season_end)
                logging.info("Season processing start date = %s", season_processing_start)
                logging.info("Season processing end date = %s", season_processing_end)
                logging.info("Annual processing start date= %s", annual_processing_start)
                logging.info("Annual processiang end date = %s", annual_processing_end)
                logging.info("L8 = %s", l8_enable_sr)
                logging.info("SW = %s", enable_sw)
                logging.info("Tiles = %s", s2tiles_list_subset)

                #Create the associated workplan
                #todo : write the work plan in json file with a file name containing aez_id
                #todo : add 6 dates + enable_sw args in WorkPlan
                WorkPlan(s2tiles_list, season_processing_start, season_processing_end, 'creodias',\
                    l8_enable_sr, int(aez_id), eodag_config_filepath="../../../eodag_config.yml")

    else:
        aez_id = aez_list[0]

        if all(arg is None for arg in (args.tile_id, args.aez_id, args.user_aoi)):
            if args.season_type:
                logging.info('Argument season_type is not used, \
                    value retrieved from the date provided')
            season_type = get_aez_season_type_from_date(args.s2tiles_aez_file, \
                aez_id, args.prod_start_date)
        elif not args.season_type:
            raise ValueError("Argument season_type is missing")
        else:
            season_type = args.season_type

        season_start, season_end, season_processing_start, season_processing_end, \
            annual_processing_start, annual_processing_end, l8_enable_sr, enable_sw = \
                get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
                    s2tiles_list, season_type, args.prod_start_date)

        logging.info("AEZ = %s", int(aez_id))
        if all(arg is None for arg in (season_start, season_end)):
            logging.info("No %s season", season_type)
        else:
            logging.info("Season start date = %s", season_start)
            logging.info("Season end date = %s", season_end)
            logging.info("Season processing start date = %s", season_processing_start)
            logging.info("Season processing end date = %s", season_processing_end)
            logging.info("Annual processing start date= %s", annual_processing_start)
            logging.info("Annual processiang end date = %s", annual_processing_end)
            logging.info("L8 = %s", l8_enable_sr)
            logging.info("SW = %s", enable_sw)
            logging.info("Tiles = %s", s2tiles_list)

            #Create the associated workplan
            #todo : write the work plan in json file with a file name containing aez_id
            #todo : add 6 dates + enable_sw args in WorkPlan
            WorkPlan(s2tiles_list, season_processing_start, season_processing_end, 'creodias',\
                l8_enable_sr, int(aez_id), eodag_config_filepath="../../../eodag_config.yml")

def run()->None:
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
