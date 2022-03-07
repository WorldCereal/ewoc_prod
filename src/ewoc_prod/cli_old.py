import argparse
from datetime import date, datetime
import json
import logging
from pathlib import Path
import subprocess
import sys

import docker

from ewoc_work_plan.workplan import WorkPlan

from ewoc_prod import __version__

__author__ = "Mickael Savinaud"
__copyright__ = "Mickael Savinaud"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from ewoc_prod.cli import ewoc_prod`,
# when using this Python module as a library.


def ewoc_prod(prod_start_date, aez_region_id, tile_id, prototype_site_code,
              tile_start_date, tile_end_date, output_type):
    """EWoC production main script 

    Args:
      n (int): integer
      prod_start_date (date): production start date
      aez_region_id
      tiles_id
      season_start_date
      season_end_date
      output_type

    Returns:
      
    """
    aez_db_filepath = Path('/home/mickael/dev/EWoC/aez/AEZ.geojson')
    tiles_id = list()
    start_date= None
    end_date = None


    # Identify the tiles and the period from the info provided by the user
    if tile_id is not None:
        tiles_id.append(tiles_id)
        start_date = tile_start_date
        end_date = tile_end_date
        _logger.debug('Use information provided for the tile: %s, %s, %s!',  tiles_id, start_date, end_date)

    elif prototype_site_code is not None:
        assert(tile_start_date is None)
        assert(tile_end_date is None)
        
        # TODO Connect to the prototype file and use right dates
        # TODO Open the Prototype site db to retrieve to retrieve information by a simple search
        tiles_id.append('XXXXX')
        start_date = date.today()
        end_date = date.today()

        _logger.debug('Use information provided from the prototype db: %s, %s, %s!',  tiles_id, start_date, end_date)
        raise NotImplementedError
   
    elif aez_region_id is not None:
        # Search the aez region according to prod_start_date
        _logger.debug('Search the aez information according the aez region id: %s', aez_region_id)
        aez_db = EWOC_AEZ_DB(aez_db_filepath)
        aez = aez_db.get_aez_from_id(aez_region_id)
        tiles_id.append('XXXXX') # TODO Add key with tiles_id in aez db
        # TODO which ref year ?
        ref_year_str = str(date.today().year)
        # TODO Manage sos > eos
        # TODO Compute according the right formula
        if output_type == 'crop_type_ww':
            start_date = datetime.strptime(ref_year_str + '-' + str(int(aez['wwsos_min'])), "%Y-%j").date()
            end_date = datetime.strptime(ref_year_str + '-' + str(int(aez['wweos_max'])), "%Y-%j").date()
        elif output_type == 'crop_type_m1':
            start_date = datetime.strptime(ref_year_str + '-' + str(int(aez['m1sos_min'])), "%Y-%j").date()
            end_date = datetime.strptime(ref_year_str + '-' + str(int(aez['m1eos_max'])), "%Y-%j").date()
        elif output_type == 'crop_type_m2':
            start_date = datetime.strptime(ref_year_str + '-' + str(int(aez['m2sos_min'])), "%Y-%j").date()
            end_date = datetime.strptime(ref_year_str + '-' + str(int(aez['m2eos_max'])), "%Y-%j").date()
        else:
            # TODO Add all mode
            raise NotImplementedError

        _logger.debug('Use information provided from the aez db: %s, %s, %s!',  tiles_id, start_date, end_date)
        raise NotImplementedError

    else:
        _logger.debug('Search the aez according the production date requested: %s', prod_start_date)
        # Search the aez information according to aez_region_id
        aez_db = EWOC_AEZ_DB(aez_db_filepath)
        aezs = aez_db.get_aezs_from_end_date(prod_start_date)
        _logger.info('Found %s aez for ', len(aezs), prod_start_date)
        # TODO manage the case where several aez are requested
        # TODO retrieve information
        _logger.debug('Use information provided from the aez db: %s, %s, %s!',  tiles_id, start_date, end_date)
        raise NotImplementedError
    
    if tiles_id is None:
        if prototype_site_code is not None or tiles_id is not None or aez_region_id is not None:
            _logger.critical('No information to start production!')
        else:
            _logger.warning('No production for %s', prod_start_date)
    else:
        _logger.info('Produce %s products for %s tiles [%s, %s]!', output_type, tiles_id, start_date, end_date)

    # Use ewoc_workplan to create the associated workplan
    wp = WorkPlan(tiles_id, start_date, end_date, 'creodias')

    # Serialize on the disk for debug purpose
    if _logger.level == logging.DEBUG:
        from tempfile import NamedTemporaryFile
        wp.to_json(Path(NamedTemporaryFile(prefix='wp', delete=False)))

    # Fill the db
    wp.to_ewoc_db()

    # Run processing
    local_run = True # TODO move as a cli parameter
    if local_run:
        if output_type == 'ard_s2':
            client = docker.from_env()
            env_dict = dict()
            env_filepath = Path('/path/to/env.file')
            with open(env_filepath) as env_file:
                for line in env_file:
                    key, val = line.partition('=')[::2]
                    env_dict[key.strip()] = val
            client.containers.run(image='ewoc_s2:0.5.3', environment=env_dict)
    else:
        # found the right workflow
        workflow_filepath = None
        if output_type == "ard_s2":
            workflow_filepath = Path('/path/to/workflow_s2.yaml')
        else:
            raise NotImplementedError

        # Run the right workflow
        cmd = ['argo', 'submit', str(workflow_filepath)]
        subprocess.run(cmd)

    # Watch the workflow or interrogate the database to see how the processing progress ? 


class EWOC_AEZ_DB():
    def __init__(self, aez_db_filepath) -> None:
        self._aezs=None
        self._read(aez_db_filepath)
        _logger.info('%s aez avaialble!', len(self._aezs['features']))

    def _read(self, aez_filepath) -> None:
        with open(aez_filepath) as aez_file:
            self._aezs = json.load(aez_file)
            _logger.debug("Loading %s",aez_filepath)

    def get_aez_from_id(self, aez_zone_id):
        for aez in self._aezs['features']:
            if int(aez['properties']['zoneID']) == int(float(aez_zone_id)):
                return aez['properties']
        return None
    
    def get_aezs_from_end_date(self, end_date, crop_type='ww'):
        end_doy = end_date.strftime("%j")
        aez_date_key=None
        if crop_type == "ww":
            aez_date_key = "wweos_max"
        elif crop_type == "m1":
            aez_date_key = "m1eos_max"
        elif crop_type == "m2":
            aez_date_key = "m2eos_max"
        else:
            raise ValueError
        
        aezs_info = list()
        for aez in self._aezs['features']:
            if int(aez['properties'][aez_date_key]) == int(end_doy):
                aezs_info.append(aez)
        
        return aezs_info

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

def parse_date(date_str):
    try:
        # With python 3.7 it could be replaced by 
        # return date.isoformat(date_str)
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(date_str)
        raise argparse.ArgumentTypeError(msg)

def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Run the end to end ewoc processing")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('-aid', "--aez_region_id",
                        help="AEZ region id",
                        type=str)
    input_group.add_argument("-pd", "--prod_start_date", 
                        help="Production start date - format YYYY-MM-DD", 
                        type=parse_date, 
                        default=date.today())
    input_group.add_argument("-t","--tile_id",
                        help="Tile id for production",
                        type=str, nargs=1)
    input_group.add_argument("-ps","--prototype_site_code",
                        choices=['ESP', 'FRA', 'UKR', 'TZA', 'ARG'],
                        help="ISO 3166 code of production prototype countries",
                        type=str)
    parser.add_argument("-tssd","--tile_prod_start_date",
                        help="Production prototype season start date - format YYYY-MM-DD",
                        type=parse_date, nargs='?')
    parser.add_argument("-tsed","--tile_prod_end_date",
                        help="Overwrite season end date - format YYYY-MM-DD",
                        type=parse_date, nargs='?')
    parser.add_argument("-ot","--output_type",
                        choices=['ard', 'ard_s2', 'ard_l8', 'ard_s1', 'crop_mask', 'crop_type_ww', 'crop_type_m1', 'crop_type_m2', 'irrigation', 'all'],
                        help="Output produced by the production system",
                        default='all',
                        type=str)
    parser.add_argument(
        "--version",
        action="version",
        version="ewoc_prod {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    """Wrapper allowing :func:`fib` to be called with string arguments in a CLI fashion

    Instead of returning the value from :func:`fib`, it prints the result to the
    ``stdout`` in a nicely formatted message.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "42"]``).
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug("Starting crazy calculations...")
    ewoc_prod(  args.prod_start_date, args.aez_region_id, args.tile_id, args.prototype_site_code,
                args.tile_prod_start_date, args.tile_prod_end_date, args.output_type)
    _logger.info("Script ends here")


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m ewoc_prod.cli
    #
    run()
