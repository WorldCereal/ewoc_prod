from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

def conversion_doy_to_date(doy: int, year: date = date.today().year)->date:
    """
    Convert day of year to date YYYY-mm-dd
    :param doy: day of year
    :param year: year
    """
    year = str(year)
    str(doy).rjust(3 + len(str(doy)), '0')
    date_string = datetime.strptime(year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
    date_format = datetime.strptime(date_string, "%Y-%m-%d").date()
    return date_format
