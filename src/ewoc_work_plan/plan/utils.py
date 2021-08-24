from eodag.api.core import EODataAccessGateway
import os
import boto3
import xml.etree.ElementTree as et
import logging
import json
import botocore
from dataship.dag.pid_to_ard import l2a_to_ard, l8_to_ard, to_ewoc_s1_ard

def eodag_prods(df,start_date,end_date,provider,product_type,creds,cloudCover=None):
    dag = EODataAccessGateway(creds)
    dag.set_preferred_provider(provider)
    print(provider)
    poly = df.geometry[0].to_wkt()
    max_items = 2000
    if cloudCover is None:
        products, est = dag.search(productType=product_type, start=start_date, end=end_date, geom=poly, items_per_page=max_items)
    else:
        products, est = dag.search(productType=product_type, start=start_date, end=end_date, geom=poly,
                                   items_per_page=max_items, cloudCover=cloudCover)
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
        path = product.assets['B5']['href'].split('/')[8]
        row = product.assets['B5']['href'].split('/')[9]
    return path, row

def get_s3_client():
    # S3 function from argo workflow coded by Alex G.
    client_config = botocore.config.Config(
        max_pool_connections=100,
    )
    s3_client = None
    if "amazon" in os.environ["S3_ENDPOINT"]:
        s3_client = boto3.client('s3',
                                 aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                                 aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
                                 region_name="eu-central-1",
                                 config=client_config)
    if "cloudferro" in os.environ["S3_ENDPOINT"]:
        s3_client = boto3.client('s3',
                                 aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                                 aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
                                 endpoint_url=os.environ["S3_ENDPOINT"],
                                 config=client_config)

    return s3_client


def write_plan(plan, out_file):
    # Write the json
    with open(out_file, "w") as fp:
        json.dump(plan, fp, indent=4)


def reproc(bucket, in_plan, path=""):
    s3c = get_s3_client()
    paginator = s3c.get_paginator("list_objects")

    kwargs = {'Bucket': bucket, "Prefix": path}

    count = 0
    bucket_prods = []
    for page in paginator.paginate(**kwargs):
        try:
            contents = page["Contents"]
        except KeyError:
            break
        for obj in contents:
            key = obj["Key"]
            sub_k = key.split('/')[8]
            sub_k = sub_k.split('_')
            prod_tr = sub_k[-1] + '_' + sub_k[2]
            if not prod_tr in bucket_prods:
                bucket_prods.append(prod_tr)
            count += 1

    print(count)

    ## Read the json plan
    bucket_prods = list(set(bucket_prods))
    with open(in_plan) as f:
        plan = json.load(f)
    out = {}
    for tile in plan:
        out[tile] = {}
        # S1
        # TODO
        # S2_band_count = 2
        # prods = plan[tile]['SAR_PROC']['INPUTS']
        # S2
        S2_band_count = 10
        prods = plan[tile]['S2_PROC']['INPUTS']
        out[tile]['S2_PROC'] = {}
        out[tile]['S2_PROC']['INPUTS'] = []
        for prod in prods:
            prod_transformed = l2a_to_ard(prod)
            if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]) != S2_band_count:
                print("lost")
                print(prod_transformed)
                out[tile]['S2_PROC']['INPUTS'].append(prod)
        # L8 TIRS
        L8_tirs_band_count = 2
        prod_list = plan[tile]['L8_TIRS']
        out[tile]['L8_TIRS'] = []
        for prods in prod_list:
            lost_prod_list = []
            for prod in prods:
                prod_transformed = l8_to_ard(prod, tile)
                if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]) != L8_tirs_band_count:
                    print("lost")
                    print(prod_transformed)
                    lost_prod_list.append(prod)
            out[tile]['L8_TIRS'].append(lost_prod_list)

    out_plan = in_plan[:-5] + "_reproc.json"
    write_plan(out, out_plan)

