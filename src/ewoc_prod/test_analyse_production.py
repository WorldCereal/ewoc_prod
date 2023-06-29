import unittest
from pathlib import Path
import sys

from .analyse_production import main

out_filepath_geojson, status_filepath_geojson, out_filepath_csv = main(sys.argv)
class TestCase(unittest.TestCase):
    def test_output(self):
        path_prd = Path(out_filepath_geojson)
        path_status = Path(status_filepath_geojson)
        path_csv = Path(out_filepath_csv)
        self.assertTrue(path_prd.is_file())
        self.assertTrue(path_status.is_file())
        self.assertTrue(path_csv.is_file())
        self.assertFalse(path_prd.parent.is_dir())

if __name__=="__main__":
    unittest.main() 
    