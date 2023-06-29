import argparse
import csv
from pathlib import Path
import sys


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
        dest="prd_status",
        help="File path containing all status for prd tiles",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "-o","--out-dirpath",
        dest="out_dirpath",
        help="path for csv file containing all tiles and production id",
        default='.',
        type=Path,
    )
    parser.add_argument(
        "-i","--input",
        dest="tile_error",
        help="tiles in error",
        default=None,
        type=Path,
    )
    return parser.parse_args(args)


def build_rows(tile_unk, add_list):
    """From different list obtained with csv file status, assign when it is possible 
    a production id to tiles with error status
    Args;
        tile_aez (list) : List of tile and corresponding aez which are in error
        add_list (list) : all different s3 bucket address containing production id
    """
    prd_id_unk=[]

    #This for loop stores the address for the tiles in error which have the same aez id as a tile which is not in error
    for ta in tile_unk:
        cnt=0
        i=0
        cond=True
        while cond:
            if ta.split('_')[1] in add_list[i]:
                cnt+=1
                prd_id_unk.append([ta.split('_')[0], add_list[i].split('/')[3]])
            i+=1
            cond = cnt<1 and i<len(add_list)

    return prd_id_unk


def filter_func(err_list, final_prd):
    """From different list obtained with csv file status and tiles in error for different season,
    filter the tile - production id list with tile in error

    Args;
        err_list (list) : List of tile in error for a season
        final_prd (list) : list of all tile and production id
    """
    filter_list=[]
    for ta in err_list:
        cnt=0
        i=0
        cond=True
        while cond:
            if ta in final_prd[i][0]:
                cnt+=1
                filter_list.append([ta, final_prd[i][1]])
            i+=1
            cond = cnt<1 and i<len(final_prd)
    return filter_list


def main(args):
    """
    Main script
    """
    tile_aez=[]
    add_list=[]
    add_tile=[]
    prd_init=[]
    err_list=[]

    args = parse_args(args)
    ewoc_tiles_aez_path=args.prd_status
    ewoc_tiles_error_path=args.tile_error

    with open(ewoc_tiles_aez_path, 'r', encoding='utf8') as prd_file:
        prd_dict=csv.DictReader(prd_file, delimiter=',')
        for row_prd in prd_dict:
            aez_pres = row_prd['aez_id']!=''
            if aez_pres:
                add_tile.append(row_prd['s2_tile_name'])
            missing=row_prd['cropmap_path']!=''
            if missing:
                add_list.append(row_prd['cropmap_path'])
                prd_init.append([row_prd['cropmap_path'].split('/')[-2],
                                row_prd['cropmap_path'].split('/')[3]])
            elif aez_pres:
                tile_aez.append(row_prd['s2_tile_name']+'_'+row_prd['aez_id'])

    add_tile=list(set(add_tile))
    add_list=list(set(add_list))

    prd_unknown=build_rows(tile_aez, add_list)

    out_path=args.out_dirpath
    final_prd = sorted(prd_unknown+prd_init)

    #check if optionnal argument file containing tile in error for a season is given and compute list to call filter_func()
    if ewoc_tiles_error_path is not None:
        season=str(ewoc_tiles_error_path).split('_')[1]
        with open(ewoc_tiles_error_path, 'r', encoding='utf8') as error_file:
            err_dict=csv.DictReader(error_file, delimiter=',')
            for row_err in err_dict:
                err_list.append(row_err['s2_tile_name'])

        filter_list=filter_func(err_list, final_prd)
        with open(Path(out_path, f'prd_id_tile_{season}'), 'w', encoding='utf8') as run_file:
            csv_writer = csv.writer(run_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['tile_name','prd_id'])
            csv_writer.writerows(filter_list)

    with open(Path(out_path, "prd_id_tile_all.csv"), 'w', encoding='utf8') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['tile_name','prd_id'])
        csv_writer.writerows(final_prd)


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__=='__main__':
    run()
