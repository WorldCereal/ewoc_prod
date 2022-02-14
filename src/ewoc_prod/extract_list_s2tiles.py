#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import argparse
import json
import logging
import sys
from datetime import date, datetime
from osgeo import ogr

def get_tiles_from_aez(s2tiles_file, aez_id):
    tiles_id = list()
    for tile in s2tiles_file:
        if int(tile.GetField('zoneID')) == aez_id:
            tiles_id.append(tile.GetField('tile'))
    return tiles_id

def get_tiles_from_aoi(s2tiles_file, aoi_geom):
    tiles_id = list()
    s2tiles_file.SetSpatialFilter(aoi_geom)
    for tile in s2tiles_file:
        tiles_id.append(tile.GetField('tile'))
    return tiles_id

def get_tiles_from_date(s2tiles_file, date, crop_type='ww'):
    end_doy = date.strftime("%j")
    aez_date_key=None
    if crop_type == "ww":
        aez_date_key = "wweos_max"
    elif crop_type == "m1":
        aez_date_key = "m1eos_max"
    elif crop_type == "m2":
        aez_date_key = "m2eos_max"
    else:
        raise ValueError
    tiles_id = list()
    for tile in s2tiles_file:
        if int(tile.GetField(aez_date_key)) == int(end_doy):
            tiles_id.append(tile.GetField('tile'))
    return tiles_id

def extract_s2tiles_list(s2tiles_aez_file, tile_id, aez_id, user_aoi, prod_start_date):
    # Load GeoJSON file containing S2 tiles and associated AEZ
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    nb_s2tiles = len(s2tiles_layer)
    logging.info('number of s2tiles = %s', str(nb_s2tiles))
    # Identify the tiles of interest from the info provided by the user
    if tile_id is not None:
        logging.info('Extract tile : %s', tile_id)
        tiles_id = list()
        tiles_id.append(tile_id)
    elif aez_id is not None:
        logging.info('Extract tiles corresponding to the aez region id: %s', aez_id)
        tiles_id = get_tiles_from_aez(s2tiles_layer, aez_id)
    elif user_aoi is not None:
        logging.info('Extract tiles corresponding to the user aoi: %s', user_aoi)
        driver = ogr.GetDriverByName('GeoJSON')
        data_source2 = driver.Open(user_aoi, 1)
        aoi_layer = data_source2.GetLayer()
        if len(aoi_layer) != 1:
            logging.info('Warning : it must be only one aoi !') # TODO : accept several polygons
        for aoi in aoi_layer:
            aoi_geom = aoi.GetGeometryRef()
            tiles_id = get_tiles_from_aoi(s2tiles_layer, aoi_geom)
    else:
        logging.info('Extract tiles corresponding to the production date requested: %s', prod_start_date)
        tiles_id = get_tiles_from_date(s2tiles_layer, prod_start_date)
    return tiles_id

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

def parse_date(date_str):
    try:
        # With python 3.7 it could be replaced by 
        # return date.isoformat(date_str)
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(date_str)
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
    s2tiles_list = extract_s2tiles_list(args.s2tiles_aez_file, \
        args.tile_id, args.aez_id, args.user_aoi, args.prod_start_date)
    logging.info("Tiles = %s", s2tiles_list) 

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
