#!/usr/bin/env python3
'''
:author: Aurélien Bricier <aurelien.bricier@csgroup.eu>
:organization: CS Group
:copyright: 2021 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2021
'''

import os
import sys
import logging
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from dateutil.relativedelta import relativedelta
from shapely.geometry import shape
from pyproj import Geod
from eotile import eotile_module
from eodag.utils.logging import setup_logging
from eodag.api.core import EODataAccessGateway



def filter_tiles(S2_Tiles, s2_exclusion_json):
    out_s2tiles = []

    for tile in S2_Tiles:

        for feature in s2_exclusion_json['features']:
            if feature['properties']['tile'] == tile.ID:
                if feature['properties']['include']:
                    #  print(feature['properties']['tile'])
                    #  print(feature['properties']['include'])
                    out_s2tiles.append(tile)
                break

    logging.info("Before filtering : %s S2 tiles / After filtering : %s S2 tiles",
                 str(len(S2_Tiles)),
                 str(len(out_s2tiles)))

    return out_s2tiles


def sub_search(sos, eos, curr_y, dag, aez, prod_type):
    nb = 0
    current_start = sos
    current_end = current_start + relativedelta(months=+1)
    date_end = eos
    while current_start < date_end:

        if date_end < current_end:
            current_end = date_end

        products, current_nb = dag.search(
            productType=prod_type,
            start=current_start.strftime("%Y-%m-%d"),
            end=current_end.strftime("%Y-%m-%d"),
            geom=aez.wkt
        )

        nb = nb + current_nb
        logging.info("[%s; %s] nb: %s",
                     sos.strftime("%Y-%m-%d"),
                     current_end.strftime("%Y-%m-%d"),
                     str(nb))
        current_start = current_end #+ relativedelta(days=+1)
        current_end = current_start + relativedelta(months=+1)

    logging.info("[%s; %s] nb: %s",
                 sos.strftime("%Y-%m-%d"),
                 eos.strftime("%Y-%m-%d"),
                 str(nb))
    return nb


def main(arguments):
    '''Entrypoint'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-a',
                        '--aez',
                        help="cropcalendar.json file")
    parser.add_argument('-e',
                        '--exclusion',
                        help="s2tile_selection.geojson file")
    parser.add_argument('-y',
                        '--year',
                        help="Year of interest")
    # TODO:
    #  parser.add_argument('-m',
                        #  '--margin',
                        #  help="Margin before Start of Season in days",
                        #  default=0)
    parser.add_argument('-t',
                        '--threshold',
                        help="Min number of S2 tiles to keep AEZ",
                        default=0)
    parser.add_argument('-o',
                        '--out',
                        help="daily.dat")
    parser.add_argument('--debug',
                        action='store_true',
                        help='Activate Debug Mode')
    args = parser.parse_args(arguments)


    logging_format = '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s'
    if args.debug is True:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=logging_format)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=logging_format)

    # load GeoJSON file containing AEZs
    with open(args.aez) as aezs:
        jsaezs = json.load(aezs)
        logging.debug("Loading %s",
                      args.aez)

    # load exclusion list
    with open(args.exclusion) as excl:
        s2_exclusion_json = json.load(excl)
        logging.debug("Loading %s",
                      args.exclusion)

    # eodag
    setup_logging(verbose=0)
    dag = EODataAccessGateway()
    dag.set_preferred_provider("astraea_eod")

    print("DoY:"
          +"; Date"
          +"; S2 tiles to be processed")

    doy_lst = []
    dat_lst = []
    s2t_lst = []

    for doy in range(1,365):
        today_s2tiles = 0
        contributing_aez = ""
        for a in jsaezs['features']:
            aez = shape(a['geometry'])
            if aez.is_valid is False:
                logging.info("AEZ [%s] (fid %s) Is invalid! Fixing it.",
                              str(a["properties"]["zoneID"]),
                              str(a["properties"]["fid"]))
                # Try fixing polygon
                aez = aez.buffer(0)

            # Check is seasons are ending today:
            if a["properties"]["m1eos_max"] == doy:
                # Process M1
                if a["properties"]["m2eos_min"]:
                    # Only M1
                    [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
                                                                                            srtm=True,
                                                                                            cop=True)
                    filtered_s2_tiles = filter_tiles(S2_Tiles, s2_exclusion_json)
                    today_s2tiles += len(filtered_s2_tiles)
                    contributing_aez += str(a["properties"]["zoneID"])+"["+str(len(filtered_s2_tiles))+"](M1) "

                else:
                    # M1+CL
                    [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
                                                                                            srtm=True,
                                                                                            cop=True)
                    filtered_s2_tiles = filter_tiles(S2_Tiles, s2_exclusion_json)
                    today_s2tiles += len(filtered_s2_tiles)
                    contributing_aez += str(a["properties"]["zoneID"])+"["+str(len(filtered_s2_tiles))+"](CL) "


            if a["properties"]["m2eos_max"] == doy:
                # Process M2+CL
                [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
                                                                                        srtm=True,
                                                                                        cop=True)
                filtered_s2_tiles = filter_tiles(S2_Tiles, s2_exclusion_json)
                today_s2tiles += len(filtered_s2_tiles)
                contributing_aez += str(a["properties"]["zoneID"])+"["+str(len(filtered_s2_tiles))+"](CL) "


            if a["properties"]["wweos_max"] == doy:
                # Process WW
                [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
                                                                                        srtm=True,
                                                                                        cop=True)
                filtered_s2_tiles = filter_tiles(S2_Tiles, s2_exclusion_json)
                today_s2tiles += len(filtered_s2_tiles)
                contributing_aez += str(a["properties"]["zoneID"])+"["+str(len(filtered_s2_tiles))+"](WW) "

        doy_lst.append(doy)
        dat_lst.append(datetime.strptime(args.year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d"))
        s2t_lst.append(today_s2tiles)

        print("DoY:"+str(doy)
              +";"+datetime.strptime(args.year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
              +";"+str(today_s2tiles)
              +";"+contributing_aez)

    data = np.column_stack((doy_lst, s2t_lst))
    np.savetxt(args.out, data)

    fig, ax = plt.subplots()
    ax.plot(*np.loadtxt(args.out,unpack=True),
         label='Projected S2 tiles to be processed',
         linewidth=2.0)
    ax.set(xlabel='Day of the Year',
           ylabel='S2 tiles to be processed')
    plt.title("Processing Forecast in 2019",
              fontsize=10)
    plt.legend(prop={'size': 6}, loc='upper left')
    # Major ticks every month.
    fmt_month = mdates.MonthLocator()
    ax.xaxis.set_major_locator(fmt_month)
    ax.grid(True)

    plt.savefig(os.path.splitext(args.out)[0]+".png", dpi=300)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
