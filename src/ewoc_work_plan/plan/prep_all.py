import csv
import json
import logging
import re
from tqdm import tqdm

import geopandas as gpd
from eotile import eotile_module


from ewoc_work_plan.plan.utils import is_descending, get_path_row, eodag_prods
from ewoc_work_plan.remote.landsat_cloud_mask import Landsat_Cloud_Mask
from ewoc_work_plan.remote.sentinel_cloud_mask import Sentinel_Cloud_Mask


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

CHECK_MSK = False # If true, S2_proc becomes a dict

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
            _logger.debug(self.rest_ids)
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
            #plan[tile_id]["SAR_PROC"]["AUX"] = {}
            # Get S1 products over the S2 tile
            s1_prods_types = {"peps": "S1_SAR_GRD", "astraea_eod": "sentinel1_l1c_grd","creodias":"S1_SAR_GRD"}
            product_type = s1_prods_types[self.provider.lower()]
            s1_prods = eodag_prods(df, start_date, end_date, provider=self.provider, product_type=s1_prods_types[self.provider], creds=self.creds)

            s1_prods_desc = [s1_prod for s1_prod in s1_prods if is_descending(s1_prod, self.provider)]
            s1_prods_asc = [s1_prod for s1_prod in s1_prods if not is_descending(s1_prod, self.provider)]
            _logger.info('Number of descending products : {}'.format(len(s1_prods_desc)))
            _logger.info('Number of ascending products : {}'.format(len(s1_prods_asc)))

            # Filtering by orbit type
            ascending_selected = True
            if len(s1_prods_desc) >= len(s1_prods_asc):
                s1_prods = s1_prods_desc
                ascending_selected = False
            else:
                s1_prods = s1_prods_asc

            dic = {}
            for s1_prod in s1_prods:
                date = re.split("_|T", s1_prod.properties["id"])[4]
                if date in dic and len(s1_prod.properties["id"]) > 0:
                    dic[date].append(s1_prod.properties["id"])
                elif len(s1_prod.properties["id"]) > 0:
                    dic[date] = [s1_prod.properties["id"]]
            plan[tile_id]["SAR_PROC"]["INPUTS"] = list(dic.values())

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
                        ## Legacy
                        ## Should this be removed?
                        mask_file = ""
                        if tile_id in s2_prod_id:
                            s2_mask = Sentinel_Cloud_Mask(tile_id, date)
                            if s2_mask.mask_exists():
                                mask_file = f"s3://{s2_mask.bucket}/{s2_mask.key}"
                            tmp = {"id": s2_prod_id, "cloud_mask": mask_file}
                            plan[tile_id]["S2_PROC"]["INPUTS"].append(tmp)
                            s2_dates_list.append(s2_prod_id)
                    elif tile_id in s2_prod_id:
                        plan[tile_id]["S2_PROC"]["INPUTS"].append(s2_prod_id)

            # L8 part
            plan[tile_id]["L8_PROC"] = {}
            plan[tile_id]["L8_PROC"]["INPUTS"] = []
            #plan[tile_id]["L8_PROC"]["AUX"] = {}
            plan[tile_id]["L8_TIRS"] = []
            # Quick fix for L8
            l8_provider ="astraea_eod"
            l8_prods_types = {"peps": "L8_OLI_TIRS_C1L1", "astraea_eod": "landsat8_c2l1t1","creodias":"L8_OLI_TIRS_C1L1"}
            product_type = l8_prods_types[l8_provider.lower()]
            l8_prods = eodag_prods(df,start_date,end_date,provider=l8_provider, product_type=product_type,creds=self.creds,cloudCover=self.maxcloud)
            # filter the prods: keep only T1 products
            l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith(('T1','T1_L1TP'))]
            #l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith('RT')]
            _logger.debug(l8_prods)
            l8_date_list = []
            dic = {}
            dic_process = {}
            for l8_prod in l8_prods:
                l8_prod_id = l8_prod.properties["id"]
                mask_file = ""
                tirs_b10_file = ""
                path, row  = get_path_row(l8_prod,l8_provider.lower())
                date = (l8_prod.properties["startTimeFromAscendingNode"].split("T")[0].replace("-", ""))
                _logger.debug(path,row,date)
                l8_mask = Landsat_Cloud_Mask(path,row,date)
                if l8_mask.mask_exists():
                    mask_file = f"s3://{l8_mask.bucket}/{l8_mask.cloud_key}"
                    tirs_b10_file = f"s3://{l8_mask.bucket}/{l8_mask.tirs_10_key}"
                    _logger.debug(tirs_b10_file)
                if process_l8 == 'y':
                    tmp = {"id": l8_prod_id, "cloud_mask": mask_file}
                    if path + date in dic and len(tirs_b10_file) > 0:
                        dic[path + date].append(tirs_b10_file)
                        dic_process[path + date].append(tmp)
                    elif len(tirs_b10_file) > 0:
                        dic[path + date] = [tirs_b10_file]
                        dic_process[path + date] = [tmp]
                else:
                    if path + date in dic and len(tirs_b10_file) > 0:
                        dic[path + date].append(tirs_b10_file)
                    elif len(tirs_b10_file) > 0:
                        dic[path + date] = [tirs_b10_file]
                l8_date_list.append(date)
            plan[tile_id]["L8_TIRS"] = list(dic.values())
            if process_l8 == 'y':
                plan[tile_id]["L8_PROC"]["INPUTS"] = list(dic_process.values())
            self.plan = plan

        # Summary
        _logger.info("")
        _logger.info(" -- Summary -- ")
        if ascending_selected:
            _logger.info(" {} ascending S1 products have been downloaded ({} descending)".format(len(s1_prods),
                                                                                                len(s1_prods_desc)))
        else:
            _logger.info(" {} descending S1 products have been downloaded ({} ascending)".format(len(s1_prods),
                                                                                                 len(s1_prods_asc)))
        _logger.info(" {} L8 products have been downloaded".format(len(l8_prods)))

    def write_plan(self, out_file):
        # Write the json
        with open(out_file, "w") as fp:
            json.dump(self.plan, fp, indent=4)
