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
from typing import List
from osgeo import ogr, osr


def main(arguments: List[str])->None:
    '''Entrypoint'''

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-a',
                        '--aez',
                        help="aez.geojson file")
    parser.add_argument('-t',
                        '--s2tiles',
                        help="s2tile_selection.geojson file")
    parser.add_argument('-o',
                        '--out',
                        help="s2tile_selection_aez.geojson, the s2tile file with aez information")
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


    ogr_types = {'Integer': ogr.OFTInteger, 'Real': ogr.OFTReal, 'String': ogr.OFTString}

    # Load GeoJSON file containing AEZs
    driver = ogr.GetDriverByName('GeoJSON')
    data_source1 = driver.Open(args.aez, 1)
    aez_layer = data_source1.GetLayer()
    nb_aez = len(aez_layer)
    logging.info('number of aez = %s', str(nb_aez))

    # Load GeoJSON file containing S2 tiles
    data_source2 = driver.Open(args.s2tiles, 1)
    s2tiles_layer = data_source2.GetLayer()
    nb_s2tiles = len(s2tiles_layer)
    logging.info('number of s2tiles = %s', str(nb_s2tiles))

    # Exclude tiles that do not contain crop
    s2tiles_layer.SetAttributeFilter("include = 1")
    # s2tiles_layer.SetAttributeFilter("tile = '32UNC'")
    nb_s2tiles = len(s2tiles_layer)
    logging.info('number of s2tiles included = %s', str(nb_s2tiles))

    # Create output GeoJSON file
    data_dest = driver.CreateDataSource(args.out)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    out_layer = data_dest.CreateLayer("s2tiles_aez", srs, ogr.wkbMultiPolygon)

    # Copy s2tiles file columns names
    defn = s2tiles_layer.GetLayerDefn()
    for i in range(defn.GetFieldCount()):
        field_name =  defn.GetFieldDefn(i).GetName()
        field_type_code = defn.GetFieldDefn(i).GetType()
        field_type = defn.GetFieldDefn(i).GetFieldTypeName(field_type_code)
        out_layer.CreateField(ogr.FieldDefn(field_name, ogr_types[field_type]))

    # Copy aez file columns names
    defn = aez_layer.GetLayerDefn()
    for i in range(defn.GetFieldCount()):
        field_name =  defn.GetFieldDefn(i).GetName()
        field_type_code = defn.GetFieldDefn(i).GetType()
        field_type = defn.GetFieldDefn(i).GetFieldTypeName(field_type_code)
        out_layer.CreateField(ogr.FieldDefn(field_name, ogr_types[field_type]))

    # Loop on s2 tiles
    for tile in s2tiles_layer:
        tile_name = tile.GetField("tile")

        # Get tile geometry
        geom_tile = tile.GetGeometryRef()
        geom_tile = str(geom_tile)
        geometry_tile = ogr.CreateGeometryFromWkt(geom_tile)

        # Apply spatial filter
        aez_layer.SetSpatialFilter(geometry_tile)

        # Get the AEZ that intersects the most (= aez_selected)
        aez_selected = None
        aez_overlap = 0

        if len(aez_layer) == 0:
            logging.info('WARNING : Tile %s does not overlap any AEZ', tile_name)
        elif len(aez_layer)==1:
            for aez in aez_layer:
                aez_selected = aez.GetField("zoneID")
                aez_overlap = 100
        elif len(aez_layer)>1:
            for aez in aez_layer:

                # Get aez geometry
                geom_aez = aez.GetGeometryRef()
                geom_aez = str(geom_aez)
                geometry_aez = ogr.CreateGeometryFromWkt(geom_aez)

                # Calcul tile/aez overlap
                overlap = geometry_tile.Intersection(geometry_aez)
                overlap_area = int(overlap.GetArea()*100/geometry_tile.GetArea())
                # logging.info("AEZ %s have an overlap of %s%%", str(aez_id), str(overlap_area))

                # Keep the aez that intersects the most
                if overlap_area > aez_overlap:
                    aez_selected = aez.GetField("zoneID")
                    aez_overlap = overlap_area

        logging.info('Tile %s : %s AEZ (n°%s is %s%%)',
                    tile_name, len(aez_layer), str(int(aez_selected)), aez_overlap)

        aez_layer.SetSpatialFilter(None)

        # Add new tile feature with aez information in output file
        aez_layer.SetAttributeFilter(f"zoneID = '{aez_selected}'")

        feature = ogr.Feature(out_layer.GetLayerDefn())
        feature.SetGeometry(tile.GetGeometryRef())
        defn = s2tiles_layer.GetLayerDefn()
        for i in range(defn.GetFieldCount()):
            field_name =  defn.GetFieldDefn(i).GetName()
            feature.SetField(field_name, tile.GetField(field_name))

        for aez in aez_layer:
            defn = aez_layer.GetLayerDefn()
            for i in range(defn.GetFieldCount()):
                field_name =  defn.GetFieldDefn(i).GetName()
                feature.SetField(field_name, aez.GetField(field_name))

        out_layer.CreateFeature(feature)
        feature = None
        aez_layer.SetAttributeFilter(None)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
