from eotile.eotile_module import main
from ewoc_work_plan.utils import eodag_prods
from datetime import datetime
import logging
from typing import List

_logger = logging.getLogger(__name__)


def get_e84_ids(s2_tile, start, end, creds, cloudcover=100):
    poly = main(s2_tile)[0]
    # Start search with element84 API
    s2_prods_e84 = eodag_prods(
        poly,
        start,
        end,
        "earth_search",
        "sentinel-s2-l2a-cogs",
        creds=creds,
        cloud_cover=cloudcover,
    )
    # Filter and Clean
    e84 = {}
    for el in s2_prods_e84:
        pid = el.properties["sentinel:product_id"]
        cc = el.properties["cloudCover"]
        date = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if s2_tile in pid:
            e84[pid] = {"cc": float(cc), "date": date, "provider": "aws_cog"}
    return e84


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
            creo[pid] = {"cc": float(cc), "date": date, "status": status, "provider": "creodias"}
    return creo


def get_s2_ids(s2_tile, provider, start, end, creds, cloudcover=100, level="L2A"):
    if provider == "aws_cog" and level == "L2A":
        return get_e84_ids(s2_tile, start, end, creds, cloudcover=cloudcover)
    elif provider == "aws":
        # implement aws synergize ids using eodag
        pass
    elif provider == "creodias":
        return get_creodias_ids(s2_tile, start, end, creds, cloudcover=cloudcover, level=level)
    else:
        _logger.warning("Cannot continue with provider %s and level %s" % (provider, level))


def merge_ids(ref, sec):
    fusion = {}
    for pid_r in ref:
        found = False
        for pid_s in sec:
            if ref[pid_r]["date"] == sec[pid_s]["date"]:
                found = True
                sec_id = pid_s
                _logger.info("Found match between ref and sec %s -- %s" % (pid_r, pid_s))
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
    # Filter produtcs by cloud cover
    cc_filter = [[s2_prds[prd]["provider"], prd] for prd in s2_prds if s2_prds[prd]["cc"] <= float(cloudcover)]
    _logger.info("Found %s products with cloudcover below %s%%", len(cc_filter), cloudcover)

    if len(cc_filter) >= min_nb_prods:
        _logger.info(
            "Found enough products below %s%% (%s, min nb prods: %s)",
            cloudcover, len(cc_filter), min_nb_prods
        )
        return cc_filter
    elif s2_prds:
        _logger.warning(
            "Not enough products below %s%%, full list of products (cloudcover 100%%) \
            will be used", cloudcover
        )
        return list(s2_prds.keys())
    else:
        _logger.error("Product list is empty!")
        return list(s2_prds.keys())


def cross_prodvider_ids(s2_tile, start, end, cloudcover_max, cloudcover_min, min_nb_prods, creds, providers,
                        strategy=None):
    if strategy is None:
        strategy = ["L2A", "L2A"]
    ref_provider = providers[0]
    ref_level = strategy[0]
    # If the two providers are the same with same product level, only one provider is used
    if len(set(providers)) == 1 and len(set(strategy)) == 1:
        _logger.info("One provider: %s will be used to get level: %s data" % (ref_provider, ref_level))
        ref = get_s2_ids(s2_tile, ref_provider, start, end, creds, cloudcover=cloudcover_max, level=ref_level)
        ref = {el: v for el, v in sorted(ref.items(), key=lambda item: item[1]["date"])}
        return get_best_prds(ref, cloudcover_min, min_nb_prods)
    else:
        sec_provider = providers[1]
        sec_level = strategy[1]
        _logger.info("Refrence provider: %s, level %s with secondary provider: %s, level %s" % (
            ref_provider, ref_level, sec_provider, sec_level))
        ref = get_s2_ids(s2_tile, ref_provider, start, end, creds, cloudcover=cloudcover_max, level=ref_level)
        sec = get_s2_ids(s2_tile, sec_provider, start, end, creds, cloudcover=cloudcover_max, level=sec_level)
        # Merge two dictionaries
        fusion = merge_ids(ref, sec)
        # Sort by date ascending
        fusion = {el: v for el, v in sorted(fusion.items(), key=lambda item: item[1]["date"])}
        # Return list of best products for a given cloud cover and yearly threshold
        fusion = get_best_prds(fusion, cloudcover_min, min_nb_prods)
        return fusion


if __name__ == "__main__":
    fusion = cross_prodvider_ids("31TCJ", "2018-01-01", "2021-01-01", cloudcover_max=100, cloudcover_min=95,
                                 min_nb_prods=50, creds="/eodag_config.yml",
                                 providers=["creodias", "aws_cog"], strategy=["L1C", "L2A"])
    for el in fusion:
        print(el)
