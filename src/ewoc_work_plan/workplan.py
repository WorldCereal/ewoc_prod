import csv
import json
import logging
import re
import tempfile
from datetime import datetime

import geopandas as gpd
from eotile import eotile_module
from ewoc_db.fill.fill_db import main as main_ewoc_db
from shapely.wkt import dumps

from ewoc_work_plan import __version__
from ewoc_work_plan.remote.landsat_cloud_mask import Landsat_Cloud_Mask
from ewoc_work_plan.reproc import reproc_wp
from ewoc_work_plan.s2prods import run_multiple_cross_provider
from ewoc_work_plan.utils import (
    eodag_prods,
    get_path_row,
    greatest_timedelta,
    sort_sar_products,
)

logger = logging.getLogger(__name__)


class WorkPlan:
    def __init__(
        self,
        tile_ids,
        meta_dict,
        wp_processing_start,
        wp_processing_end,
        data_provider,
        strategy,
        l8_sr=False,
        aez_id=0,
        user="EWoC_admin",
        visibility="public",
        season_type="winter",
        detector_set="winterwheat, irrigation",
        enable_sw=False,
        eodag_config_filepath=None,
        cloudcover=90,
        min_nb_prods=50,
    ) -> None:

        self._cloudcover = cloudcover
        self.strategy = strategy
        if not set(data_provider).issubset(
            ["creodias", "peps", "astraea_eod", "aws", "aws_cog"]
        ):
            raise ValueError("Incorrect data provider")
        # Filling the plan
        self._plan = dict()
        #  Common MetaData
        self._plan["version"] = str(__version__)
        self._plan["user"] = user
        self._plan["visibility"] = visibility
        self._plan["generated"] = (
            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        self._plan["aez_id"] = aez_id
        self._plan["season_type"] = season_type
        self._plan["enable_sw"] = enable_sw
        self._plan["detector_set"] = detector_set
        self._plan["wp_processing_start"] = wp_processing_start
        self._plan["wp_processing_end"] = wp_processing_end
        self._plan["s1_provider"] = "creodias"
        self._plan["s2_provider"] = data_provider
        # Only L8 C2L2 provider supported for now is aws usgs
        self._plan["l8_provider"] = "usgs_satapi_aws"
        self._plan["yearly_prd_threshold"] = min_nb_prods
        if not meta_dict:
            logger.warning("The meta dictionary is empty!!")
        # Addind tiles
        tiles_plan = list()

        for i, tile_id in enumerate(tile_ids):
            tile_plan = dict()
            tile_plan["tile_id"] = tile_id
            s2_tile = eotile_module.main(tile_id)[0]
            s1_prd_ids, orbit_dir = self._identify_s1(
                s2_tile, eodag_config_filepath=eodag_config_filepath
            )
            s2_prd_ids = self._identify_s2(
                tile_id, s2_tile, eodag_config_filepath=eodag_config_filepath
            )
            l8_prd_ids = self._identify_l8(
                s2_tile, l8_sr=l8_sr, eodag_config_filepath=eodag_config_filepath
            )
            tile_plan["s1_ids"] = s1_prd_ids
            tile_plan["s1_orbit_dir"] = orbit_dir
            tile_plan["s1_nb"] = len(s1_prd_ids)
            tile_plan["s2_ids"] = s2_prd_ids
            tile_plan["s2_nb"] = len(s2_prd_ids)
            tile_plan["l8_ids"] = l8_prd_ids
            tile_plan["l8_nb"] = len(l8_prd_ids)
            tile_plan["geometry"] = dumps(s2_tile.iloc[0]["geometry"])
            tile_plan["epsg"] = "epsg:4326"
            if isinstance(l8_sr, list) and len(l8_sr) == len(tile_ids):
                tile_plan["l8_enable_sr"] = l8_sr[i]
            elif isinstance(l8_sr, list):
                logger.error("Input l8_sr should be of size %s", len(tile_ids))
                raise ValueError
            else:
                tile_plan["l8_enable_sr"] = l8_sr

            if len(s1_prd_ids) == 0:
                logger.error("No relevant S1 product found for %s", tile_id)
                raise ValueError
            if len(s2_prd_ids) == 0:
                logger.error("No relevant S2 product found for %s", tile_id)
                raise ValueError
            if len(l8_prd_ids) == 0:
                logger.error("No relevant L8 product found for %s", tile_id)
                raise ValueError

            tiles_plan.append(tile_plan)

        self._plan["tiles"] = tiles_plan

    def __str__(self):
        return json.dumps(self._plan, indent=4, sort_keys=False)

    def _identify_s1(self, s2_tile, eodag_config_filepath=None):
        s1_prods_types = {
            "peps": "S1_SAR_GRD",
            "astraea_eod": "sentinel1_l1c_grd",
            "creodias": "S1_SAR_GRD",
        }
        s1_prods_request = eodag_prods(
            s2_tile,
            self._plan["wp_processing_start"],
            self._plan["wp_processing_end"],
            self._plan["s1_provider"],
            s1_prods_types[self._plan["s1_provider"]],
            eodag_config_filepath,
        )
        print(len(s1_prods_request))
        # filter out undesirable products
        s1_prods_desc, s1_prods_asc = sort_sar_products(s1_prods_request,self._plan["s1_provider"])
        logger.info("Number of descending products: %s", len(s1_prods_desc))
        logger.info("Number of ascending products: %s", len(s1_prods_asc))

        logger.debug("ASCENDING:")
        td_asc = greatest_timedelta(
            s1_prods_asc,
            self._plan["wp_processing_start"],
            self._plan["wp_processing_end"],
        )
        logger.debug("DESCENDING:")
        td_desc = greatest_timedelta(
            s1_prods_desc,
            self._plan["wp_processing_start"],
            self._plan["wp_processing_end"],
        )

        logger.info("The greatest time delta for ASCENTING product is %s", td_asc)
        logger.info("The greatest time delta for DESCENDING product is %s", td_desc)

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
        logger.info("%s products are grouped in %s dates", len(s1_prods), len(dic))

        return list(dic.values()), orbit_dir

    def _identify_s2(self, tile_id, s2_tile, eodag_config_filepath=None):
        s2_prods_ids = run_multiple_cross_provider(
            tile_id,
            self._plan["wp_processing_start"],
            self._plan["wp_processing_end"],
            100,
            self._cloudcover,
            self._plan["yearly_prd_threshold"],
            eodag_config_filepath,
            providers=self._plan["s2_provider"],
            strategy=self.strategy,
        )
        return s2_prods_ids

    def _identify_l8(self, s2_tile, l8_sr=False, eodag_config_filepath=None):
        l8_prods = eodag_prods(
            s2_tile,
            self._plan["wp_processing_start"],
            self._plan["wp_processing_end"],
            self._plan["l8_provider"],
            "LANDSAT_C2L2_SR",
            eodag_config_filepath,
            cloud_cover=self._cloudcover,
        )
        # filter the prods: keep only T1 products
        # l8_prods = [prod for prod in l8_prods if
        # prod.properties['id'].endswith(('T1','T1_L1TP'))]
        logger.debug(l8_prods)

        # Group by same path & date
        dic = {}
        for l8_prod in l8_prods:
            # Prevent LE07 and LC09 to be randomly included
            if l8_prod.properties["id"][:4] != 'LC08':
                continue

            date = (
                l8_prod.properties["startTimeFromAscendingNode"]
                .split("T")[0]
                .replace("-", "")
            )
            path, row = get_path_row(l8_prod, self._plan["l8_provider"].lower())
            key = path + date
            l8_mask = Landsat_Cloud_Mask(path, row, date)
            if l8_mask.mask_exists():
                l8_id = l8_prod.properties["id"]
                if l8_id.endswith("_SR"):
                    l8_id = l8_id[:-3]
                # f"s3://{l8_mask.bucket}/{l8_mask.tirs_10_key}"
                if key in dic and len(l8_id) > 0:
                    dic[key].append(l8_id)
                elif len(l8_id) > 0:
                    dic[key] = [l8_id]
            else:
                logger.warning("Missing product %s", l8_prod.properties["id"])

        return list(dic.values())

    @classmethod
    def from_aoi(
        cls,
        aoi_filepath,
        season_start,
        season_end,
        season_processing_start,
        season_processing_end,
        annual_processing_start,
        annual_processing_end,
        wp_processing_start,
        wp_processing_end,
        data_provider,
        strategy,
        l8_sr=False,
        aez_id=0,
        user="EWoC_admin",
        visibility="public",
        season_type="winter",
        detector_set="winterwheat, irrigation",
        enable_sw=False,
        eodag_config_filepath=None,
        cloudcover=90,
        min_nb_prods=50,
    ):
        supported_format = [".shp", ".geojson", ".gpkg"]
        if aoi_filepath.suffix in supported_format:
            # Vector file to get bbox
            geometries = gpd.read_file(aoi_filepath)
            # Re-project geometry if needed
            if geometries.crs.to_epsg() != 4326:
                geometries = geometries.to_crs(4326)
            s2_tiles = []
            for geometry in geometries.geometry:
                current_s2_tiles = eotile_module.main(str(geometry))[0]
                for s2_tile in current_s2_tiles["id"]:
                    if s2_tile not in s2_tiles:
                        s2_tiles.append(s2_tile)
            return WorkPlan(
                s2_tiles,
                season_start,
                season_end,
                season_processing_start,
                season_processing_end,
                annual_processing_start,
                annual_processing_end,
                wp_processing_start,
                wp_processing_end,
                data_provider,
                strategy,
                l8_sr,
                aez_id,
                user,
                visibility,
                season_type,
                detector_set,
                enable_sw,
                eodag_config_filepath,
                min_nb_prods,
                cloudcover,
            )
        else:
            logging.critical(
                "%s is not supported (%s)", aoi_filepath.name, supported_format
            )
            raise ValueError

    @classmethod
    def load(cls, wp_filepath):
        wp = cls.__new__(cls)
        with open(wp_filepath, encoding="utf-8") as raw_workplan:
            wp._plan = json.load(raw_workplan)
        return wp

    @classmethod
    def from_csv(
        cls,
        csv_filepath,
        season_start,
        season_end,
        season_processing_start,
        season_processing_end,
        annual_processing_start,
        annual_processing_end,
        wp_processing_start,
        wp_processing_end,
        data_provider,
        strategy,
        l8_sr=False,
        aez_id=0,
        user="EWoC_admin",
        visibility="public",
        season_type="winter",
        detector_set="winterwheat, irrigation",
        enable_sw=False,
        eodag_config_filepath=None,
        cloudcover=90,
        min_nb_prods=50,
    ):
        tile_ids = list()
        with open(csv_filepath, encoding="latin-1") as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                for tile_id in line:
                    tile_ids.append(tile_id)

        return cls(
            tile_ids,
            season_start,
            season_end,
            season_processing_start,
            season_processing_end,
            annual_processing_start,
            annual_processing_end,
            wp_processing_start,
            wp_processing_end,
            data_provider,
            strategy,
            l8_sr=l8_sr,
            aez_id=aez_id,
            user=user,
            visibility=visibility,
            season_type=season_type,
            detector_set=detector_set,
            enable_sw=enable_sw,
            eodag_config_filepath=eodag_config_filepath,
            cloudcover=cloudcover,
            min_nb_prods=min_nb_prods,
        )

    def to_json(self, out_filepath):
        with open(out_filepath, "w", encoding="utf-8") as json_file:
            json.dump(self._plan, json_file, indent=4)

    def to_ewoc_db(self):
        temporary_json_file = tempfile.NamedTemporaryFile(suffix=".json")
        self.to_json(temporary_json_file.name)
        main_ewoc_db(temporary_json_file.name)
        temporary_json_file.close()

    def reproc(self, bucket, path):
        new_wp = WorkPlan.__new__(WorkPlan)
        new_wp._plan = reproc_wp(bucket, self._plan, path)
        return new_wp
