#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import argparse
import csv
import glob
import json
import logging
import numpy as np
import os
import os.path as pa
import sys
import time

from collections import defaultdict
from datetime import date, datetime
from itertools import repeat
from multiprocessing.pool import ThreadPool as Pool
from pathlib import Path
from typing import List

from ewoc_work_plan.workplan import WorkPlan

from ewoc_prod.tiles_2_workplan import (extract_s2tiles_list,
    check_number_of_aez_for_selected_tiles, extract_s2tiles_list_per_aez,
    get_aez_season_type_from_date, get_tiles_infos_from_tiles,
        get_tiles_metaseason_infos_from_tiles, ewoc_s3_upload)

_logger = logging.getLogger(__name__)

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
    parser.add_argument('-in', "--s2tiles_aez_file",
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
    parser.add_argument('-ut',"--user_tiles",
                        help="User tiles id for production (geojson file)",
                        type=str)
    parser.add_argument('-ult',"--user_list_tiles",
                        help="User tiles id for production (e.g. 38KKG 38KLF 38KLG)",
                        nargs="+",
                        default=[])
    parser.add_argument('-m', "--metaseason",
                        help="Active the metaseason mode that cover all seasons",
                        action='store_true')
    parser.add_argument('-m_yr', "--metaseason_year",
                        help="Year of the season to process in the metaseason mode (e.g. 2021 to process 2020/2021)",
                        type=int,
                        default=2021)
    parser.add_argument('-season', "--season_type",
                        help="Season type (winter, summer1, summer2)",
                        type=str,
                        default=None)
    parser.add_argument('-s1prov', "--s1_data_provider",
                        help="s1 provider (creodias/astraea_eod)",
                        type=str,
                        default="creodias")
    parser.add_argument('-s2prov', "--s2_data_provider",
                        help="s2 provider (peps/creodias/astraea_eod/aws)",
                        nargs="+",
                        type=str,
                        default=["creodias","aws"])
    parser.add_argument('-strategy', "--s2_strategy",
                        help="Fusion strategy (L2A,L1C)",
                        nargs="+",
                        type=str,
                        default=["L1C","L2A"])
    parser.add_argument('-u', "--user",
                        help="Username",
                        type=str,
                        default="EWoC_admin")
    parser.add_argument('-visib', "--visibility",
                        help="Visibility, public or private",
                        type=str,
                        default="public")
    parser.add_argument('-cc', "--cloudcover",
                        help="Cloudcover parameter",
                        type=int,
                        default=90)
    parser.add_argument('-min_prods', "--min_nb_prods",
                        help="Yearly minimum number of products",
                        type=int,
                        default=75)
    parser.add_argument('-orbit', "--orbit_file",
                        help="Force s1 orbit direction for a list of tiles",
                        type=str,
                        default=None)
    parser.add_argument('-rm_l1c', "--remove_l1c",
                        help="Remove L1C products or not",
                        action='store_true')
    parser.add_argument('-o', "--output_path",
                        help="Output path for json files",
                        type=str)
    parser.add_argument('-s3', "--s3_bucket",
                        help="Name of s3 bucket to upload wp",
                        type=str,
                        default='world-cereal')
    parser.add_argument('-k', "--s3_key",
                        help="Key of s3 bucket to upload wp",
                        type=str,
                        default='_WP_PHASE_II_')
    parser.add_argument('-no_s3', "--no_upload_s3",
                        help="Skip the upload of json files to s3 bucket",
                        action='store_true')
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

def merge_dict_list(dict_list):
    """
    Merge dictionnaries
    """
    default_dict = defaultdict(list)

    dictionary = dict_list[0]
    for key, value in dictionary.items():
        if isinstance(value, list):
            default_dict[key].extend(value)
        else:
            default_dict[key] = value

    for dictionary in dict_list[1:]:
        for key, value in dictionary.items():
            if (isinstance(value, list)) and (key != 's2_provider'):
                default_dict[key].extend(value)
            else:
                pass
    return dict(default_dict)

def main(args: List[str])->None:
    """
    Main script
    """
    start_time = time.time()
    args = parse_args(args)
    setup_logging(args.loglevel)

    user_short = args.user.split('-')[0]
    date_now = datetime.now().strftime('%Y%m%d')

    if not args.s2tiles_aez_file:
        raise ValueError("Argument s2tiles_aez_file is missing")
    if not args.output_path:
        raise ValueError("Argument output_path is missing")
    if args.metaseason:
        logging.info("The metaseason mode is activated")
        if all(arg is None for arg in (args.tile_id, args.aez_id, args.user_aoi, args.user_tiles, args.user_list_tiles)):
            raise ValueError("The metaseason mode requires -t, -aid, -aoi, -ut or -ult inputs and is not compatible with -pd input")

    #Extract list of s2 tiles
    s2tiles_list = extract_s2tiles_list(args.s2tiles_aez_file,
                                        args.tile_id,
                                        args.aez_id,
                                        args.user_aoi,
                                        args.user_tiles,
                                        args.user_list_tiles,
                                        args.prod_start_date)
    logging.debug("Tiles = %s", s2tiles_list)

    if not s2tiles_list:
        logging.info("No tile found")
        sys.exit(0)

    #Check number of AEZ
    aez_list = check_number_of_aez_for_selected_tiles(args.s2tiles_aez_file, s2tiles_list)
    logging.debug("AEZ = %s", aez_list)

    #Get tiles info for each AEZ
    for aez_id in aez_list:
        logging.debug("Current AEZ = %s", aez_id)
        aez_id = str(int(aez_id)) #Remove .0

        #Create output folder
        json_path = pa.join(args.output_path, aez_id, 'json')
        if not pa.exists(json_path):
            os.makedirs(json_path)

        #Extract list of s2 tiles for the aez
        if len(aez_list) == 1:
            s2tiles_list_subset = s2tiles_list
        else:
            s2tiles_list_subset = extract_s2tiles_list_per_aez(args.s2tiles_aez_file,
                                                               s2tiles_list,
                                                               aez_id)

        #Get season_type info
        if args.metaseason:
            logging.info("Argument season_type is not used in the metaseason mode")
            season_type = None
        else:
            if all(arg is None for arg in (args.tile_id,
                                            args.aez_id,
                                            args.user_aoi,
                                            args.user_tiles,
                                            args.user_list_tiles)):
                if args.season_type:
                    logging.info("Argument season_type is not used, \
                        value retrieved from the date provided")
                season_type = get_aez_season_type_from_date(args.s2tiles_aez_file,
                                                            aez_id,
                                                            args.prod_start_date)
            elif not args.season_type:
                raise ValueError("Argument season_type is missing")
            else:
                season_type = args.season_type

        #Create one WP per tile in parallel
        def process_tile(tile,
                         aez_id,
                         json_path,
                         s2tiles_aez_file,
                         s1_data_provider,
                         s2_data_provider,
                         s2_strategy,
                         user,
                         visibility,
                         cloudcover,
                         min_nb_prods,
                         orbit_file,
                         remove_l1c,
                         prod_start_date,
                         metaseason,
                         metaseason_year,
                         season_type,
                         user_short,
                         date_now):

            error_tiles = []
            if glob.glob(pa.join(json_path, f'{aez_id}_{tile}_*.json')):
                pass
            else:
                tile_lst = [tile]

                #Get tile info
                if metaseason:
                    season_type, season_start, season_end, \
                    season_processing_start, season_processing_end, \
                    annual_processing_start, annual_processing_end, wp_processing_start, \
                    wp_processing_end, l8_enable_sr, enable_sw, detector_set = \
                    get_tiles_metaseason_infos_from_tiles(s2tiles_aez_file, \
                    tile_lst, year=metaseason_year)
                else:
                    season_start, season_end, season_processing_start, season_processing_end, \
                    annual_processing_start, annual_processing_end, wp_processing_start, \
                    wp_processing_end, l8_enable_sr, enable_sw, detector_set = \
                    get_tiles_infos_from_tiles(s2tiles_aez_file, \
                    tile_lst, season_type, prod_start_date)

                meta_dict = {"season_start": str(season_start),
                            "season_end": str(season_end),
                            "season_processing_start": str(season_processing_start),
                            "season_processing_end": str(season_processing_end),
                            "annual_processing_start": str(annual_processing_start),
                            "annual_processing_end": str(annual_processing_end)}

		        #Get s1 orbit direction
                orbit_dir = None
                if orbit_file:
                    with open(orbit_file, "r") as csv_file:
                        reader = csv.reader(csv_file, delimiter=';')
                        headers = next(reader)
                        for row in reader:
                            if row[0] == tile:
                                orbit_dir = row[1]
                                logging.info("Force orbit direction to %s for tile %s", orbit_dir, tile)

                #Print tile info
                logging.info("aez_id = %s", aez_id)
                if all(arg is None for arg in (season_start, season_end)) and not metaseason:
                    logging.info("No %s season", season_type)
                else:
                    logging.info("s1_data_provider = %s", s1_data_provider)
                    logging.info("s2_data_provider = %s", s2_data_provider)
                    logging.info("strategy = %s", s2_strategy)
                    logging.info("user = %s", user)
                    logging.info("visibility = %s", visibility)
                    logging.info("cloudcover = %s", cloudcover)
                    logging.info("min_nb_prods = %s", min_nb_prods)
                    logging.info("orbit_dir = %s", orbit_dir)
                    logging.info("remove_l1c = %s", remove_l1c)
                    logging.info("season_type = %s", season_type)
                    logging.info("meta_dict = %s", meta_dict)
                    logging.info("wp_processing_start = %s", wp_processing_start)
                    logging.info("wp_processing_end = %s", wp_processing_end)
                    logging.info("l8_enable_sr = %s", l8_enable_sr)
                    logging.info("enable_sw = %s", enable_sw)
                    logging.info("detector_set = %s", detector_set)
                    logging.info("tiles = %s", tile_lst)

                #Create the associated workplan
                try:
                    wp_for_tile = WorkPlan(tile_lst,
                                        meta_dict,
                                        str(wp_processing_start),
                                        str(wp_processing_end),
                                        s1_data_provider=s1_data_provider,
                                        s2_data_provider=s2_data_provider,
                                        strategy=s2_strategy,
                                        l8_sr=l8_enable_sr,
                                        aez_id=int(aez_id),
                                        user=user,
                                        visibility=visibility,
                                        season_type=season_type,
                                        detector_set=detector_set,
                                        enable_sw=enable_sw,
                                        eodag_config_filepath="../../../eodag_config.yml",
                                        cloudcover=cloudcover,
                                        min_nb_prods=min_nb_prods,
                                        orbit_dir=orbit_dir,
                                        rm_l1c=remove_l1c)

                    #Export tile wp to json file
                    filepath = pa.join(json_path, f'{aez_id}_{tile}_{user_short}_{date_now}.json')
                    wp_for_tile.to_json(filepath)
                except AttributeError as att_err:
                    logging.error(att_err)
                    error_tiles.append([tile, att_err])
                except ValueError as val_err:
                    logging.error(val_err)
                    error_tiles.append([tile, val_err])
                except Exception as exception:
                    logging.error(exception)
                    error_tiles.append([tile, exception])

            return error_tiles

        with Pool() as pool:
            error_tiles = pool.starmap(process_tile,
                            zip(s2tiles_list_subset,
                            repeat(aez_id),
                            repeat(json_path),
                            repeat(args.s2tiles_aez_file),
                            repeat(args.s1_data_provider),
                            repeat(args.s2_data_provider),
                            repeat(args.s2_strategy),
                            repeat(args.user),
                            repeat(args.visibility),
                            repeat(args.cloudcover),
                            repeat(args.min_nb_prods),
                            repeat(args.orbit_file),
                            repeat(args.remove_l1c),
                            repeat(args.prod_start_date),
                            repeat(args.metaseason),
                            repeat(args.metaseason_year),
                            repeat(season_type),
                            repeat(user_short),
                            repeat(date_now)),
                            chunksize = 20)

        #Merge all tiles wp to AEZ wp
        list_files_aez = glob.glob(pa.join(json_path, f'{aez_id}*.json'))
        nb_tiles_processed = len(list_files_aez)

        error_tiles = [x for x in error_tiles if x]
        if len(np.array(error_tiles)) == 1:
            error_tiles = np.array(error_tiles)[0]
        else:
            error_tiles = np.squeeze(np.array(error_tiles))
        logging.info('Number of tiles with errors = %s', str(len(error_tiles)))

        error_file = pa.join(args.output_path, f'error_tiles_{aez_id}.csv')
        with open(error_file, 'w') as err_file:
            w = csv.writer(err_file, delimiter=';')
            for row in error_tiles:
                logging.info(row)
                w.writerow(row)
        err_file.close()

        if pa.isfile(error_file):
            with open(error_file, encoding="utf-8") as err_file:
                nb_tiles_error = sum(1 for line in err_file if "Can't get attribute 'W3Segment'" not in line)
                logging.info("Number of tiles with error = %s", str(nb_tiles_error))
        else:
            nb_tiles_error = 0
        logging.info("Number of tiles with error = %s", str(nb_tiles_error))

        if nb_tiles_processed == (len(s2tiles_list_subset)-nb_tiles_error):
            logging.info('All the tiles are processed (%s tiles with error)', str(nb_tiles_error))
            wp_for_aez = pa.join(args.output_path, aez_id, f'{aez_id}_{user_short}_{date_now}.json')

            if nb_tiles_processed==0:
                logging.info("No tile processed --> No merge")
            elif len(s2tiles_list_subset) == 1 or args.tile_id is not None: #only one tile
                if not args.no_upload_s3:
                    ewoc_s3_upload(Path(list_files_aez[0]), args.s3_bucket, \
                        f'{args.s3_key}/{Path(list_files_aez[0]).name}')
            else:
                #Merge wp
                i = 0
                list_dict = []
                for file_aez in list_files_aez:
                    with open(file_aez, encoding="utf-8") as json_file:
                        globals()[f'dict_{i}'] = json.load(json_file)

                    list_dict.append(globals()[f'dict_{i}'])
                    i += 1
                json_merged = merge_dict_list(list_dict)

                #Export wp to json file
                with open(wp_for_aez, "w", encoding="utf-8") as outfile:
                    json.dump(json_merged, outfile, indent=4, separators=(',', ': '))

                #Export json to s3 bucket
                if not args.no_upload_s3:
                    ewoc_s3_upload(Path(wp_for_aez), args.s3_bucket, \
                        f'{args.s3_key}/{Path(wp_for_aez).name}')

        else:
            logging.info('Need to process %s missing tiles among %s tiles before merging to AEZ', \
                (len(s2tiles_list_subset) - nb_tiles_processed), len(s2tiles_list_subset))

    logging.info("END of the Process")
    logging.info("--- Total time : %s seconds ---", (time.time() - start_time))

def run()->None:
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
