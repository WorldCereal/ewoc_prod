#!/usr/bin/env python3
'''
:author: Marjorie Battude <marjorie.battude@csgroup.eu>
:organization: CS Group
:copyright: 2022 CS Group. All rights reserved.
:license: see LICENSE file
:created: 2022
'''

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

def conversion_doy_to_date(doy: int, year: date = date.today().year)->date:
    """
    Convert day of year to date YYYY-mm-dd
    :param doy: day of year
    :param year: year
    """
    year = str(year)
    doy = doy + 1
    str(doy).rjust(3 + len(str(doy)), '0')
    date_string = datetime.strptime(year + "-" + str(doy), "%Y-%j").strftime("%Y-%m-%d")
    date_format = datetime.strptime(date_string, "%Y-%m-%d").date()
    return date_format
