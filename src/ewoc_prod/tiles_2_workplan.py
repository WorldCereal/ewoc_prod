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
from osgeo import ogr

from ewoc_work_plan.workplan import WorkPlan

def get_tiles_from_tile(tile_id):
    """
    Get s2 tiles list from tile chosen by user
    :param tile_id: tile id (e.g. '31TCJ' Toulouse)
    """
    tiles_id = []
    tiles_id.append(tile_id)
    return tiles_id

def get_tiles_from_aez(s2tiles_layer, aez_id):
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

def get_tiles_from_aoi(s2tiles_layer, aoi_geom):
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

def get_tiles_from_date(s2tiles_layer, prod_start_date):
    """
    Get s2 tiles list from aoi provided by user
    :param s2tiles_layer: MGRS grid that contains for each included tile
        the associated aez information
    :param prod_start_date: production start date
    """
    end_doy = prod_start_date.strftime("%j")
    #Get s2 tiles list and corresponding season
    tiles_id = []
    season = []
    for tile in s2tiles_layer:
        if int(tile.GetField("wweos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
            season.append("winter")
        elif int(tile.GetField("m1eos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
            season.append("summer1")
        elif int(tile.GetField("m2eos_max")) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
            season.append("summer2")
    season = list(set(season))
    if len(season) > 1:
        logging.info('The date provided by user corresponds to several seasons')
        sys.exit(1)
    return tiles_id, season

def extract_s2tiles_list(s2tiles_aez_file, tile_id, aez_id, user_aoi, prod_start_date):
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
    season = None
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
        logging.info('Extract tiles corresponding to the production \
            date requested: %s', prod_start_date)
        tiles_id, season = get_tiles_from_date(s2tiles_layer, prod_start_date)
    return tiles_id, season

def check_number_of_aez_for_selected_tiles(s2tiles_aez_file, tiles_id):
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

def extract_s2tiles_list_per_aez(s2tiles_aez_file, tiles_id, aez_id):
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

def get_aez_dates_from_season_type(season_type):
    """
    Get the start/end dates for the aez
    :param season_type: season type (winter, summer1, summer2)
    """
    aez_start_date_key=None
    aez_end_date_key=None
    if season_type == "winter":
        aez_start_date_key = "wweos_min"
        aez_end_date_key = "wweos_max"
    elif season_type == "summer1":
        aez_start_date_key = "m1eos_min"
        aez_end_date_key = "m1eos_max"
    elif season_type == "summer1":
        aez_start_date_key = "m2eos_min"
        aez_end_date_key = "m2eos_max"
    else:
        raise ValueError
    return aez_start_date_key, aez_end_date_key

def conversion_doy_to_date(doy):
    """
    Convert day of year to date YYYY-mm-dd
    :param doy: day of year
    """
    year = str(date.today().year)
    str(doy).rjust(3 + len(str(doy)), '0')
    date_format = datetime.strptime(year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
    return date_format

def get_tiles_infos_from_tiles(s2tiles_aez_file, tiles_id, season):
    """
    Get some tiles informations (dates, l8_sr)
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param tiles_id: list of s2 tiles selected
    :param season: season type (winter, summer1, summer2)
    """
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    tiles_id_str = '(' + ','.join(f"'{tile_id}'" for tile_id in tiles_id) + ')'
    s2tiles_layer.SetAttributeFilter(f"tile IN {tiles_id_str}")
    tile = s2tiles_layer.GetNextFeature()
    #Get aez dates
    aez_start_date_key, aez_end_date_key = get_aez_dates_from_season_type(season)
    #Get dates info
    start_date = tile.GetField(aez_start_date_key)
    end_date = tile.GetField(aez_end_date_key)
    #Conversion start_date/end_date
    start_date = conversion_doy_to_date(start_date)
    end_date = conversion_doy_to_date(end_date)
    #Get L8 info
    if tile.GetField('L8')==0:
        l8_sr = False
    elif tile.GetField('L8')==1:
        l8_sr = True
    else:
        raise ValueError
    #Remove filter
    s2tiles_layer.SetAttributeFilter(None)
    return start_date, end_date, l8_sr

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

def parse_date(date_str):
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

def parse_args(args):
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
                        '--s2tiles_aez_file',
                        help="s2tiles_aez.geojson file")
    parser.add_argument("-pd", "--prod_start_date",
                        help="Production start date - format YYYY-MM-DD",
                        type=parse_date,
                        default=date.today())
    parser.add_argument("-t","--tile_id",
                        help="Tile id for production",
                        type=str)
    parser.add_argument('-aid', "--aez_id",
                        help="AEZ region id for production",
                        type=int)
    parser.add_argument('-aoi', "--user_aoi",
                        help="User AOI for production",
                        type=str)
    parser.add_argument('-season', "--season_type",
                        help="Season type",
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

def setup_logging(loglevel):
    """Setup basic logging
    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

def main(args):
    '''Main script'''
    args = parse_args(args)
    setup_logging(args.loglevel)

    #Extract list of s2 tiles
    s2tiles_list, season = extract_s2tiles_list(args.s2tiles_aez_file, \
        args.tile_id, args.aez_id, args.user_aoi, args.prod_start_date)
    # logging.info("Tiles = %s", s2tiles_list)

    if not s2tiles_list:
        logging.info("No tile found")
        sys.exit(0)

    #Check number of AEZ
    aez_list = check_number_of_aez_for_selected_tiles(args.s2tiles_aez_file, s2tiles_list)

    #Get tiles info for each AEZ
    if not season:
        season = args.season_type
    else:
        season = season[0]
    if len(aez_list) > 1:
        for aez_id in aez_list:
            s2tiles_list_subset = extract_s2tiles_list_per_aez(args.s2tiles_aez_file, \
                s2tiles_list, aez_id)
            start_date, end_date, l8_sr = get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
                s2tiles_list_subset, season)
            logging.info("AEZ = %s", int(aez_id))
            logging.info("Start date = %s", start_date)
            logging.info("End date = %s", end_date)
            logging.info("L8 = %s", l8_sr)
            logging.info("Tiles = %s", s2tiles_list_subset)

            #Create the associated workplan
            #todo : write the work plan in json file with a file name containing aez_id
            WorkPlan(s2tiles_list, start_date, end_date, 'creodias', l8_sr, int(aez_id), \
                eodag_config_filepath="../../../eodag_config.yml")

    else:
        aez_id = aez_list[0]
        start_date, end_date, l8_sr = get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
            s2tiles_list, season)
        logging.info("AEZ = %s", int(aez_id))
        logging.info("Start date = %s", start_date)
        logging.info("End date = %s", end_date)
        logging.info("L8 = %s", l8_sr)
        logging.info("Tiles = %s", s2tiles_list)

        #Create the associated workplan
        #todo : write the work plan in json file with a file name containing aez_id
        WorkPlan(s2tiles_list, start_date, end_date, 'creodias', l8_sr, int(aez_id), \
            eodag_config_filepath="../../../eodag_config.yml")

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
