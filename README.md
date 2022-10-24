# EWoC ToolBox

The toolbox is in charge to prepare WorkPlan inputs from AEZ information (associated to S2 tiles).

## Link AEZ information to S2 tiles

First step is to link the AEZ information to each s2 tile on the MRGS grid. 
A tile corresponds to an AEZ (the one that covers the most).

```bash
usage: link_aez_tiles.py [-h] [-a AEZ] [-t S2TILES] [-o OUT] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  -a AEZ, --aez AEZ     aez.geojson file
  -t S2TILES, --s2tiles S2TILES
                        s2tile_selection.geojson file
  -o OUT, --out OUT     s2tile_selection_aez.geojson, the s2tile file with aez
                        information
  --debug               Activate Debug Mode
```

## Prepare inputs and launch WorkPlan 

Second step is to prepare WorkPlan inputs before launch.
In order to generate a plan you'll need some information specific to each AEZ :

- season_start, season_end : key dates for a given crop type (season_type)
- season_processing_start, season_processing_end : these parameters will define the time interval of the satellite products search (buffer added before crop emergence)
- annual_processing_start, annual_processing_end : these parameters will be used to process cropmap (it covers one year till season_end)
- wp_processing_start, wp_processing_end : dates that are finally used to generate the workplan (can be either season_processing or annual_processing)
- l8_enable_sr : if True, L8 SR will be used to complete optical time series
- enable_sw : if True, spring wheat map will be produced

### Steps:
- Get the list of tiles that correspond to user needs
- Group tiles by AEZ as one WorkPlan will be generated for each AEZ
- Get and format tiles information needed to launch the WorkPlan 
- Launch WP (need the last version of ewoc_workplan-x.y.z.tar.gz)

Several modes are proposed to extract tiles information :

    * From a tile id (--tile_id)
    * From an AEZ id (--aez_id)
    * From an AOI (area of interest) corresponding to one or several geometries (--user_aoi)
    * From a list of tiles in a geojson file (--user_tiles)
    * From a list of tiles (--user_list_tiles)
    * From a specific date in the past (--prod_start_date)
    * From today's date (default mode ; continuous monitoring)

Args --tile_id, --aez_id, --user_aoi, --user_tiles, --user_list_tiles are optional and must not be used at the same time. Season_type is mandatory for these 5 modes (if metaseason mode is deactivated ; see above).
If none of them are declared, a date will be used and season_type becomes unused.

### Metaseason mode:
I addition, it is possible to activate a "metaseason" mode with argument --metaseason (will be used in production). It corresponds to a custom season that will cover all the seasons. This mode requires either --tile_id, --aez_id, --user_aoi, --user_tiles or --user_list_tiles but it does not work with --prod_start_date and continuous monitoring mode. The --season_type is not used when --metaseason is activated.

### Orbit file:
Do not forget to use the sentinel 1 orbit file if you want to force some tiles orbit direction. This can be activated using the --orbit option

### Full help (ewoc_prod):
```bash
usage: ewoc_prod [-h] [-in S2TILES_AEZ_FILE] [-pd PROD_START_DATE]
                 [-t TILE_ID] [-aid AEZ_ID] [-aoi USER_AOI] [-ut USER_TILES]
                 [-ult USER_LIST_TILES [USER_LIST_TILES ...]] [-m]
                 [-m_yr METASEASON_YEAR] [-season SEASON_TYPE]
                 [-s2prov S2_DATA_PROVIDER [S2_DATA_PROVIDER ...]]
                 [-strategy S2_STRATEGY [S2_STRATEGY ...]] [-u USER]
                 [-visib VISIBILITY] [-cc CLOUDCOVER]
                 [-min_prods MIN_NB_PRODS] [-orbit ORBIT_FILE] [-rm_l1c]
                 [-o OUTPUT_PATH] [-s3 S3_BUCKET] [-k S3_KEY] [-no_s3] [-v]
                 [-vv]

optional arguments:
  -h, --help            show this help message and exit
  -in S2TILES_AEZ_FILE, --s2tiles_aez_file S2TILES_AEZ_FILE
                        MGRS grid that contains for each included tile the
                        associated aez information (geojson file)
  -pd PROD_START_DATE, --prod_start_date PROD_START_DATE
                        Production start date - format YYYY-MM-DD
  -t TILE_ID, --tile_id TILE_ID
                        Tile id for production (e.g. '31TCJ')
  -aid AEZ_ID, --aez_id AEZ_ID
                        AEZ region id for production (e.g. '46172')
  -aoi USER_AOI, --user_aoi USER_AOI
                        User AOI for production (geojson file)
  -ut USER_TILES, --user_tiles USER_TILES
                        User tiles id for production (geojson file)
  -ult USER_LIST_TILES [USER_LIST_TILES ...], --user_list_tiles USER_LIST_TILES [USER_LIST_TILES ...]
                        User tiles id for production (e.g. 38KKG 38KLF 38KLG)
  -m, --metaseason      Active the metaseason mode that cover all seasons
  -m_yr METASEASON_YEAR, --metaseason_year METASEASON_YEAR
                        Year of the season to process in the metaseason mode
                        (e.g. 2021 to process 2020/2021)
  -season SEASON_TYPE, --season_type SEASON_TYPE
                        Season type (winter, summer1, summer2)
  -s2prov S2_DATA_PROVIDER [S2_DATA_PROVIDER ...], --s2_data_provider S2_DATA_PROVIDER [S2_DATA_PROVIDER ...]
                        s2 provider (peps/creodias/astraea_eod/aws)
  -strategy S2_STRATEGY [S2_STRATEGY ...], --s2_strategy S2_STRATEGY [S2_STRATEGY ...]
                        Fusion strategy (L2A,L1C)
  -u USER, --user USER  Username
  -visib VISIBILITY, --visibility VISIBILITY
                        Visibility, public or private
  -cc CLOUDCOVER, --cloudcover CLOUDCOVER
                        Cloudcover parameter
  -min_prods MIN_NB_PRODS, --min_nb_prods MIN_NB_PRODS
                        Yearly minimum number of products
  -orbit ORBIT_FILE, --orbit_file ORBIT_FILE
                        Force s1 orbit direction for a list of tiles
  -rm_l1c, --remove_l1c
                        Remove L1C products or not
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        Output path for json files
  -s3 S3_BUCKET, --s3_bucket S3_BUCKET
                        Name of s3 bucket to upload wp
  -k S3_KEY, --s3_key S3_KEY
                        Key of s3 bucket to upload wp
  -no_s3, --no_upload_s3
                        Skip the upload of json files to s3 bucket
  -v, --verbose         set loglevel to INFO
  -vv, --very-verbose   set loglevel to DEBUG
```

### Examples:
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv (continuous mode)
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -pd '2021-10-10'
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -t '37MBS' -season winter
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -aid '37189' -season winter
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -aoi /path/to/selected_countries.geojson -season winter

    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -t '37MBS' -m (metaseason mode on a tile)
    * ewoc_prod -v -in /path/to/s2tile_selection_aez.geojson -orbit /path/to/s1_orbit_tiles_ASC_DES_prod.csv -aid '37189' -m (metaseason mode on a AEZ) 

## Use the supervisor

A random error occured several times while using ewoc_prod. The supervisor allows to launch ewoc_prod several times until the tiles concerned are produced. It also creates an error_tiles.csv file. If some tiles have not been produced (for a real error ; not random), this file contains the tiles_id and the associated errors (empty file if all tiles are done)

### Full help (supervisor):
```bash
usage: supervisor.py [-h] [-in S2TILES_AEZ_FILE]
                     [-aez AEZ_LIST [AEZ_LIST ...]] [-orbit ORBIT_FILE]
                     [-m_yr METASEASON_YEAR] [-merge] [-o OUTPUT_PATH] [-v]
                     [-vv]

optional arguments:
  -h, --help            show this help message and exit
  -in S2TILES_AEZ_FILE, --s2tiles_aez_file S2TILES_AEZ_FILE
                        MGRS grid that contains for each included tile the
                        associated aez information (geojson file)
  -aez AEZ_LIST [AEZ_LIST ...], --aez_list AEZ_LIST [AEZ_LIST ...]
                        List of aez to process
  -orbit ORBIT_FILE, --orbit_file ORBIT_FILE
                        Force s1 orbit direction for a list of tiles
  -m_yr METASEASON_YEAR, --metaseason_year METASEASON_YEAR
                        Year of the season to process in the metaseason mode
                        (e.g. 2021 to process 2020/2021)
  -merge, --force_merge
                        Force merging tiles json into aez file
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        Output path for json files
  -v, --verbose         set loglevel to INFO
  -vv, --very-verbose   set loglevel to DEBUG
```

### Steps for production (example for AEZ 34119 in the RUN6 for year 2021):
- Preparation :
    * connect on creodias vm (mng)
    * create config.sh (containing AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) in ~/dev
    * create venv with EWOC code in ~/dev
    * move eodag_config.yml in ~/dev/.venv/lib (it contains creodias and astraea_eod credientials)
    * check supervisor.py (s2prov, strategy, user etc.) and change if needed
    * upload the files : ~/dev/s2tile_selection_aez_prod_details_RUN6.geojson, ~/dev/s1_orbit_tiles_ASC_DES_prod.csv
    * create output directory : ~/dev/WorkPlan/prod_RUN6
- Source files : 
    * cd ~/dev
    * source config.sh
    * source .venv/bin/activate
- Run supervisor :
    * cd ~/dev/.venv/lib/python3.6/site-packages/ewoc_prod/
    * nohup python supervisor.py -v -aez 34119 -in ~/dev/s2tile_selection_aez_prod_details_RUN6.geojson -orbit ~/dev/s1_orbit_tiles_ASC_DES_prod.csv -o ~/dev/WorkPlan/prod_RUN6 2>&1 > ~/dev/WorkPlan/prod_RUN6/log/log_34119.txt &
- Check number of tiles produced:
    * ls ~/dev/WorkPlan/prod_RUN6/34119/json | wc -l
- Check final json creation:
    * ls ~/dev/WorkPlan/prod_RUN6/34119/*.json
- If one tile is missing:
    * check and suppress error file : ~/dev/WorkPlan/prod_RUN6/error_tiles_34119.csv
    * run supervisor in merge mode : nohup python supervisor.py -v -aez 34119 -in ~/dev/s2tile_selection_aez_prod_details_RUN6.geojson -orbit ~/dev/s1_orbit_tiles_ASC_DES_prod.csv -o ~/dev/WorkPlan/prod_RUN6 -merge 2>&1 > ~/dev/WorkPlan/prod_RUN6/log/log_34119_merge.txt &
- Save final json on local machine and put it on aws vm (mng) using scp
