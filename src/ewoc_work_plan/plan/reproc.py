import json
from dataship.dag.pid_to_ard import l2a_to_ard, l8_to_ard, to_ewoc_s1_ard
from pathlib import Path
from ewoc_work_plan.plan.utils import get_s3_client, write_plan


def reproc(bucket, in_plan, path=""):
    bucket_prods = fetch_bucket(bucket, path)
    search_json_and_dump(bucket_prods, in_plan, path)


def reproc_list(bucket, in_plans, path=""):
    bucket_prods = fetch_bucket(bucket, path)
    for in_plan in in_plans:
        search_json_and_dump(bucket_prods, in_plan, path)


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


def search_json_and_dump(bucket_prods, in_plan, path):
    ## Read the json plan
    bucket_prods = list(set(bucket_prods))
    with open(in_plan) as f:
        plan = json.load(f)
    out = {}
    for tile in plan:
        out[tile] = {}
        # S1
        prod_list = plan[tile]['SAR_PROC']['INPUTS']
        out[tile]['SAR_PROC'] = {}
        out[tile]['SAR_PROC']['INPUTS'] = []
        for prods in prod_list:
            product_is_found = False
            for prod in prods:
                prod_transformed1, prod_transformed2 = to_ewoc_s1_ard(Path(path), prod, tile)
                if (any(str(prod_transformed1) in elt for elt in bucket_prods) and
                       any(str(prod_transformed2) in elt for elt in bucket_prods)):
                    product_is_found = True
            if not product_is_found:
                print("lost")
                print(prods)
                out[tile]['SAR_PROC']['INPUTS'].append(prods)
        # S2
        S2_band_count = 10
        prods = plan[tile]['S2_PROC']['INPUTS']
        out[tile]['S2_PROC'] = {}
        out[tile]['S2_PROC']['INPUTS'] = []
        for prod in prods:
            prods_transformed = l2a_to_ard(prod, path)
            is_present = [any(str(prod_transformed).split("MSI")[0] in elt for elt in bucket_prods)
                          for prod_transformed in prods_transformed]
            if not(all(is_present)) or len(is_present) != S2_band_count:
                print("lost")
                print(prods)
                out[tile]['S2_PROC']['INPUTS'].append(prod)
                if len(is_present) != S2_band_count:
                    print("There is", len(is_present), "S2 products and there should be ",S2_band_count)

        # L8 TIRS
        L8_tirs_band_count = 2
        prod_list = plan[tile]['L8_TIRS']
        out[tile]['L8_TIRS'] = []
        for prods in prod_list:
            product_is_found = False
            for prod in prods:
                prod_transformed = l8_to_ard(prod, tile, path)
                if len([prod_path for prod_path in bucket_prods if prod_transformed in prod_path]
                       ) == L8_tirs_band_count:
                    product_is_found = True
            if not product_is_found:
                print("lost")
                print(prods)
                out[tile]['L8_TIRS'].append(prods)

    out_plan = in_plan[:-5] + "_reproc.json"
    write_plan(out, out_plan)
