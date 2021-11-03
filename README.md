# EWoC work plan generation

The aim of this tool is to prepare and organize the satellite products that will be processed by the EWoC system.
The generated json plan is the starting point for the Argo workflows.

## The anatomy of a plan

A plan is a json file with a list of S2 MGRS tiles and the corresponding satellite products to process.

```json
{
    "version": "0.1.1",
    "user": "EWoC_admin",
    "visibility": "public",
    "generated": "2021-09-10 17:27:27 CEST",
    "aez_id": 0,
    "season_start": "2020-10-20",
    "season_end": "2020-10-30",
    "season_type": "cropland",
    "S1_provider": "creodias",
    "S2_provider": "creodias",
    "L8_provider": "usgs_AWS",
    "tiles": [
        {
            "tile_id": "31TCJ",
            "s1_ids": [
                [
                    "S1A_IW_GRDH_1SDV_20201029T060104_20201029T060129_035007_041562_76A1",
                    "S1A_IW_GRDH_1SDV_20201029T060048_20201029T060113_035007_041562_DAC7",
                    "S1A_IW_GRDH_1SDV_20201029T060039_20201029T060104_035007_041562_9FE9"
                ],
                [
                    "S1B_IW_GRDH_1SDV_20201028T060826_20201028T060851_024009_02DA2A_C6FC",
                    "S1B_IW_GRDH_1SDV_20201028T060826_20201028T060851_024009_02DA2A_31F3",
                    "S1B_IW_GRDH_1SDV_20201028T060801_20201028T060826_024009_02DA2A_CC6C",
                    "S1B_IW_GRDH_1SDV_20201028T060801_20201028T060826_024009_02DA2A_9E22"
                ],
                [
                    "S1B_IW_GRDH_1SDV_20201023T060008_20201023T060033_023936_02D7EE_771D",
                    "S1B_IW_GRDH_1SDV_20201023T060006_20201023T060031_023936_02D7EE_7C33"
                ],
                [
                    "S1A_IW_GRDH_1SDV_20201022T060914_20201022T060939_034905_0411DD_1B4A",
                    "S1A_IW_GRDH_1SDV_20201022T060904_20201022T060929_034905_0411DD_8038",
                    "S1A_IW_GRDH_1SDV_20201022T060849_20201022T060914_034905_0411DD_5D80"
                ]
            ],
            "S1_orbit_dir": "DES",
            "s1_nb": 4,
            "s2_ids": [
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T31TCJ_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T31TDH_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T31TCK_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T31TDJ_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T31TCH_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T30TYQ_20201027T130310"
                ],
                [
                    "S2A_MSIL1C_20201027T105141_N0209_R051_T30TYP_20201027T130310"
                ],
                [
                    "S2B_MSIL1C_20201025T110039_N0209_R094_T30TYP_20201025T120537"
                ],
                [
                    "S2A_MSIL1C_20201024T104121_N0209_R008_T31TDH_20201024T141709"
                ],
                [
                    "S2A_MSIL1C_20201024T104121_N0209_R008_T31TCJ_20201024T141709"
                ],
                [
                    "S2A_MSIL1C_20201024T104121_N0209_R008_T31TDJ_20201024T141709"
                ]
            ],
            "s2_nb": 11,
            "l8_ids": [
                [
                    "LC08_L1TP_199029_20201026_20201106_02_T1",
                    "LC08_L1TP_199030_20201026_20201106_02_T1"
                ]
            ],
            "l8_nb": 1,
            "L8_enable_sr": false
        }
    ]
}
```

## How to generate a plan

In order to generate a plan you'll need the following:

- Start_date/ end_date: this parameters will define the time interval of the satellite products search (using EOdag)
- AOI: you Area Of Interest, this can be a vector file or an S2 MGRS tile id such as 31TCJ.
- Provider: the name of the satellite data cloud storage provider (creodias/peps/...) this list of accepted providers is the same as EOdag
- EOdag config file: a valid EOdag config file with the credentials to the desired providers

### Steps:

0. Download the python package
1. Create a virtualenv: `python3 -m venv venv-ewoc-wp`
2. Activate the venv: `source /path/to/venv-ewoc-wp/bin/activate`
3. Update pip: `pip install pip --upgrade`
4. Install with `pip install /path/to/ewoc_workplan-x.y.z.tar.gz`
5. Run `ewoc_workplan aoi sd ed o creds provider process_l8`

Full help

```bash
Usage: ewoc_workplan [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

Options:
  --version      Show the version and exit.
  -v, --verbose  Verbosity level default is warning, -v for info, -vv for debug
  --help  Show this message and exit.

Commands:
  generate
  load
  print
  push
  reproc
  write
```

```bash
$ ewoc_workplan generate
EWoC plan generation
Usage: ewoc_workplan generate [OPTIONS]

Options:
  -input TEXT                  Input: a list of S2 tiles eg: '31TCJ,30STF', a
                               csv file, a vector AOI file

  -sd TEXT                     Start date, format YYYY-mm-dd
  -ed TEXT                     End date, format YYYY-mm-dd
  -prov TEXT                   Provider (peps/creodias/astraea_eod)
  -l8_sr TEXT                  Process L8 OLI bands or not
  -aez_id INTEGER              ID of the AED
  -user TEXT                   Username
  -visibility TEXT             Visibility, public or private
  -season_type TEXT            Season type
  -eodag_config_filepath TEXT  Path to the Eodag yml config file
  -cloudcover TEXT             Cloudcover parameter
  --help                       Show this message and exit.

```

You can use as many commands at once as you like, for example:

```bash
$ ewoc_workplan load wp.json reproc -bucket "bucket_name" -path "/SPAIN/" write wp_reproc.json
```

### What's next

Once you generate a plan, the EWoC system database needs to be updated with the new products and tiles to process.
This update is done using an argo workflow. Once this update done, you can run the processors!

## How to release

You can find here the steps to release a new package:

1. Merge all the features into `develop` branch through PR on github
2. Check the CI
3. Merge `develop` into `main`
4. Tag a new version: `git tag -a X.Y.Z -m 'message'` according to [SemVer](https://semver.org/)
5. Push the `main` branch to github: `git push origin main --tags`
6. Generate the new packages cf. [here](https://packaging.python.org/tutorials/packaging-projects/#generating-distribution-archives)
7. Upload the package on the Github release page
