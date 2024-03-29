from datetime import datetime, timedelta
import logging
import os
import re
from typing import List
import xml.etree.ElementTree as et

import boto3
from click import Option, UsageError
from eodag.api.core import EODataAccessGateway
from ewoc_dag.eo_prd_id.s1_prd_id import S1PrdIdInfo
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


def is_valid_sar(s1_product, provider):
    # Get some info from the eoproduct propeties
    pid = s1_product.properties["id"]
    if provider == 'creodias':
        timeliness = s1_product.properties["timeliness"]
    nrt_deadline = datetime.strptime("20210223T000000",'%Y%m%dT%H%M%S')
    # Get more info from product id
    s1_product_meta = S1PrdIdInfo(pid)
    start_time = s1_product_meta.start_time
    beam_mode = s1_product_meta.beam_mode
    polarisation = s1_product_meta.polarisation
    # Kick-out the NRT-3h produced befor 20210223
    if provider == 'creodias' and start_time < nrt_deadline and timeliness != "Fast-24h":
        _logger.info(f"Bad product {s1_product.properties['id']} - timeliness: {timeliness}")
        return False
    # Check the sensor mode and polarisation
    if beam_mode == "IW" and polarisation == "DV":
        return True
    else:
        _logger.info(f"Bad product {s1_product.properties['id']} - polarisation: {polarisation}")
        return False


def sort_sar_products(s1_products, provider):
    ascending = []
    descending = []
    for s1_product in s1_products:
        if is_valid_sar(s1_product, provider):
            if is_descending(s1_product, provider):
                descending.append(s1_product)
            else:
                ascending.append(s1_product)
    return descending, ascending


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


def remove_duplicates(prd_list_ids: List) -> List:
    """
    Remove duplicates in product ids
    Keep the most recent reprocessing of the Sentinel-2 product
    :param prd_list_ids: List of Sentinel-2 ids
    """
    dates = {}
    res = []
    for pid in prd_list_ids:
        day_time = datetime.strptime(pid.split("_")[2], "%Y%m%dT%H%M%S")
        if day_time in dates:
            dates[day_time].append(pid)
        else:
            dates[day_time] = []
            dates[day_time].append(pid)
    for day in dates:
        pids_list = dates[day]
        if len(pids_list) > 1:
            _logger.warning(
                "Found %s duplicates, keeping only latest product reproc"
                % len(pids_list)
            )
            pids_list.sort(
                key=lambda x: datetime.strptime(x.split("_")[6].replace(".SAFE", ""), "%Y%m%dT%H%M%S")
            )
        res.append(pids_list[-1])
    return res

class MutuallyExclusiveOption(Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        help = kwargs.get('help', '')
        if self.mutually_exclusive:
            ex_str = ', '.join(self.mutually_exclusive)
            kwargs['help'] = help + (
                ' NOTE: This argument is mutually exclusive with '
                ' arguments: [' + ex_str + '].'
            )
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise UsageError(
                "Illegal usage: `{}` is mutually exclusive with "
                "arguments `{}`.".format(
                    self.name,
                    ', '.join(self.mutually_exclusive)
                )
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(
            ctx,
            opts,
            args
        )
