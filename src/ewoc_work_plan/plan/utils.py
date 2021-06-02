from eodag.api.core import EODataAccessGateway
import os
import boto3
import xml.etree.ElementTree as et
import logging

def eodag_prods(df,start_date,end_date,provider,product_type,creds,cloudCover=None):
    dag = EODataAccessGateway(creds)
    dag.update_providers_config("""
        creodias:
            products:
                L8_OLI_TIRS_C1L1:
                    collection: Landsat8
        """)
    dag.set_preferred_provider(provider)
    bbox = df.total_bounds
    extent = {'lonmin': bbox[0], 'latmin': bbox[1], 'lonmax': bbox[2], 'latmax': bbox[3]}

    max_items = 2000
    if cloudCover is None:
        products, est = dag.search(productType=product_type, start=start_date, end=end_date, geom=extent, items_per_page=max_items)
    else:
        products, est = dag.search(productType=product_type, start=start_date, end=end_date, geom=extent,
                                   items_per_page=max_items, cloudCover=cloudCover)
    return products

def is_ascending(s1_product,provider):
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
                return True
            else:
                return False
        except RuntimeError:
            logging.ERROR('Could not determine orbit direction')

def get_path_row(product,provider):
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
        path = product.assets['B5']['href'].split('/')[5]
        row = product.assets['B5']['href'].split('/')[6]
    return path, row