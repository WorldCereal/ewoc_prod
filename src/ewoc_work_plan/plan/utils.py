import os
import json
import logging
import xml.etree.ElementTree as et

import boto3
from eodag.api.core import EODataAccessGateway


_logger = logging.getLogger(__name__)

def eodag_prods(df,start_date,end_date,provider,product_type,creds,cloudCover=None):
    dag = EODataAccessGateway(user_conf_file_path=creds)
    dag.set_preferred_provider(provider)
    poly = df.geometry[0].to_wkt()
    max_items = 2000
    if cloudCover is None:
        products, __unused = dag.search( productType=product_type,
                                    start=start_date, end=end_date,
                                    geom=poly, items_per_page=max_items)
    else:
        products, __unused = dag.search( productType=product_type,
                                    start=start_date, end=end_date, geom=poly,
                                     items_per_page=max_items,
                                     cloudCover=cloudCover)
    return products


def is_descending(s1_product,provider):
    if provider.lower() == 'creodias':
        if s1_product.properties['orbitDirection'] == "descending":
            return True
    else:
        manifest_key = os.path.split(s1_product.assets['vv']['href'])[0].replace('measurement', 'manifest.safe')
        bucket = "sentinel-s1-l1c"
        key = manifest_key.replace("s3://sentinel-s1-l1c/","")
        s3 = boto3.client('s3')
        try:
            obj = s3.get_object(Bucket=bucket,Key=key,RequestPayer='requester')
            xml_string = obj['Body'].read()
            tree = et.ElementTree(et.fromstring(xml_string))
            root = tree.getroot()
            orbit = root.iter("{http://www.esa.int/safe/sentinel-1.0/sentinel-1}pass")
            orbit= list(orbit)[0]
            if orbit.text == "ASCENDING":
                return False
            else:
                return True
        except RuntimeError:
            _logger.error('Could not determine orbit direction')


def get_path_row(product, provider):
    path = ""
    row  = ""
    if provider.lower() == "creodias":
        path = str(product.properties['path'])
        row = str(product.properties['row'])
        if len(path) == 2:
            path = "0"+path
        if len(row) == 2:
            row = "0"+row
    elif provider.lower() == "astraea_eod":
        path = product.assets['B5']['href'].split('/')[8]
        row = product.assets['B5']['href'].split('/')[9]
    return path, row


def write_plan(plan, out_file):
    # Write the json
    with open(out_file, "w") as fp:
        json.dump(plan, fp, indent=4)
