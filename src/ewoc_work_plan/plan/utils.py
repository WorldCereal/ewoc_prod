from eodag.api.core import EODataAccessGateway
import os
import boto3
import xml.etree.ElementTree as et
import logging
import json
import sys
import botocore

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
        # S1
        # TODO
        # S2_band_count = 2
        # prods = plan[tile]['SAR_PROC']['INPUTS']
        # S2
        S2_band_count = 10
        prods = plan[tile]['S2_PROC']['INPUTS']
        out[tile] = {}
        out[tile]['S2_PROC'] = {}
        out[tile]['S2_PROC']['INPUTS'] = []
        for prod in prods:
            prod_transformed = l2a_to_ard(prod)
            if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]) != S2_band_count:
                print("lost")
                print(prod_transformed)
                out[tile]['S2_PROC']['INPUTS'].append(prod_transformed)
        # L8
        L8_band_count = 2
        prod_list = plan[tile]['L8_TIRS']
        out[tile]['L8_TIRS'] = []
        for prods in prod_list:
            lost_prod_list = []
            for prod in prods:
                prod_transformed = l8_to_ard(prod, tile)
                if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]) != L8_band_count:
                    print("lost")
                    print(prod_transformed)
                    lost_prod_list.append(prod_transformed)
            out[tile]['L8_TIRS'].append(lost_prod_list)

    out_plan = in_plan[:-5] + "_reproc.json"
    write_plan(out, out_plan)


def l2a_to_ard(product_id):
    """
    Convert an L2A product into EWoC ARD format
    :param l2a_folder: L2A SAFE folder
    :param work_dir: Output directory
    """

    platform = product_id.split("_")[0]
    processing_level = product_id.split("_")[1]
    date = product_id.split("_")[2]
    year = date[:4]
    # Get tile id , remove the T in the beginning
    tile_id = product_id.split("_")[5][1:]
    unique_id = "".join(product_id.split("_")[3:6])
    folder_st = os.path.join(
        "OPTICAL",
        tile_id[:2],
        tile_id[2],
        tile_id[3:],
        year,
        date.split("T")[0],
    )
    dir_name = f"{platform}_{processing_level}_{date}_{unique_id}_{tile_id}"
    ard_folder = os.path.join(folder_st, dir_name)
    return ard_folder


def l8_to_ard(key,s2_tile,out_dir=None):
    product_id = os.path.split(key)[-1]
    platform = product_id.split('_')[0]
    processing_level = product_id.split('_')[1]
    date = product_id.split('_')[3]
    year = date[:4]
    # Get tile id , remove the T in the beginning
    tile_id = s2_tile
    unique_id = f"{product_id.split('_')[2]}{product_id.split('_')[5]}{product_id.split('_')[6]}"
    folder_st = os.path.join('TIR', tile_id[:2], tile_id[2], tile_id[3:], year,date.split('T')[0])
    dir_name = f"{platform}_{processing_level}_{date}_{unique_id}_{tile_id}"
    out_name = f"{platform}_{processing_level}_{date}_{unique_id}_{tile_id}"
    raster_fn = os.path.join(folder_st, dir_name, out_name)
    if out_dir is not None:
        tmp = os.path.join(out_dir, folder_st, dir_name)
        if not os.path.exists(tmp):
            os.makedirs(tmp)
    return raster_fn