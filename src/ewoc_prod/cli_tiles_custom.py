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
import time
from osgeo import ogr
from typing import List

from ewoc_prod.tiles_2_workplan import retrieve_custom_dates
from ewoc_work_plan.workplan import WorkPlan

_logger = logging.getLogger(__name__)

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

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
    parser.add_argument('-t',"--tile_id",
                        help="Tile id for production (e.g. '31TCJ')",
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
    start_time = time.time()
    args = parse_args(args)
    setup_logging(args.loglevel)

    #Get tiles_list
    s2tiles_list = []
    s2tiles_list.append(args.tile_id)
    #Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(args.s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()
    #Add filter
    s2tiles_layer.SetAttributeFilter(f"tile = '{args.tile_id}'")
    tile = s2tiles_layer.GetNextFeature()
    #Get AEZ id
    aez_id = tile.GetField('zoneID')
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
    #Get other infos
    season_type = 'custom'
    season_start = 'None'
    season_end = 'None'
    season_processing_start = 'None'
    season_processing_end = 'None'
    annual_processing_start = 'None'
    annual_processing_end = 'None'
    wp_processing_start, wp_processing_end = \
        retrieve_custom_dates(args.s2tiles_aez_file, args.tile_id, year=2021)
    detector_set = 'None'

    # logging.info("aez_id = %s", int(aez_id))
    # logging.info("season_type = %s", season_type)
    # logging.info("season_start = %s", season_start)
    # logging.info("season_end = %s", season_end)
    # logging.info("season_processing_start = %s", season_processing_start)
    # logging.info("season_processing_end = %s", season_processing_end)
    # logging.info("annual_processing_start = %s", annual_processing_start)
    # logging.info("annual_processing_end = %s", annual_processing_end)
    # logging.info("wp_processing_start = %s", wp_processing_start)
    # logging.info("wp_processing_end = %s", wp_processing_end)
    # logging.info("l8_enable_sr = %s", l8_enable_sr)
    # logging.info("enable_sw = %s", enable_sw)
    # logging.info("detector_set = %s", detector_set)
    # logging.info("tiles = %s", s2tiles_list)

    # Create the associated workplan
    wp_for_aez = WorkPlan(s2tiles_list, str(season_start), str(season_end), \
        str(season_processing_start), str(season_processing_end), \
            str(annual_processing_start), str(annual_processing_end), \
            str(wp_processing_start), str(wp_processing_end), \
                data_provider='creodias', l8_sr=l8_enable_sr, aez_id=int(aez_id), \
                    user="EWoC_admin", visibility="public", season_type=season_type,\
                        detector_set=detector_set, enable_sw=enable_sw, \
                            eodag_config_filepath="../../../eodag_config.yml")
    # print(wp_for_aez.__dict__)
    wp_for_aez.to_json(f'wp_aez_{int(aez_id)}_tile_{args.tile_id}_creodias_v2.json')

    logging.info("--- %s seconds ---", (time.time() - start_time))

def run()->None:
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
