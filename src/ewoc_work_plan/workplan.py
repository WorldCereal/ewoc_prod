import csv
import json
import logging
import re
import geopandas as gpd
from eotile import eotile_module
from datetime import datetime
from ewoc_work_plan import __version__
from ewoc_work_plan.plan.utils import eodag_prods, is_descending


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
        self._tile_ids = tile_ids
        self._start_date = start_date
        self._end_date = end_date

        self._cloudcover = cloudcover
        if data_provider in ['creodias', 'peps', 'astraea_eod']:
            self._data_provider = data_provider
        else:
            raise ValueError

        ## Filling the plan
        self._plan = dict()
        ## Common MetaData
        self._plan['version'] = str(__version__)
        self._plan['user'] = user
        self._plan['visibility'] = visibility
        self._plan['generated'] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        self._plan['aez_id'] = aez_id
        self._plan['session_start'] = start_date
        self._plan['session_end'] = end_date
        self._plan['season_type'] = season_type
        self._plan['S1_provider'] = data_provider
        self._plan['S2_provider'] = data_provider
        #  TODO : Fill or change the provider translator system
        provider_translator_L8_dict = {'creodias': 'usgs_AWS', 'peps': 'peps', 'astraea_eod': 'astraea_eod'}
        self._plan['L8_provider'] = provider_translator_L8_dict[data_provider]


        ## Addind tiles
        tiles_plan=list()

        for i, tile_id in enumerate(tile_ids):
            tile_plan = dict()
            tile_plan['tile_id'] = tile_id
            s1_prd_ids, orbit_dir = self._identify_s1(tile_id, eodag_config_filepath=eodag_config_filepath)
            s2_prd_ids = self._identify_s2(tile_id, eodag_config_filepath=eodag_config_filepath)
            l8_prd_ids = self._identify_l8(tile_id, l8_sr=l8_sr, eodag_config_filepath=eodag_config_filepath)
            tile_plan['s1_ids'] = s1_prd_ids
            tile_plan['S1_orbit_dir'] = orbit_dir
            tile_plan['S1_nb'] = len(s1_prd_ids)
            tile_plan['s2_ids'] = s2_prd_ids
            tile_plan['s2_nb'] = len(s2_prd_ids)
            tile_plan['l8_ids'] = l8_prd_ids
            tile_plan['l8_nb'] = len(l8_prd_ids)
            if isinstance(l8_sr, list) and len(l8_sr) == len(tile_ids):
                tile_plan["L8_enable_sr"]= l8_sr[i]
            elif isinstance(l8_sr, list):
                logger.error(f"Input l8_sr should be of size {len(tile_ids)}")
                raise ValueError
            else:
                tile_plan["L8_enable_sr"] = l8_sr


            tiles_plan.append(tile_plan)
        
        self._plan['tiles']= tiles_plan


    def _identify_s1(self,tile_id, eodag_config_filepath=None):
        df = eotile_module.main(tile_id)[0]
        s1_prods_types = {"peps": "S1_SAR_GRD", 
                          "astraea_eod": "sentinel1_l1c_grd",
                          "creodias":"S1_SAR_GRD"}
        s1_prods_full = eodag_prods( df, 
                                self._start_date, self._end_date, 
                                self._data_provider, 
                                s1_prods_types[self._data_provider], 
                                eodag_config_filepath)
        
        s1_prods_desc = [s1_prod for s1_prod in s1_prods_full if is_descending(s1_prod, self._data_provider)]
        s1_prods_asc = [s1_prod for s1_prod in s1_prods_full if not is_descending(s1_prod, self._data_provider)]
        logger.info('Number of descending products: {}'.format(len(s1_prods_desc)))
        logger.info('Number of ascending products: {}'.format(len(s1_prods_asc)))

        # Filtering by orbit type
        if len(s1_prods_desc) >= len(s1_prods_asc):
            s1_prods = s1_prods_desc
            orbit_dir = "DES"
        else:
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
        df = eotile_module.main(tile_id)[0]
        s2_prods_types = {"peps": "S2_MSI_L1C", 
                          "astraea_eod": "sentinel2_l1c", 
                          "creodias": "S2_MSI_L1C"}
        product_type = s2_prods_types[self._data_provider.lower()]
        s2_prods = eodag_prods( df, self._start_date, self._end_date, 
                                self._data_provider, 
                                s2_prods_types[self._data_provider.lower()],
                                eodag_config_filepath, 
                                cloudCover=self._cloudcover)
        s2_prod_ids = list()
        for s2_prod in s2_prods:
            s2_prod_ids.append([s2_prod.properties["id"]])
        return s2_prod_ids

    def _identify_l8(self, tile_id, l8_sr=False, eodag_config_filepath=None):
        l8_prods = eodag_prods( eotile_module.main(tile_id)[0],
                                self._start_date, self._end_date,
                                'astraea_eod',
                                'landsat8_c2l1t1',
                                eodag_config_filepath,
                                cloudCover=self._cloudcover)
        # filter the prods: keep only T1 products
        l8_prods = [prod for prod in l8_prods if prod.properties['id'].endswith(('T1','T1_L1TP'))]
        logger.debug(l8_prods)

        return list()

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
    def from_csv(cls, csv_filepath, start_date, end_date,
                data_provider,
                l8_sr=False, aez_id=0,
                user="EWoC_admin",
                visibility="public",
                season_type="cropland",
                eodag_config_filepath=None, cloudcover=90):
        tile_ids=list()
        with open(csv_filepath) as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                for tile_id in line:
                    tile_ids.append(tile_id)
        return WorkPlan(tile_ids, data_provider, start_date, end_date,
                data_provider,
                l8_sr,
                aez_id,
                user,
                visibility,
                season_type,
                eodag_config_filepath , cloudcover)

    def to_json(self, out_filepath):
        with open(out_filepath, "w") as fp:
            json.dump(self._plan, fp, indent=4)

    def to_ewoc_db(self):
        raise NotImplementedError

if __name__ == "__main__":
    from pathlib import Path
    logging.basicConfig(level=logging.DEBUG)
    #wp2 = WorkPlan.from_aoi(Path("/home/mgerma/Documents/Documents/EODAG/EOTILE/testdata/ewoc/test.shp"),
    #                        "2020-10-01", "2020-10-10", 'creodias', False)
    #wp = WorkPlan(['31TCJ', '31TDJ'], "2020-10-01", "2020-10-30", 'creodias', [False, False])
    wp.to_json(Path('/tmp/wp2.json'))

