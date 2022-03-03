import logging
import os
import re
import xml.etree.ElementTree as et
from datetime import datetime, timedelta
from typing import List

import boto3
from eodag.api.core import EODataAccessGateway
from eotile import eotile_module
from shapely.wkt import dumps

_logger = logging.getLogger(__name__)


def set_logger(verbose_v):
    """
    Set the logger level
    :param loglevel:
    :return:
    """
    v_to_level = {0: "WARNING", 1: "INFO", 2: "DEBUG"}
    loglevel = v_to_level[verbose_v]
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    formatter = logging.Formatter(logformat, datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger().handlers[0].setFormatter(formatter)
    logging.getLogger().setLevel(loglevel)


def eodag_prods(
    df, start_date, end_date, provider, product_type, creds, cloud_cover=None
):
    dag = EODataAccessGateway(user_conf_file_path=creds)
    dag.set_preferred_provider(provider)
    poly = dumps(df.geometry[0])
    max_items = 500
    if cloud_cover is None:
        products = dag.search_all(
            productType=product_type,
            start=start_date,
            end=end_date,
            geom=poly,
            items_per_page=max_items,
        )
    elif product_type == "LANDSAT_C2L2_SR":
        products = dag.search_all(
            productType=product_type,
            geom=poly,
            start=start_date,
            end=end_date,
            platformSerialIdentifier="LANDSAT_8",
            cloudCover=cloud_cover,
        )

    else:
        products = dag.search_all(
            productType=product_type,
            start=start_date,
            end=end_date,
            geom=poly,
            items_per_page=max_items,
            cloudCover=cloud_cover,
        )

    return products


def is_descending(s1_product, provider):
    if provider.lower() == "creodias":
        if s1_product.properties["orbitDirection"] == "descending":
            return True
    else:
        manifest_key = os.path.split(s1_product.assets["vv"]["href"])[0].replace(
            "measurement", "manifest.safe"
        )
        bucket = "sentinel-s1-l1c"
        key = manifest_key.replace("s3://sentinel-s1-l1c/", "")
        s3_client = boto3.client("s3")
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=key, RequestPayer="requester")
            xml_string = obj["Body"].read()
            tree = et.ElementTree(et.fromstring(xml_string))
            root = tree.getroot()
            orbit = root.iter("{http://www.esa.int/safe/sentinel-1.0/sentinel-1}pass")
            orbit = list(orbit)[0]
            if orbit.text == "ASCENDING":
                return False
            else:
                return True
        except RuntimeError:
            _logger.error("Could not determine orbit direction")


def get_path_row(product, provider):
    if provider.lower() == "creodias":
        path = str(product.properties["path"])
        row = str(product.properties["row"])
        if len(path) == 2:
            path = "0" + path
        if len(row) == 2:
            row = "0" + row
    elif provider.lower() == "astraea_eod":
        path = product.assets["B5"]["href"].split("/")[8]
        row = product.assets["B5"]["href"].split("/")[9]
    elif provider.lower() == "usgs_satapi_aws":
        path = product.assets["blue"]["href"].split("/")[8]
        row = product.assets["blue"]["href"].split("/")[9]
    else:
        raise NotImplementedError(f"Provider {provider} not implemented yet ")
    return path, row


def greatest_timedelta(
    EOProduct_list: list, start_date: str, end_date: str, date_format: str = "%Y%m%d"
) -> timedelta:
    """
    Computes the greatest time delta from a list of EOdag products

    :param EOProduct_list: List of EOdag products to analyse
    :param date_format: Date format for the strptime
    :param start_date: Period start date, format must be: "%Y-%m-%d"
    :param end_date: Period end date, format must be: "%Y-%m-%d"
    :return: Datetime delta
    """

    if len(EOProduct_list) < 1:
        _logger.warning("Input list is empty, returning high value 9999")
        return timedelta(9999)
    else:
        split_parameter = "_|T"
        extremity_dateformat = "%Y-%m-%d"

        # Building date list (to make sure they are sorted)
        date_list = []
        for s1_prod in EOProduct_list:
            date = re.split(split_parameter, s1_prod.properties["id"])[4]
            date_list.append(datetime.strptime(date, date_format))

        date_list.sort()

        # Comparing to the start extremity
        previous_date = datetime.strptime(start_date, extremity_dateformat)
        delta_max = timedelta(0)

        # Chained comparison
        for current_date in date_list:
            delta_max = max(abs(current_date - previous_date), delta_max)
            _logger.debug("DATE: %s", previous_date)
            # logging (1)
            previous_date = current_date

        # Comparing to the end extremity
        end_date_strp = datetime.strptime(end_date, extremity_dateformat)
        delta_max = max(abs(previous_date - end_date_strp), delta_max)

        # logging (2)
        _logger.debug("DATE: %s", previous_date)
        _logger.debug("DATE: %s", end_date_strp)

        return delta_max


def cross_prodvider_ids(s2_tile, start, end, cloudcover, min_nb_prods, creds):
    poly = eotile_module.main(s2_tile)[0]
    # Start search with element84 API
    s2_prods_e84 = eodag_prods(
        poly,
        start,
        end,
        "earth_search",
        "sentinel-s2-l2a-cogs",
        creds=creds,
        cloud_cover=100,
    )
    # Filter and Clean
    e84 = {}
    for el in s2_prods_e84:
        pid = el.properties["sentinel:product_id"]
        cc = el.properties["cloudCover"]
        date = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if s2_tile in pid:
            e84[pid] = {"cc": float(cc), "date": date}
    # Sort by date ascending
    e84 = {el: v for el, v in sorted(e84.items(), key=lambda item: item[1]["date"])}
    # Return list of best products for a given cloud cover and yearly threshold
    e84 = get_best_prds(e84, cloudcover, min_nb_prods)
    return e84


def get_best_prds(s2_prds: dict, cloudcover: float, min_nb_prods: int) -> List:
    # Get number of months from sorted dict
    last_date = s2_prds[list(s2_prds.keys())[-1]]["date"]
    first_date = s2_prds[list((s2_prds.keys()))[0]]["date"]
    n_months = (
        (last_date.year - first_date.year) * 12 + last_date.month - first_date.month
    )
    min_nb_prods = round((n_months * min_nb_prods) / 12)
    # Filter produtcs by cloud cover
    cc_filter = [prd for prd in s2_prds if s2_prds[prd]["cc"] <= float(cloudcover)]
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


if __name__ == "__main__":
    aws = cross_prodvider_ids(
        "31TCJ", "2018-01-01", "2019-01-01", 90, 50, creds="/eodag_config.yml"
    )
    print("\n".join(aws))
