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
import json
import logging
import os
import os.path as pa
import sys
import time

from collections import defaultdict
from datetime import datetime
from osgeo import ogr
from pathlib import Path
from typing import List

from ewoc_prod.tiles_2_workplan import ewoc_s3_upload

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
    parser.add_argument('-in', '--input_file',
                        default = '/home/mbattude/Documents/WorldCereal/EWoC_Code/aez/s2tile_selection_aez.geojson',
                        help="s2tile_selection_aez.geojson, the s2tile file with aez information")
    parser.add_argument('-aid', "--aez_id",
                        help="AEZ region id for production (e.g. '46172')",
                        type=int)
    parser.add_argument('-o', "--output_path",
                        help="Output path with json files",
                        type=str,
                        default='/home/mbattude/Documents/WorldCereal/EwoC_Data/WorkPlan/WP_AEZ_prod/')
    parser.add_argument('-s3', "--s3_bucket",
                        help="Name of s3 bucket to upload wp",
                        type=str,
                        default='world-cereal')
    parser.add_argument('-s3key', "--s3_key",
                        help="Key of s3 bucket to upload wp",
                        type=str,
                        default='_WP_PHASE_II_')
    parser.add_argument('-c', "--country",
                        help="Country of the AEZ ('Canada', 'Tanzania', 'Brazil', 'Ukraine')",
                        type=str)
    parser.add_argument("-v", "--verbose",
                        dest="loglevel",
                        help="set loglevel to INFO",
                        action="store_const",
                        const=logging.INFO)
    parser.add_argument("-vv", "--very-verbose",
                        dest="loglevel",
                        help="set loglevel to DEBUG",
                        action="store_const",
                        const=logging.DEBUG)
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
            if isinstance(value, list):
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

    # Open geojson
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(args.input_file, 1)
    tiles_layer = data_source.GetLayer()

    # Apply filter
    tiles_layer.SetAttributeFilter(f"zoneID = {args.aez_id}")

    # List tiles
    tiles_id = []
    for tile in tiles_layer:
        tiles_id.append(tile.GetField('tile'))

    # Remove filter
    tiles_layer.SetAttributeFilter(None)

    # Create log folder
    # log_directory = pa.join(args.output_path, str(int(args.aez_id)), 'log')
    # if not pa.exists(log_directory):
    #     os.makedirs(log_directory)

    # Processing tiles
    tile_num = 1
    for tile in tiles_id:
        logging.info('%s:%s/%s', tile, tile_num, len(tiles_id))

        if glob.glob(pa.join(args.output_path, str(args.aez_id),\
            'json', f'{args.aez_id}_{tile}_*.json')):
            pass
        else:
            # os.system(f"nohup ewoc_prod -v -in {args.input_file} -t '{tile}' --metaseason \
            #      -s2prov aws -u c728b264-5c97-4f4c-81fe-1500d4c4dfbd -o {args.output_path} -no_upload \
            #      2>&1 > {log_directory}/log_tile_{tile}.txt &")
            try:
                os.system(f"ewoc_prod -v -in {args.input_file} -t '{tile}'\
                    --metaseason -s2prov aws -u c728b264-5c97-4f4c-81fe-1500d4c4dfbd \
                    -o {args.output_path} -no_upload")
            except Exception:
                logging.info('ERROR FOR THIS TILE')
        tile_num += 1

    # Merge all tiles to AEZ
    nb_tiles_processed = len(glob.glob(pa.join(args.output_path,\
        str(args.aez_id), 'json', f'{args.aez_id}_*.json')))

    if nb_tiles_processed == len(tiles_id):

        json_path  = pa.join(args.output_path, str(args.aez_id), 'json')
        list_files_aez = glob.glob(os.path.join(json_path, f'{args.aez_id}*.json'))

        # Prepare dicts
        i = 0
        list_dict = []

        for file_aez in list_files_aez:
            with open(file_aez, encoding="utf-8") as json_file:
                globals()[f'dict_{i}'] = json.load(json_file)

            list_dict.append(globals()[f'dict_{i}'])
            i += 1

        # Merge dicts
        date_now = datetime.now().strftime('%Y%m%d')
        filepath = pa.join(args.output_path, str(args.aez_id),\
            f"{args.aez_id}_c728b264_{date_now}.json")

        json_merged = merge_dict_list(list_dict)
        with open(filepath, "w", encoding="utf-8") as outfile:
            json.dump(json_merged, outfile, indent=4, separators=(',', ': '))

        # Export json to s3 bucket
        # ewoc_s3_upload(Path(filepath), args.s3_bucket, f'{args.s3_key}/{args.country}/{Path(filepath).name}')

    else:
        logging.info('Need to process %s missing tiles before merging to AEZ', \
            (len(tiles_id) - nb_tiles_processed))

    logging.info("--- %s seconds ---", (time.time() - start_time))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
