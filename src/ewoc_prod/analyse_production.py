import argparse
import csv
from datetime import datetime
import json
import logging
import sys
import tarfile
import shutil

from datetime import datetime
from pathlib import Path

__author__ = "Mickael Savinaud"
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
        dest="selection_filepath",
        help="Filepath to selection tiles geojson",
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

def analyse_rows(ewoc_status_reader, type):
    ewoc_season=type.split(" ")[0]

    nb_requested_tiles=0
    nb_error_status=0
    nb_pp_error_status=0
    nb_unknown_status=0
    nb_scheduled_status=0
    nb_processing_status=0
    nb_done_status=0
    nb_na_status=0
    ewoc_status={}
    for row in ewoc_status_reader:
        nb_requested_tiles+=1
        if row[type]=='Unknown status':
            nb_unknown_status+=1
            ewoc_status[row['Tile name']]='not ingested'
        elif row[type]=='pperror':
            nb_pp_error_status+=1
            ewoc_status[row['Tile name']]='pre-processing error'
        elif row[type]=='error':
            nb_error_status+=1
            ewoc_status[row['Tile name']]='error'
        elif row[type]=='processing':
            nb_processing_status+=1
            ewoc_status[row['Tile name']]='processing'
        elif row[type]=='scheduled':
            nb_scheduled_status+=1
            ewoc_status[row['Tile name']]='scheduled'
        elif row[type]=='Not Available for this season':
            nb_na_status+=1
            ewoc_status[row['Tile name']]='not expected'
        elif row[type].split('/')[0] == 's3:':
            nb_done_status+=1
            ewoc_status[row['Tile name']]=row[type]
        else:
            raise ValueError('Unknow value: %s',row[type])

    _logger.info(f'------- {ewoc_season} -------')
    if ewoc_season == 'Summer2':
        nb_requested_tiles = nb_requested_tiles - nb_na_status    
    _logger.info(f'Nb Tiles requested {nb_requested_tiles}')
    _logger.info(f'Nb Tiles not ingested {nb_unknown_status}')
    _logger.info(f'Nb Tiles scheduled {nb_scheduled_status}')
    _logger.info(f'Nb Tiles in processing {nb_processing_status}')
    _logger.info(f'Nb Tiles blocked in pre-processing error {nb_pp_error_status}')
    _logger.info(f'Nb Tiles in error {nb_error_status}')
    _logger.info(f'Nb Tiles in success {nb_done_status}')

    return ewoc_status

def is_s3path(value:str)->bool:
    return value.split('/')[0] == 's3:'

def main(args):

    args = parse_args(args)
    setup_logging(args.loglevel)

    ewoc_status_filepath = args.status_filepath
    
    if ewoc_status_filepath.suffix == ".gz":
        with tarfile.open(ewoc_status_filepath) as ewoc_status_file:
            _logger.debug(ewoc_status_file.getnames())
            first_folder=ewoc_status_file.getnames()[0]
            csv_filename = ewoc_status_file.getnames()[1]
            ewoc_status_file.extract(str(csv_filename), Path('.'))

        ewoc_status_filepath=Path('.') / csv_filename
        print('path', ewoc_status_filepath)

    ewoc_season_year=ewoc_status_filepath.stem.split('_')[1]
    ewoc_date_status=ewoc_status_filepath.stem.split('_')[2]
    ewoc_time_status=ewoc_status_filepath.stem.split('_')[3]
    
    CROPMAP_KEY='Cropmap path'
    SUMMER1_KEY='Summer1 path'
    SUMMER2_KEY='Summer2 path'
    WINTER_KEY='Winter path'
    
   
    with open(ewoc_status_filepath, 'r') as ewoc_status_file:
        ewoc_status_reader = csv.DictReader(ewoc_status_file, delimiter=',')

        ewoc_cm_status= analyse_rows(ewoc_status_reader, CROPMAP_KEY)

    with open(ewoc_status_filepath, 'r') as ewoc_status_file:
        ewoc_status_reader = csv.DictReader(ewoc_status_file, delimiter=',')

        ewoc_s1_status=analyse_rows(ewoc_status_reader, SUMMER1_KEY)

    with open(ewoc_status_filepath, 'r') as ewoc_status_file:
        ewoc_status_reader = csv.DictReader(ewoc_status_file, delimiter=',')

        ewoc_s2_status=analyse_rows(ewoc_status_reader, SUMMER2_KEY)

    with open(ewoc_status_filepath, 'r') as ewoc_status_file:
        ewoc_status_reader = csv.DictReader(ewoc_status_file, delimiter=',')

        ewoc_w_status=analyse_rows(ewoc_status_reader, WINTER_KEY)
    
    ewoc_tiles_filepath=Path(args.selection_filepath)

    out_filepath_geojson=Path(f'{args.out_dirpath}/ewoc_prd_tiles_{ewoc_season_year}_{ewoc_date_status}T{ewoc_time_status}.geojson')
    out_filepath_geojson.unlink(missing_ok=True)
    status_filepath_geojson=Path(f'{args.out_dirpath}/ewoc_status_tiles_{ewoc_season_year}_{ewoc_date_status}T{ewoc_time_status}.geojson')
    status_filepath_geojson.unlink(missing_ok=True)
    out_filepath_csv=out_filepath_geojson.with_suffix('.csv')
    out_filepath_csv.unlink(missing_ok=True)

    new_data={}
    status_data={}
    with open(ewoc_tiles_filepath, 'r') as ewoc_tiles_file:
        data = json.load(ewoc_tiles_file)
        new_data['type'] = data['type']
        new_data['name'] = "ewoc_prd_tiles"
        new_data['crs'] = data['crs']
        new_data['features']=[]

        status_data['type'] = data['type']
        status_data['name'] = "ewoc_prd_tiles"
        status_data['crs'] = data['crs']
        status_data['features']=[]

        with open(out_filepath_csv, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter='|',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['s2_tile_name',
                                 'epsg_code',
                                 'aez_id',
                                 'cropmap_path',
                                 'summer1_path',
                                 'summer2_path',
                                 'winter_path'])
            
            # Iterating through the geojson features
            for i in data['features']:

                # change the name of key and the type related to aez id    
                tile_id = i['properties']['tile_id']
                
                gp_v2_inclusion = i['properties']['GP_v2_include']

                cropmap_path=None
                summer1_path=None
                summer2_path=None
                winter_path=None
                epsg_code=''
                aez_id=''
                if gp_v2_inclusion:
                    if is_s3path(ewoc_cm_status.get(tile_id)):
                        cropmap_path = ewoc_cm_status[tile_id]
                    if is_s3path(ewoc_s1_status.get(tile_id)):
                        summer1_path = ewoc_s1_status[tile_id]
                    if is_s3path(ewoc_s2_status.get(tile_id)):
                        summer2_path = ewoc_s2_status[tile_id]
                    if is_s3path(ewoc_w_status.get(tile_id)):
                        winter_path = ewoc_w_status[tile_id]

                    epsg_code = i['properties']['epsg_code']
                    i['properties'].pop('epsg_code')
                    aez_id = i['properties']['aez_id']
                    i['properties'].pop('aez_id')

                    i['properties']['s2_tile_name']= tile_id
                    i['properties']['epsg_code']= epsg_code
                    i['properties']['aez_id']=aez_id
                    i['properties']['cropmap_path']= cropmap_path
                    i['properties']['summer1_path']= summer1_path
                    i['properties']['summer2_path']= summer2_path
                    i['properties']['winter_path']= winter_path
                    # Remove unused element
                    i['properties'].pop('tile_id')
                    i['properties'].pop('optical_l8')
                    i['properties'].pop('GP_v2_include')
                    i['properties'].pop('UKR')

                    new_data['features'].append(i)
                    
                    if is_s3path(ewoc_cm_status[tile_id]):
                        i['properties']['cropmap_status']='ok'
                    else:
                        i['properties']['cropmap_status']=ewoc_cm_status[tile_id]
                    
                    if is_s3path(ewoc_s1_status[tile_id]):
                        i['properties']['summer1_status']='ok'
                    else:
                        i['properties']['summer1_status']=ewoc_s1_status[tile_id]
                    
                    if is_s3path(ewoc_s2_status[tile_id]):
                        i['properties']['summer2_status']='ok'
                    else:
                        i['properties']['summer2_status']=ewoc_s2_status[tile_id]
                    
                    if is_s3path(ewoc_w_status[tile_id]):
                        i['properties']['winter_status']='ok'
                    else:
                        i['properties']['winter_status']=ewoc_w_status[tile_id]
                    
                    i['properties'].pop('cropmap_path')
                    i['properties'].pop('summer1_path')
                    i['properties'].pop('summer2_path')
                    i['properties'].pop('winter_path')
                    status_data['features'].append(i)

                csv_writer.writerow([tile_id,
                                     epsg_code,
                                     aez_id,
                                     cropmap_path,
                                     summer1_path,
                                     summer2_path,
                                     winter_path])

        _logger.info(f'Sucessfully write: {out_filepath_csv}')

        with open(out_filepath_geojson, 'w') as geojson_file:
            json.dump(new_data, geojson_file)
            _logger.info(f'Sucessfully write: {out_filepath_geojson}')

        with open(status_filepath_geojson, 'w') as status_geojson_file:
            json.dump(status_data, status_geojson_file)
            _logger.info(f'Sucessfully write: {status_filepath_geojson}')
    
    #deleting csv file and its folder extracted from .tag.gz file 
    shutil.rmtree(Path('.',first_folder))

    return out_filepath_geojson, status_filepath_geojson, out_filepath_csv

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == "__main__":
    run()
