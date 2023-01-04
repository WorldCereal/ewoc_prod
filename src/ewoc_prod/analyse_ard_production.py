import argparse
import csv
from datetime import datetime
import json
import logging
import sys
import tarfile
import numpy as np
import os 
import shutil

from datetime import datetime
from pathlib import Path
from analyse_production import setup_logging, is_s3path

__author__ = "Romain Buguet de Chargere"
__copyright__ = "CS Group France"
__license__ = "Unlicense"

_logger = logging.getLogger(__name__)

def setup_logging(loglevel: int) -> None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel,
        stream=sys.stdout,
        format=logformat,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="EWoC Classification parser")
    parser.add_argument(
        "--version",
        action="version",
        version=f"TODO",
    )
    parser.add_argument(
        dest="status_filepath",
        help="Filepath to status",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "-o","--out-dirpath",
        dest="out_dirpath",
        help="Cropland models version",
        type=Path,
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



def analyse_ard_rows(csv_dict_reader, tile, file_name):
    """Analyze csv file rows for several tiles about OPTICAL, SAR and TIR ARD data status 
    
    Args;
        csv_dict (DictReader) : Ordered dict containing the products and address (or error status) of each csv file
        tile (str) ; the tile concerned by the csv file examinated
        file_name (str) : path to the csv file 
    """
    
    nb_error_opt=0
    nb_error_sar=0
    nb_error_tir=0
    ewoc_status={}
    ard_list=[]

    if "opt" in str(file_name):
        nb_prd_opt=0
        for row in csv_dict_reader:
            nb_prd_opt+=1
            if row['status']=='error':
                logging.debug(f"OPTICAL product {row['product']} is in error")
                nb_error_opt+=1
                ard_list.append([tile,'OPTICAL', row['product']])
            elif row['status']=='scheluded':
                logging.debug(f"OPTICAL product {row['product']} of tile {tile} is scheduled")
            elif not is_s3path(row['status']):
                logging.debug(f"OPTICAL product {row['product']} status of tile {tile} is unknown")

        opt_ratio=(nb_error_opt/(nb_prd_opt+1e-15))
        print(f"OPTICAL Tile {tile} has {round(opt_ratio*100, ndigits=4)}% products in errors")

    elif 'tir' in str(file_name):
        nb_prd_tir=0
        for row in csv_dict_reader:
            nb_prd_tir+=1
            if row['status']=='error':
                logging.info(f"TIR product {row['product']} of tile {tile} is in error")
                nb_error_tir+=1
                ard_list.append([tile,'TIR', row['product']])
            elif row['status']=='scheluded':
                logging.debug(f"TIR product {row['product']} of tile {tile} is scheduled")
            elif not is_s3path(row['status']):
                logging.debug(f"TIR product {row['product']} status of tile {tile} is unknown")

        tir_ratio=(nb_error_tir/(nb_prd_tir+1e-15))
        print(f"TIR Tile {tile} has {round(tir_ratio*100, ndigits=4)}% products in error")

    elif 'sar' in str(file_name):
        nb_prd_sar=0
        for row in csv_dict_reader:
            if row['status']=='error':
                nb_prd_sar+=1
                logging.info(f"SAR product {row['product']} of tile {tile} is in error")
                nb_error_sar+=1
                ard_list.append([tile,'SAR', row['product']])
            elif row['status']=='scheluded':
                logging.debug(f"SAR product {row['product']} of tile {tile} is scheduled")
            elif not is_s3path(row['status']):
                logging.debug(f"SAR product {row['product']} status of tile {tile} is unknown")

        sar_ratio=(nb_error_sar/(nb_prd_sar+1e-15))
        print(f"SAR Tile {tile} has {sar_ratio*100}% product in error")

    return ard_list


def main(args):
    args = parse_args(args)
    setup_logging(args.loglevel)

    ewoc_status_filepath = args.status_filepath 

    #Take date and time written at the end of the filename 
    info_date=str(ewoc_status_filepath).split('_')[-3:]

    if ewoc_status_filepath.suffix == ".gz":
        with tarfile.open(ewoc_status_filepath) as ewoc_status_file:
            _logger.debug(ewoc_status_file.getnames())
            names=ewoc_status_file.getnames()

            #Take folder name where is stored extracted files
            first_folder=ewoc_status_file.getnames()[0]
            
            #Select only desired csv files 
            name_list=[i for i in names if "path.csv" in i] 
            for i in name_list:
                ewoc_status_file.extract(str(i), Path(args.out_dirpath))

    ard_list=[]
    for csv_path in name_list:
        tile=csv_path.split('/')[-2]
        with open(Path(args.out_dirpath)/csv_path) as csv_file:
            csv_dict=csv.DictReader(csv_file, fieldnames=['product', 'status'], delimiter=',')
            result_ard=analyse_ard_rows(csv_dict, tile, csv_file)
            if type(result_ard) is not None:
                ard_list.append(result_ard)
    

    out_file_path=Path(f'{args.out_dirpath}/ard_error').with_suffix('.csv')

    with open(out_file_path, 'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter='|',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['tile_name','type','ard_product'])
            csv_writer.writerows(ard_list)
    
    logging.info(f"File {args.out_dirpath}/ard_error.csv succesfully created ")

    #deleting csv file extracted from .tag.gz file 
    shutil.rmtree(Path(args.out_dirpath,first_folder))
    logging.info(f"File {args.out_dirpath}/{first_folder} succesfully deleted ")


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == "__main__":
    run()
