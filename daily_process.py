#!/usr/bin/env python3
'''
:author: Aurélien Bricier <aurelien.bricier@csgroup.eu>
:organization: CS Group
:copyright: 2021 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2021
'''
import sys
import logging
import argparse
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from shapely.geometry import shape
from pyproj import Geod
from eotile import eotile_module
from eodag.utils.logging import setup_logging
from eodag.api.core import EODataAccessGateway



def filter_tiles(S2_Tiles, s2_exclusion_json):
    out_s2tiles = []

    logging.info("Before filtering : %s S2 tiles / After filtering : %s S2 tiles",
                 str(len(S2_Tiles)),
                 str(len(out_s2tiles)))

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
                        help="filtered.json")
    parser.add_argument('--debug',
                        action='store_true',
                        help='Activate Debug Mode')
    args = parser.parse_args(arguments)


    logging_format = '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s'
    if args.debug is True:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=logging_format)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=logging_format)

    #  geo = osr.SpatialReference()
    #  geo.ImportFromEPSG(4326)
    #  drv = ogr.GetDriverByName( 'GeoJSON' )
    #  if os.path.exists(args.out):
        #  os.remove(args.out)
    #  dst_ds = drv.CreateDataSource(args.out)
    #  dst_layer = dst_ds.CreateLayer('', srs=geo , \
                                   #  geom_type=ogr.wkbPolygon )

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

        print("DoY:"+str(doy)
              +";"+datetime.strptime(args.year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
              +";"+str(today_s2tiles)
              +";"+contributing_aez)






        #  # Print the area in deg^2
        #  print(str(aez.area) +" deg^2")
        #
        #  # Print the area in km^2
        #  geod = Geod(ellps="WGS84")
        #  area = abs(geod.geometry_area_perimeter(aez)[0])
        #  area_str='{:12.3f}'.format(area/1e6)
        #  print(area_str +" km^2")
        #
        #  [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
        #                                                                          srtm=True,
        #                                                                          cop=True)
        #
        #  filtered_s2_tiles = filter_tiles(S2_Tiles, s2_exclusion_json)
        #
        #  if a["properties"]["m1sos_min"] and a["properties"]["m1eos_min"]:
        #      year = str(args.year)
        #      if (a["properties"]["m1sos_min"]) > int(a["properties"]["m1eos_max"]):
        #          year = str(int(args.year)+1)
        #      m1eos = int(a["properties"]["m1eos_max"])
        #      m1trigweek = datetime.strptime(year + "-" + str(m1eos), "%Y-%j").strftime("%Y-%U")
        #      cltrigweek = m1trigweek
        #
        #  if a["properties"]["m2sos_min"] and a["properties"]["m2eos_min"]:
        #      year = str(args.year)
        #      if (a["properties"]["m2sos_min"]) > int(a["properties"]["m2eos_max"]):
        #          year = str(int(args.year)+1)
        #      m2eos = int(a["properties"]["m2eos_max"])
        #      m2trigweek = datetime.strptime(year + "-" + str(m2eos), "%Y-%j").strftime("%Y-%U")
        #      cltrigweek = m2trigweek
        #
        #
        #  if a["properties"]["wwsos_min"] and a["properties"]["wweos_min"]:
        #      year = str(args.year)
        #      if (a["properties"]["wwsos_min"]) > int(a["properties"]["wweos_max"]):
        #          year = str(int(args.year)+1)
        #      wweos = int(a["properties"]["wweos_max"])
        #      wwtrigweek = datetime.strptime(year + "-" + str(wweos), "%Y-%j").strftime("%Y-%U")
        #
        #
        #  if len(filtered_s2_tiles) >= int(args.threshold):
        #      if a["properties"]["m1sos_min"]:
        #          if m1trigweek == cltrigweek:
        #              print("fid:"+str(int(a["properties"]["fid"]))
        #                    +";"+str(a["properties"]["zoneID"])
        #                    +";"+area_str
        #                    +";M1 + CL"
        #                    +";"
        #                    +";"
        #                    +";"+cltrigweek
        #                    +";"+str(len(S2_Tiles))
        #                    +";"+str(len(filtered_s2_tiles))
        #                    +";"
        #                    +";"+str(len(L8_Tiles))
        #                    +";"
        #                    +";"
        #                    +";"+str(len(SRTM_Tiles))
        #                    +";"+str(len(Copernicus_Tiles)))
        #          else:
        #              print("fid:"+str(int(a["properties"]["fid"]))
        #                    +";"+str(a["properties"]["zoneID"])
        #                    +";"+area_str
        #                    +";M1"
        #                    +";"
        #                    +";"
        #                    +";"+m1trigweek
        #                    +";"+str(len(S2_Tiles))
        #                    +";"+str(len(filtered_s2_tiles))
        #                    +";"
        #                    +";"+str(len(L8_Tiles))
        #                    +";"
        #                    +";"
        #                    +";"+str(len(SRTM_Tiles))
        #                    +";"+str(len(Copernicus_Tiles)))
        #
        #      if a["properties"]["m2sos_min"]:
        #          if m2trigweek == cltrigweek:
        #              print("fid:"+str(int(a["properties"]["fid"]))
        #                    +";"+str(a["properties"]["zoneID"])
        #                    +";"+area_str
        #                    +";M2 + CL"
        #                    +";"
        #                    +";"
        #                    +";"+cltrigweek
        #                    +";"+str(len(S2_Tiles))
        #                    +";"+str(len(filtered_s2_tiles))
        #                    +";"
        #                    +";"+str(len(L8_Tiles))
        #                    +";"
        #                    +";"
        #                    +";"+str(len(SRTM_Tiles))
        #                    +";"+str(len(Copernicus_Tiles)))
        #          else:
        #              print("fid:"+str(int(a["properties"]["fid"]))
        #                    +";"+str(a["properties"]["zoneID"])
        #                    +";"+area_str
        #                    +";M2"
        #                    +";"
        #                    +";"
        #                    +";"+m2trigweek
        #                    +";"+str(len(S2_Tiles))
        #                    +";"+str(len(filtered_s2_tiles))
        #                    +";"
        #                    +";"+str(len(L8_Tiles))
        #                    +";"
        #                    +";"
        #                    +";"+str(len(SRTM_Tiles))
        #                    +";"+str(len(Copernicus_Tiles)))
        #
        #      if a["properties"]["wwsos_min"]:
        #          print("fid:"+str(int(a["properties"]["fid"]))
        #                +";"+str(a["properties"]["zoneID"])
        #                +";"+area_str
        #                +";WW"
        #                +";"
        #                +";"
        #                +";"+wwtrigweek
        #                +";"+str(len(S2_Tiles))
        #                +";"+str(len(filtered_s2_tiles))
        #                +";"
        #                +";"+str(len(L8_Tiles))
        #                +";"
        #                +";"
        #                +";"+str(len(SRTM_Tiles))
        #                +";"+str(len(Copernicus_Tiles)))



if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
