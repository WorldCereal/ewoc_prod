# EWoC work plan generation

The aim of this tool is to prepare and organize the satellite products that will be processed by the EWoC system.
The generated json plan is the starting point for the Argo workflows.

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
  -v, --verbose  Verbosity level default is warning, -v for info, -vv for
                 debug

  --help         Show this message and exit.

Commands:
  display   Print the workplan
  generate  Generate the workplan :param ctx: :param input_data: a list of...
  load      Load the workplan
  reproc    Reprocess the workplan for tiles that failed
  write     Write the workplan
```

```bash
$ ewoc_workplan generate
EWoC plan generation
Usage: ewoc_workplan generate [OPTIONS]

Options:
  -input_data TEXT             Input: a list of S2 tiles eg: '31TCJ,30STF', a
                               csv file, a vector AOI file

  -meta TEXT                   All the meta data that will be passed on to the
                               DB

  -wp_processing_start TEXT    Workplan processing start date, format YYYY-mm-
                               dd

  -wp_processing_end TEXT      Workplan processing end date, format YYYY-mm-dd
  -prov <TEXT TEXT>...         Provider (peps/creodias/astraea_eod)
  -strategy <TEXT TEXT>...     Fusion strategy (L2A,L1C)
  -l8_sr TEXT                  Process L8 OLI bands or not
  -aez_id INTEGER              ID of the AED
  -user TEXT                   Username
  -visibility TEXT             Visibility, public or private
  -season_type TEXT            Season type
  -detector_set TEXT           Detector set linked to season type
  -enable_sw TEXT              Process spring wheat or not
  -eodag_config_filepath TEXT  Path to the Eodag yml config file
  -cloudcover INTEGER          Cloudcover parameter
  -min_nb_prods INTEGER        Yearly minimum number of products
  --help                       Show this message and exit.

```
**Generation example**
```bash
ewoc_workplan -v generate -input_data 35UMQ -wp_processing_start 2018-07-02 -wp_processing_end 2019-10-26
  -prov creodias -prov creodias -l8_sr True -eodag_config_filepath ~/eodag_config.yml -strategy L1C -strategy L1C write 35UMQ.json
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