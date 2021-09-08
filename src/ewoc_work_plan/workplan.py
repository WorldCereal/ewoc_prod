import csv
import json
import logging
import re

from eotile import eotile_module

from ewoc_work_plan import __version__
from ewoc_work_plan.plan.utils import eodag_prods, is_descending


logger = logging.getLogger(__name__)

class WorkPlan:
    def __init__(self, tile_ids,
                start_date, end_date,
                data_provider, 
                l8_sr = False,
                eodag_config_filepath=None, cloudcover=90) -> None:
        self._tile_ids = tile_ids
        self._start_date= start_date
        self._end_date= end_date
        if data_provider in ['creodias', 'peps', 'astraea_eod']:
            self._data_provider = data_provider
        else:
            raise ValueError
        self._cloudcover = cloudcover
        
        self._plan = dict()
        self._plan['version'] = str(__version__)
        tiles_plan=list()

        for tile_id in tile_ids:
            tile_plan = dict()
            tile_plan['tile_id'] = tile_id    
            s1_prd_ids = self._identify_s1(tile_id, eodag_config_filepath=eodag_config_filepath)
            s2_prd_ids = self._identify_s2(tile_id, eodag_config_filepath=eodag_config_filepath)
            l8_prd_ids = self._identify_l8(tile_id, l8_sr=l8_sr, eodag_config_filepath=eodag_config_filepath)
            tile_plan['s1'] = s1_prd_ids
            tile_plan['s2'] = s2_prd_ids
            tile_plan['l8'] = l8_prd_ids

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
        else:
            s1_prods = s1_prods_asc

        # Group by same acquisition date
        dic = {}
        for s1_prod in s1_prods:
            date = re.split("_|T", s1_prod.properties["id"])[4]
            if date in dic and len(s1_prod.properties["id"]) > 0:
                dic[date].append(s1_prod.properties["id"])
            elif len(s1_prod.properties["id"]) > 0:
                dic[date] = [s1_prod.properties["id"]]

        return list(dic.values())


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
    def from_aoi(cls, aoi_filepath):
        supported_format=['.shp', '.geojson', '.gpkg']
        if aoi_filepath.suffix() in supported_format:
            raise NotImplementedError
        else:
            logging.critical('%s is not supported (%s)', aoi_filepath.name,
                                                         supported_format)
            raise ValueError

    @classmethod
    def from_csv(cls, csv_filepath, data_provider, 
                l8_sr = False, eodag_config_filepath=None, cloudcover=90):
        tile_ids=list()
        with open(csv_filepath) as csvfile:
            reader = csv.reader(csvfile)
            for line in reader:
                for tile_id in line:
                    tile_ids.append(tile_id)
        return WorkPlan(tile_ids, data_provider, 
                        l8_sr=l8_sr, eodag_config_filepath=eodag_config_filepath,
                        cloudcover=90)

    def to_json(self, out_filepath):
        with open(out_filepath, "w") as fp:
            json.dump(self._plan, fp, indent=4)

    def to_ewoc_db(self):
        raise NotImplementedError

if __name__ == "__main__":
    from datetime import date
    from pathlib import Path
    logging.basicConfig(level=logging.DEBUG)
    WorkPlan(['31TCJ', '31TDJ'], "2020-10-01", "2020-10-30", 'creodias').to_json(Path('/tmp/wp.json'))
