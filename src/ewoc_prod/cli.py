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
from datetime import date, datetime
from typing import List

from ewoc_prod.tiles_2_workplan import (extract_s2tiles_list, \
    check_number_of_aez_for_selected_tiles, extract_s2tiles_list_per_aez, \
    get_aez_season_type_from_date, get_tiles_infos_from_tiles, \
        get_tiles_metaseason_infos_from_tiles)

from ewoc_work_plan.workplan import WorkPlan

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
    parser.add_argument('-meta', "--metaseason",
                        help="Active the metaseason mode that cover all seasons",
                        action='store_true')
    parser.add_argument('-meta_yr', "--metaseason_year",
                        help="Year of the season to process in the metaseason mode (e.g. 2021 to process 2020/2021)",
                        type=int,
                        default=2021)
    parser.add_argument('-season', "--season_type",
                        help="Season type (winter, summer1, summer2)",
                        type=str,
                        default=None)
    parser.add_argument('-s2prov', "--s2_data_provider",
                        help="s2 provider (peps/creodias/astraea_eod/aws)",
                        type=str,
                        default="creodias")
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
                        default=95)
    parser.add_argument('-min_prods', "--min_nb_prods",
                        help="Yearly minimum number of products",
                        type=int,
                        default=70)
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

        if args.metaseason:
            raise ValueError("Not possible to have more than one AEZ in metaseason mode : use only tile_id or aez_id as input")

        for aez_id in aez_list:
            s2tiles_list_subset = extract_s2tiles_list_per_aez(args.s2tiles_aez_file, \
                s2tiles_list, aez_id)

            if all(arg is None for arg in (args.tile_id, args.aez_id, args.user_aoi)):
                if args.season_type:
                    logging.info("Argument season_type is not used, \
                        value retrieved from the date provided")
                season_type = get_aez_season_type_from_date(args.s2tiles_aez_file, \
                 aez_id, args.prod_start_date)
            elif not args.season_type:
                raise ValueError("Argument season_type is missing")
            else:
                season_type = args.season_type

            season_start, season_end, season_processing_start, season_processing_end, \
                annual_processing_start, annual_processing_end, wp_processing_start, \
                    wp_processing_end, l8_enable_sr, enable_sw, detector_set = \
                        get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
                            s2tiles_list_subset, season_type, args.prod_start_date)

            logging.info("aez_id = %s", int(aez_id))
            if all(arg is None for arg in (season_start, season_end)):
                logging.info("No %s season", season_type)
            else:
                logging.info("data_provider = %s", args.s2_data_provider)
                logging.info("user = %s", args.user)
                logging.info("visibility = %s", args.visibility)
                logging.info("cloudcover = %s", args.cloudcover)
                logging.info("min_nb_prods = %s", args.min_nb_prods)
                logging.info("season_type = %s", season_type)
                logging.info("season_start = %s", season_start)
                logging.info("season_end = %s", season_end)
                logging.info("season_processing_start = %s", season_processing_start)
                logging.info("season_processing_end = %s", season_processing_end)
                logging.info("annual_processing_start = %s", annual_processing_start)
                logging.info("annual_processing_end = %s", annual_processing_end)
                logging.info("wp_processing_start = %s", wp_processing_start)
                logging.info("wp_processing_end = %s", wp_processing_end)
                logging.info("l8_enable_sr = %s", l8_enable_sr)
                logging.info("enable_sw = %s", enable_sw)
                logging.info("detector_set = %s", detector_set)
                logging.info("tiles = %s", s2tiles_list_subset)

                #Create the associated workplan
                wp_for_aez = WorkPlan(s2tiles_list, str(season_start), str(season_end), \
                    str(season_processing_start), str(season_processing_end), \
                        str(annual_processing_start), str(annual_processing_end), \
                            str(wp_processing_start), str(wp_processing_end), \
                                data_provider=args.s2_data_provider, l8_sr=l8_enable_sr, \
                                    aez_id=int(aez_id), user=args.user, \
                                        visibility=args.visibility, season_type=season_type,\
                                            detector_set=detector_set, enable_sw=enable_sw, \
                                                eodag_config_filepath="../../../eodag_config.yml", \
                                                    cloudcover=args.cloudcover, \
                                                        min_nb_prods=args.min_nb_prods)
                wp_for_aez.to_json(f'wp_aez_{int(aez_id)}_{args.s2_data_provider}.json')
    else:
        aez_id = aez_list[0]

        if args.metaseason:
            logging.info("The metaseason mode is activated")
            if all(arg is None for arg in (args.tile_id, args.aez_id)):
                raise ValueError("The metaseason mode requires -t or -aid inputs and is not compatible with -pd and -aoi inputs")
            if args.season_type:
                logging.info("Argument season_type is not used in the metaseason mode")

            season_type, season_start, season_end, season_processing_start, season_processing_end, \
            annual_processing_start, annual_processing_end, wp_processing_start, \
                wp_processing_end, l8_enable_sr, enable_sw, detector_set = \
                    get_tiles_metaseason_infos_from_tiles(args.s2tiles_aez_file, \
                        s2tiles_list, year=args.metaseason_year)

            logging.info("aez_id = %s", int(aez_id))
            logging.info("data_provider = %s", args.s2_data_provider)
            logging.info("user = %s", args.user)
            logging.info("visibility = %s", args.visibility)
            logging.info("cloudcover = %s", args.cloudcover)
            logging.info("min_nb_prods = %s", args.min_nb_prods)
            logging.info("season_type = %s", season_type)
            logging.info("season_start = %s", season_start)
            logging.info("season_end = %s", season_end)
            logging.info("season_processing_start = %s", season_processing_start)
            logging.info("season_processing_end = %s", season_processing_end)
            logging.info("annual_processing_start = %s", annual_processing_start)
            logging.info("annual_processing_end = %s", annual_processing_end)
            logging.info("wp_processing_start = %s", wp_processing_start)
            logging.info("wp_processing_end = %s", wp_processing_end)
            logging.info("l8_enable_sr = %s", l8_enable_sr)
            logging.info("enable_sw = %s", enable_sw)
            logging.info("detector_set = %s", detector_set)
            logging.info("tiles = %s", s2tiles_list)

            # Create the associated workplan
            wp_for_aez = WorkPlan(s2tiles_list, str(season_start), str(season_end), \
                str(season_processing_start), str(season_processing_end), \
                    str(annual_processing_start), str(annual_processing_end), \
                        str(wp_processing_start), str(wp_processing_end), \
                            data_provider=args.s2_data_provider, l8_sr=l8_enable_sr, \
                                aez_id=int(aez_id), user=args.user, \
                                    visibility=args.visibility, season_type=season_type,\
                                        detector_set=detector_set, enable_sw=enable_sw, \
                                            eodag_config_filepath="../../../eodag_config.yml", \
                                                cloudcover=args.cloudcover, \
                                                    min_nb_prods=args.min_nb_prods)
                # print(wp_for_aez.__dict__)
            if args.tile_id:
                wp_for_aez.to_json(f"wp_aez_{int(aez_id)}_tile_{args.tile_id}_metaseason_{args.s2_data_provider}.json")
            else:
                wp_for_aez.to_json(f"wp_aez_{int(aez_id)}_metaseason_{args.s2_data_provider}.json")

        else:

            if all(arg is None for arg in (args.tile_id, args.aez_id, args.user_aoi)):
                if args.season_type:
                    logging.info("Argument season_type is not used, \
                        value retrieved from the date provided")
                season_type = get_aez_season_type_from_date(args.s2tiles_aez_file, \
                    aez_id, args.prod_start_date)
            elif not args.season_type:
                raise ValueError("Argument season_type is missing")
            else:
                season_type = args.season_type

            season_start, season_end, season_processing_start, season_processing_end, \
                annual_processing_start, annual_processing_end, wp_processing_start, \
                    wp_processing_end, l8_enable_sr, enable_sw, detector_set = \
                        get_tiles_infos_from_tiles(args.s2tiles_aez_file, \
                            s2tiles_list, season_type, args.prod_start_date)

            logging.info("aez_id = %s", int(aez_id))
            if all(arg is None for arg in (season_start, season_end)):
                logging.info("No %s season", season_type)
            else:
                logging.info("data_provider = %s", args.s2_data_provider)
                logging.info("user = %s", args.user)
                logging.info("visibility = %s", args.visibility)
                logging.info("cloudcover = %s", args.cloudcover)
                logging.info("min_nb_prods = %s", args.min_nb_prods)
                logging.info("season_type = %s", season_type)
                logging.info("season_start = %s", season_start)
                logging.info("season_end = %s", season_end)
                logging.info("season_processing_start = %s", season_processing_start)
                logging.info("season_processing_end = %s", season_processing_end)
                logging.info("annual_processing_start = %s", annual_processing_start)
                logging.info("annual_processing_end = %s", annual_processing_end)
                logging.info("wp_processing_start = %s", wp_processing_start)
                logging.info("wp_processing_end = %s", wp_processing_end)
                logging.info("l8_enable_sr = %s", l8_enable_sr)
                logging.info("enable_sw = %s", enable_sw)
                logging.info("detector_set = %s", detector_set)
                logging.info("tiles = %s", s2tiles_list)

                # Create the associated workplan
                wp_for_aez = WorkPlan(s2tiles_list, str(season_start), str(season_end), \
                    str(season_processing_start), str(season_processing_end), \
                        str(annual_processing_start), str(annual_processing_end), \
                            str(wp_processing_start), str(wp_processing_end), \
                                data_provider=args.s2_data_provider, l8_sr=l8_enable_sr, \
                                    aez_id=int(aez_id), user=args.user, \
                                        visibility=args.visibility, season_type=season_type,\
                                            detector_set=detector_set, enable_sw=enable_sw, \
                                                eodag_config_filepath="../../../eodag_config.yml", \
                                                    cloudcover=args.cloudcover, \
                                                        min_nb_prods=args.min_nb_prods)
                if args.tile_id:
                    wp_for_aez.to_json(f'wp_aez_{int(aez_id)}_tile_{args.tile_id}_{args.s2_data_provider}.json')
                else:
                    wp_for_aez.to_json(f'wp_aez_{int(aez_id)}.json')
    logging.info("--- %s seconds ---", (time.time() - start_time))

def run()->None:
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
