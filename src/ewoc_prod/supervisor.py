#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import argparse
import glob
import logging
import os
import os.path as pa
import subprocess
import sys

from typing import List
from osgeo import ogr

_logger = logging.getLogger(__name__)

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
    parser.add_argument('-aez', "--aez_list",
                        help="List of aez to process",
                        nargs="+",
                        type=int)
    parser.add_argument('-orbit', "--orbit_file",
                    help="Force s1 orbit direction for a list of tiles",
                    type=str,
		    default=None)
    parser.add_argument('-o', "--output_path",
                    help="Output path for json files",
                    type=str)
    parser.add_argument('-s3_folder', "--output_s3_bucket_folder",
                    help="Name of the output bucket directory", 
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

def extract_s2tiles_list_from_aez(s2tiles_aez_file: str, aez_id: str)->List[str]:
    """
    Extraction of s2 tiles list from aez id
    :param s2tiles_aez_file: MGRS grid that contains for each included tile
        the associated aez information (geojson file)
    :param aez_id: aez id (e.g. '46172')
    """
    # Open geosjon
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(s2tiles_aez_file, 1)
    s2tiles_layer = data_source.GetLayer()

    # Identify the tiles corresponding to the AEZ
    logging.debug("Extract tiles corresponding to the aez region id: %s", aez_id)

    tiles_id = []
    for tile in s2tiles_layer:
        if int(tile.GetField('zoneID')) == aez_id:
            tiles_id.append(tile.GetField('tile'))

    logging.debug("Number of tiles selected = %s", len(tiles_id))
    return tiles_id

def main(args: List[str])->None:
    """
    Main script
    """
    args = parse_args(args)
    setup_logging(args.loglevel)

    # Loop on AEZ to process
    for aez_id in args.aez_list:
        logging.info("Current AEZ = %s", str(aez_id))

        # Create output folder
        json_path = pa.join(args.output_path, str(aez_id), 'json')
        if not pa.exists(json_path):
            os.makedirs(json_path)

        # Number of tiles to process
        tiles_to_do = extract_s2tiles_list_from_aez(args.s2tiles_aez_file, aez_id)
        nb_tiles_to_do = len(tiles_to_do)
        logging.info("Number of tiles to process = %s", str(nb_tiles_to_do))

        # Number of tiles processed
        tiles_processed = glob.glob(pa.join(json_path, f'{aez_id}*.json'))
        nb_tiles_processed = len(tiles_processed)
        logging.info("Number of tiles processed = %s", str(nb_tiles_processed))

        # Number of tiles with error
        error_file = pa.join(args.output_path, f'error_tiles_{aez_id}.csv')
        if pa.isfile(error_file):
            with open(error_file, encoding="utf-8") as err_file:
                nb_tiles_error = sum(1 for line in err_file if "Can't get attribute 'W3Segment'" not in line)
            with open(error_file, encoding="utf-8") as err_file:
                nb_tiles_random_error = sum(1 for line in err_file if "Can't get attribute 'W3Segment'" in line)
            with open(error_file, encoding="utf-8") as err_file:
                tiles_random_error = list(line.split(";")[0] for line in err_file if "Can't get attribute 'W3Segment'" in line)
        else:
            nb_tiles_error = 0
            nb_tiles_random_error = 0
            tiles_random_error = []
        logging.info("Number of tiles with error = %s", str(nb_tiles_error))
        logging.info("Number of tiles with random error = %s", str(nb_tiles_random_error))
        logging.info("Tiles with random error = %s", tiles_random_error)

        try:
            i = int(len(glob.glob(pa.join(args.output_path, f'log_{aez_id}*.txt'))) + 1) # if log files already exist for this AEZ
        except:
            i = 1 # first run for this AEZ

        while (nb_tiles_processed != (nb_tiles_to_do-nb_tiles_error)) and (i <= 10):
            logging.info("Run id = %s", i)

            # Toolbox command
            if tiles_random_error: # Run only these tiles
                cmd_ewoc_prod = f"ewoc_prod -v -in {args.s2tiles_aez_file} -ult {' '.join(tiles_random_error)} \
                    -m -s2prov creodias creodias aws aws_sng -strategy L1C L2A L2A L2A \
                        -orbit {args.orbit_file} -u c728b264-5c97-4f4c-81fe-1500d4c4dfbd  \
                            -o {args.output_path} -k _WP_PHASE_II_/{args.output_s3_bucket_folder}"
            else:
                cmd_ewoc_prod = f"ewoc_prod -v -in {args.s2tiles_aez_file} -aid '{aez_id}' \
                    -m -s2prov creodias creodias aws aws_sng -strategy L1C L2A L2A L2A \
                        -orbit {args.orbit_file} -u c728b264-5c97-4f4c-81fe-1500d4c4dfbd  \
                            -o {args.output_path} -k _WP_PHASE_II_/{args.output_s3_bucket_folder}"
            logging.info(cmd_ewoc_prod)

            logfile = pa.join(args.output_path, f'log_{aez_id}_part_{i}.txt')
            with open(logfile, 'wb') as outfile:
                try:
                    subprocess.run([cmd_ewoc_prod],
                                    stdout=outfile,#subprocess.PIPE,
                                    stderr=outfile,#subprocess.PIPE,
                                    shell=True)
                except OSError as err:
                    logging.error('An error occurred while running command \'%s\'',
                    cmd_ewoc_prod, exc_info=True)

            # Check number of tiles processed
            tiles_processed = glob.glob(pa.join(json_path, f'{aez_id}*.json'))
            nb_tiles_processed = len(tiles_processed)
            logging.info("Number of tiles processed = %s", str(nb_tiles_processed))

            # Check number of tiles with error
            error_file = pa.join(args.output_path, f'error_tiles_{aez_id}.csv')
            if pa.isfile(error_file):
                with open(error_file, encoding="utf-8") as err_file:
                    nb_tiles_error = sum(1 for line in err_file if "Can't get attribute 'W3Segment'" not in line)
            else:
                nb_tiles_error = 0
            logging.info("Number of tiles with error = %s", str(nb_tiles_error))

            i += 1

def run()->None:
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == '__main__':
    run()
