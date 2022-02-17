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
- l8_enable_sr : if True, L8 SR will be used to complete optical time series
- enable_sw : if True, spring wheat map will be produced

### Steps:
- Get the list of tiles that correspond to user needs
- Group tiles by AEZ as one WorkPlan will be generated for each AEZ
- Get and format tiles information needed to launch the WorkPlan 
- Laucn WP (need the last version of ewoc_workplan-x.y.z.tar.gz)

Several modes are proposed to extract tiles information :
    * From a tile id (--tile_id)
    * From an AEZ id (--aez_id)
    * From an AOI (area of interest) corresponding to one or several geometries (--user_aoi)
    * From a specific date in the past (--prod_start_date)
    * From today's date (default mode ; continuous monitoring)

Args --tile_id, --aez_id, --user_aoi are optional and must not be used at the same time. Season_type is mandatory for these 3 modes.
If none of them are declared, a date will be used and season_type becomes unused.

Full help

```bash
usage: tiles_2_workplan.py [-h] [-in S2TILES_AEZ_FILE] [-pd PROD_START_DATE]
                           [-t TILE_ID] [-aid AEZ_ID] [-aoi USER_AOI]
                           [-season SEASON_TYPE] [-v] [-vv]

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
  -season SEASON_TYPE, --season_type SEASON_TYPE
                        Season type (winter, summer1, summer2)
  -v, --verbose         set loglevel to INFO
  -vv, --very-verbose   set loglevel to DEBUG
```
