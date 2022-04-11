import logging
from datetime import datetime
from typing import List
import re
import boto3
from botocore.handlers import disable_signing

from eotile.eotile_module import main
from ewoc_dag.bucket.aws import AWSS2L2ABucket, AWSS2L2ACOGSBucket
from ewoc_dag.eo_prd_id.s2_prd_id import S2PrdIdInfo

from ewoc_work_plan.utils import eodag_prods, remove_duplicates

_logger = logging.getLogger(__name__)

def test_pattern(pattern, mylist):
    # if re.search(r'%s' % pattern, "".join(mylist)) is not None:
    if re.search(pattern, "".join(mylist)) is not None:
        return True
    else:
        return False

def check_bucket_e84(pid, bucket, prefix):
    s3 = boto3.resource('s3')
    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
    my_bucket = s3.Bucket(bucket)

    _logger.debug('Search for product %s', pid)
    path1 = pid.split('_')[-2][1:3]
    path2 = pid.split('_')[-2][3]
    path3 = pid.split('_')[-2][4:]
    path4 = pid.split('_')[-1][:4]
    path5 = pid.split('_')[-1][4:6].strip("0")
    path6 = pid.split('_')[0]
    path7 = pid.split('_')[5][1:]
    path8 = pid.split('_')[-1][:8]
    prd_prefix = f'{prefix}/{path1}/{path2}/{path3}/{path4}/{path5}/'
    prd_pattern = f'{path6}_{path7}_{path8}'

    result = my_bucket.meta.client.list_objects(Bucket=bucket,
                                                Prefix=prd_prefix,
                                                Delimiter='/')
    s2_prods_e84_list = []
    for res in result.get('CommonPrefixes'):
        _logger.debug(res.get('Prefix'))
        s2_prods_e84_list.append(res.get('Prefix'))

    if test_pattern(prd_pattern, s2_prods_e84_list):
        _logger.debug('Product %s exists in the bucket \n', prd_pattern)
        return True
    else:
        _logger.debug('Product %s is missing \n', prd_pattern)
        return False

def get_e84_ids(s2_tile, start, end, creds, cloudcover=100, level="L2A"):
    poly = main(s2_tile)[0]

    # if level == "L1C":
    #     product_type = "S2_MSI_L1C"
    # elif level == "L2A":
    #     product_type = "S2_MSI_L2A"

    # Start search with element84 API
    s2_prods_e84_all = eodag_prods(
        poly,
        start,
        end,
        "earth_search",
        "sentinel-s2-l2a",
        creds=creds,
        cloud_cover=cloudcover,
    )
    # Check bucket
    # s2_prods_e84 = s2_prods_e84_all
    s2_prods_e84 = []
    for el in s2_prods_e84_all:
        pid = el.properties["sentinel:product_id"]

        s2_prd_info = S2PrdIdInfo(pid)
        prefix_components = [
            "sentinel-s2-l2a",
            "tiles",
            s2_prd_info.tile_id[0:2].lstrip("0"),
            s2_prd_info.tile_id[2],
            s2_prd_info.tile_id[3:5],
            str(s2_prd_info.datatake_sensing_start_time.date().year),
            str(s2_prd_info.datatake_sensing_start_time.date().month).lstrip("0"),
            el.properties["id"]
        ]
        prd_prefix = "/".join(prefix_components) + "/"
        # prd_prefix = "/".join(prefix_components) + "/" + "B12.tif"
        my_bucket = AWSS2L2ABucket()
        # if check_bucket_e84(pid, bucket='sentinel', prefix='sentinel-s2-l2a/tiles/'):
            # s2_prods_e84.append(el)
        if my_bucket._check_product(prefix=prd_prefix):
            s2_prods_e84.append(el)
    # Filter and Clean
    e84 = {}
    for el in s2_prods_e84:
        pid = el.properties["sentinel:product_id"]
        cc = el.properties["cloudCover"]
        date = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if s2_tile in pid:
            e84[pid] = {"cc": float(cc), "date": date, "provider": "aws", "level": level}
    return e84

def get_e84_cogs_ids(s2_tile, start, end, creds, cloudcover=100, level="L2A"):
    poly = main(s2_tile)[0]
    # Start search with element84 API
    s2_prods_e84_cogs_all = eodag_prods(
        poly,
        start,
        end,
        "earth_search",
        "sentinel-s2-l2a-cogs",
        creds=creds,
        cloud_cover=cloudcover,
    )
    # Check bucket
    s2_prods_e84_cogs = []
    for el in s2_prods_e84_cogs_all:
        pid = el.properties["sentinel:product_id"]

        s2_prd_info = S2PrdIdInfo(pid)
        prefix_components = [
            "sentinel-s2-l2a-cogs",
            s2_prd_info.tile_id[0:2].lstrip("0"),
            s2_prd_info.tile_id[2],
            s2_prd_info.tile_id[3:5],
            str(s2_prd_info.datatake_sensing_start_time.date().year),
            str(s2_prd_info.datatake_sensing_start_time.date().month).lstrip("0"),
            el.properties["id"]
        ]
        prd_prefix = "/".join(prefix_components) + "/" 
        # prd_prefix = "/".join(prefix_components) + "/" + "B12.tif"
        my_bucket = AWSS2L2ACOGSBucket()
        # if check_bucket_e84(pid, bucket='sentinel-cogs', prefix='sentinel-s2-l2a-cogs'):
            # s2_prods_e84_cogs.append(el)
        if my_bucket._check_product(prefix=prd_prefix):
            s2_prods_e84_cogs.append(el)
    # Filter and Clean
    e84_cogs = {}
    for el in s2_prods_e84_cogs:
        pid = el.properties["sentinel:product_id"]
        cc = el.properties["cloudCover"]
        date = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if s2_tile in pid:
            e84_cogs[pid] = {"cc": float(cc), "date": date, "provider": "aws_cog", "level": level}
    return e84_cogs


def get_creodias_ids(s2_tile, start, end, creds, cloudcover=100, level="L2A"):
    poly = main(s2_tile)[0]
    # Start search with creodias finder API
    if level == "L1C":
        product_type = "S2_MSI_L1C"
    elif level == "L2A":
        product_type = "S2_MSI_L2A"

    s2_prods_creo = eodag_prods(
        poly,
        start,
        end,
        "creodias",
        product_type=product_type,
        creds=creds,
        cloud_cover=cloudcover,
    )
    # Filter and Clean
    creo = {}
    for el in s2_prods_creo:
        pid = el.properties["title"]
        cc = el.properties["cloudCover"]
        status = el.properties["storageStatus"]
        date = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if s2_tile in pid:
            creo[pid] = {
                "cc": float(cc),
                "date": date,
                "status": status,
                "provider": "creodias",
                "level": level
            }
    return creo


def get_s2_ids(s2_tile, provider, start, end, creds, cloudcover=100, level="L2A"):
    if provider == "aws_cog" and level == "L2A":
        return get_e84_cogs_ids(s2_tile, start, end, creds, cloudcover=cloudcover, level=level)
    elif provider == "aws" and level == "L2A":
        return get_e84_ids(s2_tile, start, end, creds, cloudcover=cloudcover, level=level)
    elif provider == "creodias":
        return get_creodias_ids(
            s2_tile, start, end, creds, cloudcover=cloudcover, level=level
        )
    else:
        _logger.warning("Cannot continue with provider %s and level %s", provider, level
        )


def merge_ids(ref, sec):
    fusion = {}
    for pid_r in ref:
        found = False
        for pid_s in sec:
            if ref[pid_r]["date"] == sec[pid_s]["date"] and ref[pid_r]["level"] != sec[pid_s]["level"]:
                found = True
                sec_id = pid_s
                _logger.info("Found match between ref and sec %s -- %s", pid_r, pid_s)
        if found:
            fusion[sec_id] = sec[sec_id]
        else:
            fusion[pid_r] = ref[pid_r]
    return fusion


def get_best_prds(s2_prds: dict, cloudcover: float, min_nb_prods: int) -> List:
    # Get number of months from sorted dict
    last_date = s2_prds[list(s2_prds.keys())[-1]]["date"]
    first_date = s2_prds[list((s2_prds.keys()))[0]]["date"]
    n_months = (
        (last_date.year - first_date.year) * 12 + last_date.month - first_date.month
    )
    min_nb_prods = round((n_months * min_nb_prods) / 12)
    # Remove duplicates
    s2_prds_set = remove_duplicates(list(s2_prds.keys()))
    # Filter produtcs by cloud cover
    cc_filter = [
        [s2_prds[prd]["provider"], prd]
        for prd in s2_prds_set
        if s2_prds[prd]["cc"] <= float(cloudcover)
    ]
    _logger.info(
        "Found %s products with cloudcover below %s%%", len(cc_filter), cloudcover
    )

    if len(cc_filter) >= min_nb_prods:
        _logger.info(
            "Found enough products below %s%% (%s, min nb prods: %s)",
            cloudcover,
            len(cc_filter),
            min_nb_prods,
        )
        return cc_filter
    elif s2_prds:
        _logger.warning(
            "Not enough products below %s%%, full list of products (cloudcover 100%%) \
            will be used",
            cloudcover,
        )
        return list(s2_prds.keys())
    else:
        _logger.error("Product list is empty!")
        return list(s2_prds.keys())


def run_multiple_cross_provider(
    s2_tile,
    start,
    end,
    cloudcover_max,
    cloudcover_min,
    min_nb_prods,
    creds,
    providers,
    strategy=None,
):
    if len(providers) != len(strategy):
        _logger.error("Number of providers must match number of strategies")
    if strategy is None:
        strategy = ["L2A"] * len(providers)

    # Initilization
    ref = get_s2_ids(
        s2_tile,
        providers[0],
        start,
        end,
        creds,
        cloudcover=cloudcover_max,
        level=strategy[0],
    )

    # print('Number of %s products for %s = %s' % (strategy[0], providers[0], len(ref)))
    _logger.debug('Number of %s products for %s = %s', strategy[0], providers[0], len(ref))

    nb_tests = len(providers)-1

    while nb_tests>0:

        print(providers, strategy)
        # _logger.debug(providers, strategy)

        ref_provider =  providers[0]
        ref_level = strategy[0]
        sec_provider =  providers[1]
        sec_level = strategy[1]

        if ref is not None:  #except for the first iteration, ref_level and ref_provider is a mix of values
            # print(f'Number of reference products = {len(ref)}')
            _logger.debug('Number of reference products = %s', len(ref))
        else:
            # print('Number of reference products = 0')
            _logger.debug('Number of reference products = 0')

        # If the two providers are the same with same product level, only one provider is used
        if (ref_provider == sec_provider) and (ref_level == sec_level):
            _logger.info(
                "One provider: %s will be used to get level: %s data",
                ref_provider, ref_level
            )
        else:
            _logger.info(
                "Reference provider: %s, level %s with secondary provider: %s, level %s",
                ref_provider, ref_level, sec_provider, sec_level
            )
            ref = cross_provider_ids(
                    s2_tile,
                    start,
                    end,
                    cloudcover_max,
                    creds,
                    ref,
                    sec_provider,
                    sec_level,
                )
        nb_tests -= 1
        providers = providers[1:]
        strategy = strategy[1:]

    # print(f'Number of prd before cc filter = {len(ref)}')
    _logger.debug('Number of prd before cc filter= %s', len(ref))
    res_prd = format_results(ref, cloudcover_min, min_nb_prods)
    # print(f'Number of prd after cc filter = {len(res_prd)}')
    _logger.debug('Number of prd after cc filter= %s', len(res_prd))
    return res_prd


def cross_provider_ids(
    s2_tile,
    start,
    end,
    cloudcover_max,
    creds,
    ref,
    sec_provider,
    sec_level,
):
    sec = get_s2_ids(
        s2_tile,
        sec_provider,
        start,
        end,
        creds,
        cloudcover=cloudcover_max,
        level=sec_level,
    )

    if sec is not None :
        # print(f'Number of {sec_level} products for {sec_provider} = {len(sec)}')
        _logger.debug('Number of %s products for %s = %s', sec_level, sec_provider, len(sec))
    else:
        # print(f'Number of {sec_level} products for {sec_provider} = 0')
        _logger.debug('Number of %s products for %s = 0', sec_level, sec_provider)

    # Merge two dictionaries
    fusion = merge_ids(ref, sec)
    return fusion


def format_results(val, cloudcover_min, min_nb_prods):
    # Sort by date ascending
    val = {el: v for el, v in sorted(val.items(), key=lambda item: item[1]["date"])}
    return get_best_prds(val, cloudcover_min, min_nb_prods)


if __name__ == "__main__":
    fusion = run_multiple_cross_provider(
        "35LMK",
        "2020-08-03",
        "2020-08-04",
        cloudcover_max=100,
        cloudcover_min=95,
        min_nb_prods=50,
        creds="../../../eodag_config.yml",
        providers=["creodias", "creodias", "aws_cog", "aws"],
        strategy=["L1C", "L2A", "L2A", "L2A"],
    )
    for el in fusion:
        print(el)
