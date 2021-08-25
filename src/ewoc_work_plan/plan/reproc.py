import json
from dataship.dag.pid_to_ard import l2a_to_ard, l8_to_ard, to_ewoc_s1_ard
from pathlib import Path
from ewoc_work_plan.plan.utils import get_s3_client, write_plan


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
            if key not in bucket_prods:
                bucket_prods.append(key)
            count += 1

    print(count)

    ## Read the json plan
    bucket_prods = list(set(bucket_prods))
    with open(in_plan) as f:
        plan = json.load(f)
    out = {}
    print(bucket_prods)
    for tile in plan:
        out[tile] = {}
        # S1
        prod_list = plan[tile]['SAR_PROC']['INPUTS']
        out[tile]['SAR_PROC'] = {}
        out[tile]['SAR_PROC']['INPUTS'] = []
        for prods in prod_list:
            lost_prod_list = []
            for prod in prods:
                prod_transformed1, prod_transformed2 = to_ewoc_s1_ard(Path(path), prod, tile)
                if not(any(str(prod_transformed1) in elt for elt in bucket_prods) and
                       any(str(prod_transformed2) in elt for elt in bucket_prods)):
                    print("lost")
                    print(prod_transformed1, prod_transformed2)
                    lost_prod_list.append(prod)
            out[tile]['SAR_PROC']['INPUTS'].append(lost_prod_list)
        # S2
        S2_band_count = 10
        prods = plan[tile]['S2_PROC']['INPUTS']
        out[tile]['S2_PROC'] = {}
        out[tile]['S2_PROC']['INPUTS'] = []
        for prod in prods:
            prods_transformed = l2a_to_ard(prod, path)
            is_present = [any([prod_path for prod_path in bucket_prods if prod_transformed in prod_path])
                          for prod_transformed in prods_transformed]
            if all(is_present) and len(is_present) == S2_band_count:
                print("lost")
                print(prods_transformed, is_present)
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
