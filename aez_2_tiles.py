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



#  from osgeo import ogr
#  from osgeo import osr


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
                        help="cropcaledanr.json file")
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

    # eodag
    setup_logging(verbose=0)
    dag = EODataAccessGateway()
    dag.set_preferred_provider("astraea_eod")

    print("fid:"
          +"; Zone ID"
          +"; Area (km2)"
          +"; Season ID"
          +"; sos"
          +"; eos"
          +"; Trigger Week"
          +"; nb_S2_tiles"
          +"; nb_S2_prods"
          +"; nb_L8_tiles"
          +"; nb_L8_prods"
          +"; nb_S1_prods"
          +"; nb_SRTM_tiles"
          +"; nb_COPDEM_tiles")

    for a in jsaezs['features']:
        aez = shape(a['geometry'])
        if aez.is_valid is False:
            logging.info("AEZ [%s] (fid %s) Is invalid! Fixing it.",
                          str(a["properties"]["zoneID"]),
                          str(a["properties"]["fid"]))
            # Try fixing polygon
            aez = aez.buffer(0)

        logging.info("Processing AEZ [%s] (fid %s)",
                     str(a["properties"]["zoneID"]),
                     str(a["properties"]["fid"]))

        # Print the area in deg^2
        print(str(aez.area) +" deg^2")

        # Print the area in km^2
        geod = Geod(ellps="WGS84")
        area = abs(geod.geometry_area_perimeter(aez)[0])
        area_str='{:12.3f}'.format(area/1e6)
        print(area_str +" km^2")

        [S2_Tiles, L8_Tiles, SRTM_Tiles, Copernicus_Tiles] = eotile_module.main(aez.wkt,
                                                                                srtm=True,
                                                                                cop=True)

        if a["properties"]["m1sos_min"]:
            year = str(args.year)
            m1sos = int(a["properties"]["m1sos_min"])
            dm1sos = datetime.strptime(year + "-" + str(m1sos), "%Y-%j")
            sm1sos = dm1sos.strftime("%Y-%m-%d")
            if (a["properties"]["m1sos_min"]) > int(a["properties"]["m1eos_max"]):
                year = str(int(args.year)+1)
            m1eos = int(a["properties"]["m1eos_max"])
            dm1eos = datetime.strptime(year + "-" + str(m1eos), "%Y-%j")
            sm1eos = dm1eos.strftime("%Y-%m-%d")
            m1trigweek = datetime.strptime(year + "-" + str(m1eos), "%Y-%j").strftime("%Y-%U")

            dclsos = datetime.strptime(str(int(year)-1) + "-" + str(m1eos), "%Y-%j")
            dcleos = datetime.strptime(year + "-" + str(m1eos), "%Y-%j")
            cltrigweek = m1trigweek

            logging.info("M1: [%s; %s]",
                         sm1sos,
                         sm1eos)

        if a["properties"]["m2sos_min"]:
            #  print(a["properties"]["m2sos_min"])
            year = str(args.year)
            m2sos = int(a["properties"]["m2sos_min"])
            dm2sos = datetime.strptime(year + "-" + str(m2sos), "%Y-%j")
            sm2sos = dm2sos.strftime("%Y-%m-%d")
            if (a["properties"]["m2sos_min"]) > int(a["properties"]["m2eos_max"]):
                year = str(int(args.year)+1)
            m2eos = int(a["properties"]["m2eos_max"])
            dm2eos = datetime.strptime(year + "-" + str(m2eos), "%Y-%j")
            sm2eos = dm2eos.strftime("%Y-%m-%d")
            m2trigweek = datetime.strptime(year + "-" + str(m2eos), "%Y-%j").strftime("%Y-%U")

            dclsos = datetime.strptime(str(int(year)-1) + "-" + str(m2eos), "%Y-%j")
            dcleos = datetime.strptime(year + "-" + str(m2eos), "%Y-%j")
            cltrigweek = m2trigweek

            logging.info("M2: [%s; %s]",
                         sm2sos,
                         sm2eos)

        if a["properties"]["wwsos_min"]:
            year = str(args.year)
            wwsos = int(a["properties"]["wwsos_min"])
            dwwsos = datetime.strptime(year + "-" + str(wwsos), "%Y-%j")
            swwsos = dwwsos.strftime("%Y-%m-%d")
            if (a["properties"]["wwsos_min"]) > int(a["properties"]["wweos_max"]):
                year = str(int(args.year)+1)
            wweos = int(a["properties"]["wweos_max"])
            dwweos = datetime.strptime(year + "-" + str(wweos), "%Y-%j")
            swweos = dwweos.strftime("%Y-%m-%d")
            wwtrigweek = datetime.strptime(year + "-" + str(wweos), "%Y-%j").strftime("%Y-%U")

            logging.info("WW: [%s; %s]",
                         swwsos,
                         swweos)


        if len(S2_Tiles) >= int(args.threshold):
            # eodag

            if a["properties"]["m2sos_min"]:
                nb_m1s1 = sub_search(dm1sos, dm1eos, args.year, dag, aez, 'sentinel1_l1c_grd')
                nb_m1s2 = sub_search(dm1sos, dm1eos, args.year, dag, aez, 'sentinel2_l1c')

                products, nb_m1l8 = dag.search(
                    productType='landsat8_l1tp',
                    start=sm1sos,
                    end=sm1eos,
                    geom=aez.wkt
                )

            if a["properties"]["m2sos_min"]:

                nb_m2s1 = sub_search(dm2sos, dm2eos, args.year, dag, aez, 'sentinel1_l1c_grd')
                nb_m2s2 = sub_search(dm2sos, dm2eos, args.year, dag, aez, 'sentinel2_l1c')

                products, nb_m2l8 = dag.search(
                    productType='landsat8_l1tp',
                    start=sm2sos,
                    end=sm2eos,
                    geom=aez.wkt
                )

            if a["properties"]["m1sos_min"]:
                nb_cls1 = sub_search(dclsos, dcleos, args.year, dag, aez, 'sentinel1_l1c_grd')
                nb_cls2 = sub_search(dclsos, dcleos, args.year, dag, aez, 'sentinel2_l1c')

                products, nb_cll8 = dag.search(
                    productType='landsat8_l1tp',
                    start=dclsos.strftime("%Y-%m-%d"),
                    end=dcleos.strftime("%Y-%m-%d"),
                    geom=aez.wkt
                )

            if a["properties"]["wwsos_min"]:
                nb_wws1 = sub_search(dwwsos, dwweos, args.year, dag, aez, 'sentinel1_l1c_grd')
                nb_wws2 = sub_search(dwwsos, dwweos, args.year, dag, aez, 'sentinel2_l1c')

                products, nb_wwl8 = dag.search(
                    productType='landsat8_l1tp',
                    start=swwsos,
                    end=swweos,
                    geom=aez.wkt
                )


            if a["properties"]["m1sos_min"]:
                print("fid:"+str(int(a["properties"]["fid"]))
                      +";"+str(a["properties"]["zoneID"])
                      +";"+area_str
                      +";M1"
                      +";"+sm1sos
                      +";"+sm1eos
                      +";"+m1trigweek
                      +";"+str(len(S2_Tiles))
                      +";"+str(nb_m1s2)
                      +";"+str(len(L8_Tiles))
                      +";"+str(nb_m1l8)
                      +";"+str(nb_m1s1)
                      +";"+str(len(SRTM_Tiles))
                      +";"+str(len(Copernicus_Tiles)))

            if a["properties"]["m2sos_min"]:
                print("fid:"+str(int(a["properties"]["fid"]))
                      +";"+str(a["properties"]["zoneID"])
                      +";"+area_str
                      +";M2"
                      +";"+sm2sos
                      +";"+sm2eos
                      +";"+m2trigweek
                      +";"+str(len(S2_Tiles))
                      +";"+str(nb_m2s2)
                      +";"+str(len(L8_Tiles))
                      +";"+str(nb_m2l8)
                      +";"+str(nb_m2s1)
                      +";"+str(len(SRTM_Tiles))
                      +";"+str(len(Copernicus_Tiles)))

            if a["properties"]["m1sos_min"]:
                print("fid:"+str(int(a["properties"]["fid"]))
                      +";"+str(a["properties"]["zoneID"])
                      +";"+area_str
                      +";CL"
                      +";"+dclsos.strftime("%Y-%m-%d")
                      +";"+dcleos.strftime("%Y-%m-%d")
                      +";"+cltrigweek
                      +";"+str(len(S2_Tiles))
                      +";"+str(nb_cls2)
                      +";"+str(len(L8_Tiles))
                      +";"+str(nb_cll8)
                      +";"+str(nb_cls1)
                      +";"+str(len(SRTM_Tiles))
                      +";"+str(len(Copernicus_Tiles)))

            if a["properties"]["wwsos_min"]:
                print("fid:"+str(int(a["properties"]["fid"]))
                      +";"+str(a["properties"]["zoneID"])
                      +";"+area_str
                      +";WW"
                      +";"+swwsos
                      +";"+swweos
                      +";"+wwtrigweek
                      +";"+str(len(S2_Tiles))
                      +";"+str(nb_wws2)
                      +";"+str(len(L8_Tiles))
                      +";"+str(nb_wwl8)
                      +";"+str(nb_wws1)
                      +";"+str(len(SRTM_Tiles))
                      +";"+str(len(Copernicus_Tiles)))





if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
