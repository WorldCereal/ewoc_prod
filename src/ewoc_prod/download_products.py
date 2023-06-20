import argparse
import sys
import csv
import os
from pathlib import Path
import boto3


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="Download products")
    parser.add_argument(
        dest="path_product",
        help="CSV file containing tiles and s3 bucket path to product",
        default=None,
        type=Path,
    )
    parser.add_argument(
        dest="aez",
        help="AEZ product to download",
        default=None,
        type=int,
    )
    parser.add_argument(
        "-o","--out-dirpath",
        dest="out_dirpath",
        help="path for downloaded products",
        default='.',
        type=Path,
    )
    return parser.parse_args(args)

def download_s3_files(csv_file_path, aez, out_path):
    """
    Function to download products from a specific aez
    """
    key_id=os.environ['EWOC_S3_ACCESS_KEY_ID']
    secret_id=os.environ['EWOC_S3_SECRET_ACCESS_KEY']

    s3 = boto3.resource(
        service_name='s3',
        region_name='eu-central-1',
        aws_access_key_id=key_id,
        aws_secret_access_key=secret_id
    )
    with open(csv_file_path, encoding='utf8') as file_path:
        prod_dict=csv.DictReader(file_path, delimiter=',')
        for row in prod_dict:
            if aez in row['cropmap_path']:
                s3_path = row['cropmap_path']
                bucket_name = s3_path.split('/')[2]
                bucket=s3.Bucket(bucket_name)
                file_key = '/'.join(s3_path.split('/')[3:])

                for obj in bucket.objects.filter(Prefix = file_key+'/'):
                    check_path=os.path.dirname(Path(out_path,str(obj.key)))
                    if not os.path.exists(check_path):
                        os.makedirs(check_path)
                    bucket.download_file(obj.key, Path(out_path,str(obj.key)))

def main(args):
    """
    Main function
    """
    args = parse_args(args)
    prd_file=args.path_product
    out_path=args.out_dirpath
    aez_id=str(args.aez)

    download_s3_files(prd_file, aez_id, out_path)

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__=='__main__':
    run()
