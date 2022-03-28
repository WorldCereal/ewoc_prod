#!/usr/bin/env python3
'''
:author: Aurélien Bricier <aurelien.bricier@csgroup.eu>
:organization: CS Group
:copyright: 2021 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2021
'''

import sys
import json

import logging
import argparse
from osgeo import ogr
from osgeo import osr

from eotile import eotile_module
from eodag.utils.logging import setup_logging
from eodag.api.core import EODataAccessGateway


def filter_tiles(s2_tiles, s2_exclusion_json):
    out_s2tiles = []

    for tile in s2_tiles.iterrows():
        for feature in s2_exclusion_json['features']:
            if feature['properties']['tile'] == tile[1].id:
                if feature['properties']['include']:
                    out_s2tiles.append(tile[1].id)
                break

    logging.debug("Before filtering : %s S2 tiles / After filtering : %s S2 tiles",
                 str(len(s2_tiles)),
                 str(len(out_s2tiles)))

    return out_s2tiles


def main(arguments):
    '''Entrypoint'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-a',
                        '--aez',
                        help="aez.geojson file")
    parser.add_argument('-e',
                        '--exclusion',
                        help="s2tile_selection.geojson file, the s2 tile exclusion list")
    parser.add_argument('-o',
                        '--out',
                        help="sys_aez.geojson, the formated aez file for the system")
    parser.add_argument('--debug',
                        action='store_true',
                        help='Activate Debug Mode')
    args = parser.parse_args(arguments)

    logging_format = '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s'
    if args.debug is True:
        logging.basicConfig(stream=sys.stdout,
                            level=logging.DEBUG, format=logging_format)
    else:
        logging.basicConfig(stream=sys.stdout,
                            level=logging.INFO, format=logging_format)

    # load GeoJSON file containing AEZs
    driver = ogr.GetDriverByName('GeoJSON')
    data_source = driver.Open(args.aez, 1)
    aez_layer = data_source.GetLayer()

    # load exclusion list
    with open(args.exclusion) as excl:
        s2_exclusion_json = json.load(excl)
        logging.debug("Loading %s",
                      args.exclusion)

    # eodag
    setup_logging(verbose=0)
    dag = EODataAccessGateway()
    dag.set_preferred_provider("astraea_eod")

    # Create custom output GeoJSON file
    data_dest = driver.CreateDataSource(args.out)
    srs =  osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    out_layer = data_dest.CreateLayer("aez", srs, ogr.wkbMultiPolygon)

    out_layer.CreateField(ogr.FieldDefn('fid', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('groupID', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('zoneID', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('tiles', ogr.OFTString))
    out_layer.CreateField(ogr.FieldDefn('L8', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('m1sos_min', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('m1eos_max', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('m2sos_min', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('m2eos_max', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('wwsos_min', ogr.OFTInteger))
    out_layer.CreateField(ogr.FieldDefn('wweos_max', ogr.OFTInteger))


    for feat in aez_layer:

        [s2_tiles, l8_tiles, srtm_tiles, copernicus_tiles] = eotile_module.main(feat.GetGeometryRef().ExportToWkt())
        filtered_s2_tiles = filter_tiles(s2_tiles, s2_exclusion_json)

        if len(filtered_s2_tiles):
            logging.info("Adding AEZ %s, %s S2 tiles within the AEZ",
                          str(int(feat.GetField("zoneID"))),
                          str(len(filtered_s2_tiles)))

            feature = ogr.Feature(out_layer.GetLayerDefn())
            feature.SetGeometry(feat.GetGeometryRef())
            feature.SetField("fid", feat.GetField("fid"))
            feature.SetField("groupID", feat.GetField("groupID"))
            feature.SetField("zoneID", feat.GetField("zoneID"))
            feature.SetField("tiles", ','.join(filtered_s2_tiles))
            feature.SetField("L8", feat.GetField("L8"))
            feature.SetField("m1sos_min", feat.GetField("m1sos_min"))
            feature.SetField("m1eos_max", feat.GetField("m1eos_max"))
            feature.SetField("m2sos_min", feat.GetField("m2sos_min"))
            feature.SetField("m2eos_max", feat.GetField("m2eos_max"))
            feature.SetField("wwsos_min", feat.GetField("wwsos_min"))
            feature.SetField("wweos_max", feat.GetField("wweos_max"))

            out_layer.CreateFeature(feature)

            feature = None
        else:
            logging.info("Dropping AEZ %s, no S2 tile within the AEZ",
                          str(int(feat.GetField("zoneID"))))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
