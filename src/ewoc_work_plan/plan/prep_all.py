import json

import geopandas as gpd
from eotile import eotile_module
from tqdm import tqdm
import csv
from ewoc_work_plan.plan.utils import *
from ewoc_work_plan.remote.landsat_cloud_mask import Landsat_Cloud_Mask
from ewoc_work_plan.remote.sentinel_cloud_mask import Sentinel_Cloud_Mask

logging.basicConfig(level=logging.ERROR)

CHECK_MSK = False

class PlanProc:
    def __init__(self, aoi, eodag_creds, eodag_provider):
        self.aoi = aoi
        self.creds = eodag_creds
        self.provider = eodag_provider
        self.plan = None
        self.maxcloud = 90
        self.rest_ids=None

    def run(self, start_date, end_date,process_l8):
        if self.aoi.endswith(('.shp', '.geojson', '.gpkg')):
            # Vector file to get bbox
            vec = gpd.read_file(self.aoi)
            self.rest_ids = list(vec['tile'])
            print(self.rest_ids)
            # Re-project geometry if needed
            if vec.crs.to_epsg() != 4326:
                vec = vec.to_crs(4326)
            s2_tiles = eotile_module.main(self.aoi)
        elif self.aoi.endswith(('.csv')):
            self.rest_ids = []
            with open(self.aoi) as csvfile:
                reader = csv.reader(csvfile)
                for line in reader:
                    for id in line:
                        self.rest_ids.append(id)
        else:
            #s2_tiles = eotile_module.main(self.aoi)
            self.rest_ids=[self.aoi]
        

        # Init json plan
        plan = {}
        valid =self.rest_ids
        for s2_tile in tqdm(valid, desc="Planning S2"):
            tile_id = s2_tile
            tmp = eotile_module.main(s2_tile)
            df = tmp[0]
            #df = df.rename(columns={0:'geometry'}).set_geometry('geometry')
            plan[tile_id] = {}
            # SAR part
            plan[tile_id]["SAR_PROC"] = {}
            plan[tile_id]["SAR_PROC"]["INPUTS"] = []
            #plan[tile_id]["SAR_PROC"]["AUX"] = {}
            # Get S1 products over the S2 tile
            s1_prods_types = {"peps": "S1_SAR_GRD", "astraea_eod": "sentinel1_l1c_grd","creodias":"S1_SAR_GRD"}
            product_type = s1_prods_types[self.provider.lower()]
            s1_prods = eodag_prods(df, start_date, end_date, provider=self.provider, product_type=s1_prods_types[self.provider], creds=self.creds)
            s1_prods = [s1_prod for s1_prod in s1_prods if is_ascending(s1_prod,self.provider)]

            current_date = 0
            current_list = []
            date_begins = 17
            date_ends = 25
            for s1_prod in s1_prods:
                if s1_prod.properties["id"][date_begins:date_ends] == current_date:
                    current_list.append(s1_prod.properties["id"])
                else:
                    if len(current_list) > 0:
                        plan[tile_id]["SAR_PROC"]["INPUTS"].append(current_list)
                    current_date = s1_prod.properties["id"][date_begins:date_ends]
                    current_list = [s1_prod.properties["id"]]
            if len(current_list) > 0:
                plan[tile_id]["SAR_PROC"]["INPUTS"].append(current_list)

            # Optical part
            # S2 part
            s2_prods_types = {"peps": "S2_MSI_L1C", "astraea_eod": "sentinel2_l1c", "creodias": "S2_MSI_L1C"}
            product_type = s2_prods_types[self.provider.lower()]
            s2_prods = eodag_prods(df, start_date, end_date, provider=self.provider, product_type=product_type,
                                   creds=self.creds, cloudCover=self.maxcloud)
            plan[tile_id]["S2_PROC"] = {}
            plan[tile_id]["S2_PROC"]["INPUTS"] = []
            # plan[tile_id]["S2_PROC"]["AUX"] = {}
            s2_dates_list = []
            for s2_prod in tqdm(s2_prods):
                s2_prod_id = s2_prod.properties["id"]
                date = (s2_prod.properties["startTimeFromAscendingNode"].split("T")[0].replace("-", ""))
                if not date in s2_dates_list:
                    if CHECK_MSK:
                        mask_file = ""
                        if tile_id in s2_prod_id:
                            s2_mask = Sentinel_Cloud_Mask(tile_id, date)
                            if s2_mask.mask_exists():
                                mask_file = f"s3://{s2_mask.bucket}/{s2_mask.key}"
                            tmp = {"id": s2_prod_id, "cloud_mask": mask_file}
                            plan[tile_id]["S2_PROC"]["INPUTS"].append(tmp)
                            s2_dates_list.append(s2_prod_id)
                    elif tile_id in s2_prod_id:
                        plan[tile_id]["S2_PROC"]["INPUTS"].append({"id": s2_prod_id})

            # L8 part
            plan[tile_id]["L8_PROC"] = {}
            plan[tile_id]["L8_PROC"]["INPUTS"] = []
            #plan[tile_id]["L8_PROC"]["AUX"] = {}
            plan[tile_id]["L8_TIRS"] = []
            l8_prods_types = {"peps": "L8_OLI_TIRS_C1L1", "astraea_eod": "landsat8_l1tp","creodias":"L8_OLI_TIRS_C1L1"}
            product_type = l8_prods_types[self.provider.lower()]
            l8_prods = eodag_prods(df,start_date,end_date,provider=self.provider, product_type=product_type,creds=self.creds,cloudCover=self.maxcloud)
            # filter the prods: keep only T1 products
            l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith(('T1','T1_L1TP'))]
            #l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith('RT')]
            print(l8_prods)
            l8_date_list = []
            for l8_prod in l8_prods:
                l8_prod_id = l8_prod.properties["id"]
                mask_file = ""
                tirs_b10_file = ""
                path, row  = get_path_row(l8_prod,self.provider.lower())
                date = (l8_prod.properties["startTimeFromAscendingNode"].split("T")[0].replace("-", ""))
                if not date in l8_date_list:
                    l8_mask = Landsat_Cloud_Mask(path,row,date)
                    if l8_mask.mask_exists():
                        mask_file = f"s3://{l8_mask.bucket}/{l8_mask.cloud_key}"
                        tirs_b10_file = f"s3://{l8_mask.bucket}/{l8_mask.tirs_10_key}"
                        print(tirs_b10_file)

                    if process_l8=='y':
                        tmp = {"id": l8_prod_id, "cloud_mask": mask_file}
                        plan[tile_id]["L8_PROC"]["INPUTS"].append(tmp)
                        plan[tile_id]["L8_TIRS"].append(tirs_b10_file)
                    else:
                        plan[tile_id]["L8_TIRS"].append(tirs_b10_file)
                    l8_date_list.append(date)

            self.plan = plan

    def write_plan(self, out_file):
        # Write the json
        with open(out_file, "w") as fp:
            json.dump(self.plan, fp, indent=4)


