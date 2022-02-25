import json
import logging
from pathlib import Path

from ewoc_dag.legacy.pid_to_ard import l2a_to_ard, l8_to_ard, to_ewoc_s1_ard
from ewoc_dag.legacy.s3man import get_s3_client


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def reproc(bucket, in_plan, path=""):
    bucket_prods = fetch_bucket(bucket, path)
    with open(in_plan, encoding="utf-8") as file:
        plan = json.load(file)
    return search_json_and_dump(bucket_prods, plan, path)


def reproc_wp(bucket, wp, path=""):
    bucket_prods = fetch_bucket(bucket, path)
    return search_json_and_dump(bucket_prods, wp, path)


def reproc_list(bucket, in_plans, path=""):
    bucket_prods = fetch_bucket(bucket, path)
    return_list = []
    for in_plan in in_plans:
        with open(in_plan, encoding="utf-8") as file:
            plan = json.load(file)
        return_list.append(search_json_and_dump(bucket_prods, plan, path))
    return return_list


def fetch_bucket(bucket, path):
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
            if key not in bucket_prods:
                bucket_prods.append(key)
            count += 1

    return bucket_prods


def search_json_and_dump(bucket_prods, plan, path):
    # Band counts
    l8_tirs_band_count = 2
    s2_band_count = 10

    # Read the json plan
    bucket_prods = list(set(bucket_prods))

    out_tiles = []
    for tile_plan in plan["tiles"]:
        out = tile_plan.copy()
        # S1
        prod_list = tile_plan["s1_ids"]
        tile_id = tile_plan["tile_id"]
        out["s1_ids"] = []
        for prods in prod_list:
            product_is_found = False
            for prod in prods:
                prod_transformed1, prod_transformed2 = to_ewoc_s1_ard(Path(path), prod, tile_id)
                if (any(str(prod_transformed1) in elt for elt in bucket_prods) and
                        any(str(prod_transformed2) in elt for elt in bucket_prods)):
                    product_is_found = True
            if not product_is_found:
                logger.info("lost")
                logger.info(prods)
                out["s1_ids"].append(prods)
        # S2
        prod_list = tile_plan["s2_ids"]
        out["s2_ids"] = []
        for prod in prods:
            prods_transformed = l2a_to_ard(prod, path)
            is_present = [any(str(prod_transformed).split("MSI")[0] in elt for elt in bucket_prods)
                          for prod_transformed in prods_transformed]
            if not(all(is_present)) or len(is_present) != s2_band_count:
                logger.info("lost")
                logger.info(prods)
                out["s2_ids"].append(prod)
                if len(is_present) != s2_band_count:
                    logger.info("There is %s S2 products and there should be %s", len(is_present),
                                                                                  s2_band_count)
        # L8 TIRS
        prod_list = tile_plan["l8_ids"]
        out["l8_ids"] = []
        for prods in prod_list:
            product_is_found = False
            for prod in prods:
                prod_transformed = l8_to_ard(prod, tile_id, path)
                if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]
                       ) == l8_tirs_band_count:
                    product_is_found = True
            if not product_is_found:
                logger.info("lost")
                logger.info(prods)
                out["l8_ids"].append(prods)
        out["s1_nb"] = len(out["s1_ids"])
        out["s2_nb"] = len(out["s2_ids"])
        out["l8_nb"] = len(out["l8_ids"])
        out_tiles.append(out)
    return out_tiles
