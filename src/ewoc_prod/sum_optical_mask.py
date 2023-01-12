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
    
    args = parse_args(args)
    dir_path = args.dir_path #r'/home/rbuguetd/data/optical_mask/15PXR/'
    our_dir = args.out_dirpath

    print("dir_path", dir_path)

    tile=str(dir_path).split('/')[-1]

    app = otbApplication.Registry.CreateApplication("BandMath")

    
    nb_files=len([entry for entry in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, entry))])
    expr_str = ', '.join([f"im{i}b1" for i in range(1,nb_files+1)])
    
    #print(expr_str)
    
    files_str=[os.path.join(dir_path, file) for file in os.listdir(dir_path)]

    #["/home/rbuguetd/data/optical_mask/15PXR/S2B_L2A_20210228T162119_N0214R040T15PXR_15PXR_MASK.tif", "/home/rbuguetd/data/optical_mask/15PXR/S2B_L2A_20210218T162329_N0214R040T15PXR_15PXR_MASK.tif"]
    #files_str= os.listdir(dir_path)
    print(files_str)

    app.SetParameterStringList("il", files_str)
    app.SetParameterString("out", f"{our_dir}/S2A_L2A_{tile}_SUM")
    app.SetParameterString("exp", "sum("+expr_str+")")

    app.ExecuteAndWriteOutput()

def run():
    main(sys.argv[1:])

if __name__=="__main__":
    run()