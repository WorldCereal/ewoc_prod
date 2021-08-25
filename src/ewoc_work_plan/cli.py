import argparse
import logging
import sys

from .plan.prep_all import PlanProc

from ewoc_work_plan import __version__

__author__ = "Fahd Benatia"
__copyright__ = "CS Group France"
__license__ = "TBD"

_logger = logging.getLogger(__name__)

def generate_work_plan(aoi, start_date,end_date,out_file,eodag_creds,eodag_provider,process_l8):
    plan = PlanProc(aoi, eodag_creds,eodag_provider)
    plan.run(start_date,end_date,process_l8=process_l8)
    plan.write_plan(out_file)

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Prepares and organizes the satellite products for the EWoC system")
    parser.add_argument(
        "--version",
        action="version",
        version="ewoc_work_plan {ver}".format(ver=__version__),
    )
    parser.add_argument(dest="aoi", help="AOI file path geojson/shapefile", type=str)
    parser.add_argument(dest="sd", help="Start date, format YYYY-mm-dd", type=str)
    parser.add_argument(dest="ed", help="End date, format YYYY-mm-dd")
    parser.add_argument(dest="o", help="Path to output json file")
    parser.add_argument(dest="creds",help="EOdag creds yaml file path")
    parser.add_argument(dest="provider", help="peps/creodias/astraea_eod")
    parser.add_argument(dest="process_l8", help="Process L8 OLI bands or not")
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
    """Wrapper of generate_work_plan

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  TODO).
    """
    args = parse_args(args)

    setup_logging(args.loglevel)

    generate_work_plan(args.aoi,args.sd,args.ed,args.o,args.creds,args.provider,args.process_l8)

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == "__main__":
    run()