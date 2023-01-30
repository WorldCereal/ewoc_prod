import os
import otbApplication
import argparse
import sys
from pathlib import Path

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
        dest="dir_path",
        help="Dir path containing all S2 masks for a tile",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "-o","--out-dirpath",
        dest="out_dirpath",
        help="path for output image",
        default='.',
        type=Path,
    )
    return parser.parse_args(args)

def main(args):
    """
    Main script
    """
    args = parse_args(args)
    dir_path = args.dir_path 
    our_dir = args.out_dirpath

    print("dir_path", dir_path)

    tile=str(dir_path).split('/')[-1]

    app = otbApplication.Registry.CreateApplication("BandMath")


    nb_files=len([entry for entry in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, entry))])
    expr_str = ', '.join([f"im{i}b1" for i in range(1,nb_files+1)])

    #Compute the input str list of file to sum 
    files_str=[os.path.join(dir_path, file) for file in os.listdir(dir_path)]

    #Assign parameters, expression and run OTB application
    app.SetParameterStringList("il", files_str)
    app.SetParameterString("out", f"{our_dir}/S2A_L2A_{tile}_SUM")
    app.SetParameterString("exp", "sum("+expr_str+")")
    app.ExecuteAndWriteOutput()

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__=="__main__":
    run()
