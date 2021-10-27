import csv
from datetime import datetime
import json
import logging
import re
import tempfile

import geopandas as gpd
from eotile import eotile_module
from ewoc_db.fill.fill_db import main as main_ewoc_db

from ewoc_work_plan import __version__
from ewoc_work_plan.utils import eodag_prods, is_descending, get_path_row, greatest_timedelta
from ewoc_work_plan.reproc import reproc_wp
from ewoc_work_plan.remote.landsat_cloud_mask import Landsat_Cloud_Mask

logger = logging.getLogger(__name__)

class WorkPlan:
    #  TODO : passer les valeurs par défaut dans la cli (ou les supprimer ?)
    def __init__(self, tile_ids,
                start_date, end_date,
                data_provider,
                l8_sr=False, aez_id=0,
                user="EWoC_admin",
                visibility="public",
                season_type="cropland",
                eodag_config_filepath=None, cloudcover=90) -> None:


        self._cloudcover = cloudcover
        if data_provider not in ['creodias', 'peps', 'astraea_eod']:
            raise ValueError

        ## Filling the plan
        self._plan = dict()
        ## Common MetaData
        self._plan['version'] = str(__version__)
        self._plan['user'] = user
        self._plan['visibility'] = visibility
        self._plan['generated'] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        self._plan['aez_id'] = aez_id
        self._plan['season_start'] = start_date
        self._plan['season_end'] = end_date
        self._plan['season_type'] = season_type
        self._plan['s1_provider'] = data_provider
        self._plan['s2_provider'] = data_provider
        #  TODO : Fill or change the provider translator system
        provider_translator_l8_dict = {'creodias': 'usgs_AWS',
                                       'peps': 'peps',
                                       'astraea_eod': 'astraea_eod'}
        self._plan['l8_provider'] = provider_translator_l8_dict[data_provider]

        ## Addind tiles
        tiles_plan=list()

        for i, tile_id in enumerate(tile_ids):
            tile_plan = dict()
            tile_plan['tile_id'] = tile_id
            s1_prd_ids, orbit_dir = self._identify_s1(tile_id,
                eodag_config_filepath=eodag_config_filepath)
            s2_prd_ids = self._identify_s2(tile_id, eodag_config_filepath=eodag_config_filepath)
            l8_prd_ids = self._identify_l8(tile_id, eodag_config_filepath=eodag_config_filepath)
            tile_plan['s1_ids'] = s1_prd_ids
            tile_plan['s1_orbit_dir'] = orbit_dir
            tile_plan['s1_nb'] = len(s1_prd_ids)
            tile_plan['s2_ids'] = s2_prd_ids
            tile_plan['s2_nb'] = len(s2_prd_ids)
            tile_plan['l8_ids'] = l8_prd_ids
            tile_plan['l8_nb'] = len(l8_prd_ids)
            if isinstance(l8_sr, list) and len(l8_sr) == len(tile_ids):
                tile_plan["l8_enable_sr"]= l8_sr[i]
            elif isinstance(l8_sr, list):
                logger.error("Input l8_sr should be of size %s", len(tile_ids))
                raise ValueError
            else:
                tile_plan["l8_enable_sr"] = l8_sr

            tiles_plan.append(tile_plan)

        self._plan['tiles']= tiles_plan


    def __str__(self):
        return json.dumps(self._plan, indent=4, sort_keys=False)


    def _identify_s1(self,tile_id, eodag_config_filepath=None):
        s2_tile_df = eotile_module.main(tile_id)[0]
        s1_prods_types = {"peps": "S1_SAR_GRD",
                          "astraea_eod": "sentinel1_l1c_grd",
                          "creodias":"S1_SAR_GRD"}
        s1_prods_full = eodag_prods( s2_tile_df,
                                self._plan['season_start'], self._plan['season_end'],
                                self._plan['s1_provider'],
                                s1_prods_types[self._plan['s1_provider']],
                                eodag_config_filepath)
        s1_prods_desc = [s1_prod for s1_prod in s1_prods_full if is_descending(s1_prod, self._plan['s1_provider'])]
        s1_prods_asc = [s1_prod for s1_prod in s1_prods_full if not is_descending(s1_prod, self._plan['s1_provider'])]
        logger.info('Number of descending products: %s', len(s1_prods_desc))
        logger.info('Number of ascending products: %s', len(s1_prods_asc))

        td_asc = greatest_timedelta(s1_prods_asc, self._plan['season_start'], self._plan['season_end'])
        td_desc = greatest_timedelta(s1_prods_desc, self._plan['season_start'], self._plan['season_end'])

        # Filtering by orbit type
        # Selecting the least time_delta
        if td_asc >= td_desc:
            logger.info("Descending products where selected due to their repartition")
            s1_prods = s1_prods_desc
            orbit_dir = "DES"
        else:
            logger.info("Ascending products where selected due to their repartition")
            s1_prods = s1_prods_asc
            orbit_dir = "ASC"

        # Group by same acquisition date
        dic = {}
        for s1_prod in s1_prods:
            date = re.split("_|T", s1_prod.properties["id"])[4]
            if date in dic and len(s1_prod.properties["id"]) > 0:
                dic[date].append(s1_prod.properties["id"])
            elif len(s1_prod.properties["id"]) > 0:
                dic[date] = [s1_prod.properties["id"]]

        return list(dic.values()), orbit_dir


    def _identify_s2(self, tile_id, eodag_config_filepath=None):
        s2_tile_df = eotile_module.main(tile_id)[0]
        s2_prods_types = {"peps": "S2_MSI_L1C",
                          "astraea_eod": "sentinel2_l1c",
                          "creodias": "S2_MSI_L1C"}
        s2_prods = eodag_prods( s2_tile_df, self._plan['season_start'], self._plan['season_end'],
                                self._plan['s1_provider'],
                                s2_prods_types[self._plan['s1_provider'].lower()],
                                eodag_config_filepath,
                                cloud_cover=self._cloudcover)
        s2_prod_ids = list()
        for s2_prod in s2_prods:
            if tile_id in s2_prod.properties["id"]:
                s2_prod_ids.append([s2_prod.properties["id"]])
        return s2_prod_ids

    def _identify_l8(self, tile_id, eodag_config_filepath=None):
        l8_prods = eodag_prods( eotile_module.main(tile_id)[0],
                                self._plan['season_start'], self._plan['season_end'],
                                'astraea_eod',
                                'landsat8_c2l1t1',
                                eodag_config_filepath,
                                cloud_cover=self._cloudcover)
        # filter the prods: keep only T1 products
        l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith(('T1','T1_L1TP'))]
        logger.debug(l8_prods)

        # Group by same path & date
        dic = {}
        for l8_prod in l8_prods:
            date = (l8_prod.properties["startTimeFromAscendingNode"].split("T")[0].replace("-", ""))
            path, row = get_path_row(l8_prod, 'astraea_eod'.lower()) # TODO change 'astraea_eod' to real l8 provider
            key = path + date
            l8_mask = Landsat_Cloud_Mask(path, row, date)
            if l8_mask.mask_exists():
                l8_id = l8_prod.properties['id']
                #f"s3://{l8_mask.bucket}/{l8_mask.tirs_10_key}"
                if key in dic and len(l8_id) > 0:
                    dic[key].append(l8_id)
                elif len(l8_id) > 0:
                    dic[key] = [l8_id]
            else:
                logger.warning("Missing product %s", l8_prod.properties['id'])

        return list(dic.values())

    @classmethod
    def from_aoi(cls, aoi_filepath,
                 start_date, end_date,
                 data_provider,
                 l8_sr=False, aez_id=0,
                 user="EWoC_admin",
                 visibility="public",
                 season_type="cropland",
                 eodag_config_filepath=None, cloudcover=90):
        supported_format=['.shp', '.geojson', '.gpkg']
        if aoi_filepath.suffix in supported_format:
            # Vector file to get bbox
            geometries = gpd.read_file(aoi_filepath)
            # Re-project geometry if needed
            if geometries.crs.to_epsg() != 4326:
                geometries = vec.to_crs(4326)
            s2_tiles = []
            for geometry in geometries.geometry:
                current_s2_tiles = eotile_module.main(str(geometry))[0]
                for s2_tile in current_s2_tiles["id"]:
                    if s2_tile not in s2_tiles:
                        s2_tiles.append(s2_tile)
            return WorkPlan(s2_tiles,
                            start_date, end_date,
                            data_provider,
                            l8_sr,
                            aez_id,
                            user,
                            visibility,
                            season_type,
                            eodag_config_filepath , cloudcover)
        else:
            logging.critical('%s is not supported (%s)', aoi_filepath.name,
                                                         supported_format)
            raise ValueError


    @classmethod
    def load(cls, wp_filepath):
        wp = cls.__new__(cls)
        with open(wp_filepath, encoding='utf-8') as raw_workplan:
            wp._plan = json.load(raw_workplan)
        return wp


    @classmethod
    def from_csv(cls, csv_filepath, start_date, end_date,
                data_provider,
                l8_sr=False, aez_id=0,
                user="EWoC_admin",
                visibility="public",
                season_type="cropland",
                eodag_config_filepath=None, cloudcover=90):
        tile_ids=list()
        with open(csv_filepath,encoding="latin-1") as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                for tile_id in line:
                    tile_ids.append(tile_id)

        return cls(tile_ids, start_date, end_date,
                data_provider,
                l8_sr=l8_sr,
                aez_id=aez_id,
                user=user,
                visibility=visibility,
                season_type=season_type,
                eodag_config_filepath=eodag_config_filepath,
                cloudcover=cloudcover)

    def to_json(self, out_filepath):
        with open(out_filepath, "w", encoding='utf-8') as json_file:
            json.dump(self._plan, json_file, indent=4)

    def to_ewoc_db(self):
        temporary_json_file = tempfile.NamedTemporaryFile(suffix='.json')
        self.to_json(temporary_json_file.name)
        main_ewoc_db(temporary_json_file.name)
        temporary_json_file.close()


    def reproc(self, bucket, path):
        new_wp = WorkPlan.__new__(WorkPlan)
        new_wp._plan = reproc_wp(bucket, self._plan, path)
        return new_wp
