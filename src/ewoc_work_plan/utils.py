import os
import logging
import xml.etree.ElementTree as et
import re
from shapely.wkt import dumps
from datetime import datetime, timedelta
import boto3
from eodag.api.core import EODataAccessGateway

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


def eodag_prods(df,start_date,end_date,provider,product_type,creds,cloud_cover=None):
    dag = EODataAccessGateway(user_conf_file_path=creds)
    dag.set_preferred_provider(provider)
    #poly = df.geometry[0].to_wkt()
    poly = dumps(df.geometry[0])
    max_items = 2000
    if cloud_cover is None:
        if product_type=="LANDSAT_C2L2_SR":
            # We use search all for L8 products because we need pagination
            products = dag.search_all(productType=product_type, geom=poly, start=start_date, end=end_date,
                                     platformSerialIdentifier="LANDSAT_8")
        else:
            products, __unused = dag.search( productType=product_type,
                                    start=start_date, end=end_date,
                                    geom=poly, items_per_page=max_items)
    else:
        if product_type=="LANDSAT_C2L2_SR":
            products = dag.search_all(productType=product_type, geom=poly, start=start_date, end=end_date,
                                     platformSerialIdentifier="LANDSAT_8", cloudCover=cloud_cover)

        else:
            products, __unused = dag.search(productType=product_type,
                                        start=start_date, end=end_date, geom=poly,
                                         items_per_page=max_items,
                                         cloudCover=cloud_cover)

    return products


def is_descending(s1_product,provider):
    if provider.lower() == 'creodias':
        if s1_product.properties['orbitDirection'] == "descending":
            return True
    else:
        manifest_key = os.path.split(s1_product.assets['vv']['href'])[0].replace('measurement',
                                                                                 'manifest.safe')
        bucket = "sentinel-s1-l1c"
        key = manifest_key.replace("s3://sentinel-s1-l1c/","")
        s3_client = boto3.client('s3')
        try:
            obj = s3_client.get_object(Bucket=bucket,Key=key,RequestPayer='requester')
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
            _logger.error('Could not determine orbit direction')


def get_path_row(product, provider):
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
    elif provider.lower() == "usgs_satapi_aws":
        path = product.assets['blue']['href'].split('/')[8]
        row = product.assets['blue']['href'].split('/')[9]
    else:
        raise NotImplementedError(f"Provider {provider} not implemented yet ")
    return path, row

def greatest_timedelta(EOProduct_list:list, start_date:str, end_date:str, date_format:str = "%Y%m%d") -> timedelta:
    """
    Computes the greatest time delta from a list of EOdag products

    :param EOProduct_list: List of EOdag products to analyse
    :param date_format: Date format for the strptime
    :param start_date: Period start date, format must be: "%Y-%m-%d"
    :param end_date: Period end date, format must be: "%Y-%m-%d"
    :return: Datetime delta
    """

    if len(EOProduct_list) < 1:
        raise ValueError("Input list is empty")

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
        _logger.debug(f"DATE: %s", previous_date)
        # logging (1)
        previous_date = current_date

    # Comparing to the end extremity
    end_date_strp = datetime.strptime(end_date, extremity_dateformat)
    delta_max = max(abs(previous_date - end_date_strp), delta_max)

    # logging (2)
    _logger.debug(f"DATE: %s", previous_date)
    _logger.debug(f"DATE: %s", end_date_strp)

    return (delta_max)

