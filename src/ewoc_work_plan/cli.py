import logging
from pathlib import Path

import click

from ewoc_work_plan import __version__
from ewoc_work_plan.workplan import WorkPlan
from ewoc_work_plan.utils import set_logger

__author__ = "Mathis Germa"
__copyright__ = "CS Group France"
__license__ = "TBD"

_logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option(
    "-input_data",
    help="Input: a list of S2 tiles eg: '31TCJ,30STF', a csv file, a vector AOI file",
)
@click.option("-season_start", help="Season start date of the AEZ, format YYYY-mm-dd")
@click.option("-season_end", help="Season end date of the AEZ, format YYYY-mm-dd")
@click.option(
    "-season_processing_start", help="Season processing start date, format YYYY-mm-dd"
)
@click.option(
    "-season_processing_end", help="Season processing end date, format YYYY-mm-dd"
)
@click.option(
    "-annual_processing_start",
    help="Annual processing start date for cropland detector, format YYYY-mm-dd",
)
@click.option(
    "-annual_processing_end",
    help="Annual processing end date for cropland detector, format YYYY-mm-dd",
)
@click.option("-prov", help="Provider (peps/creodias/astraea_eod)")
@click.option("-l8_sr", default="False", help="Process L8 OLI bands or not")
@click.option("-aez_id", default=0, type=int, help="ID of the AED")
@click.option("-user", default="EWoC_admin", help="Username")
@click.option("-visibility", default="public", help="Visibility, public or private")
@click.option("-season_type", default="winter", help="Season type")
@click.option(
    "-detector_set",
    default="winterwheat, irrigation",
    help="Detector set linked to season type",
)
@click.option("-enable_sw", default="False", help="Process spring wheat or not")
@click.option(
    "-eodag_config_filepath", default=None, help="Path to the Eodag yml config file"
)
@click.option("-cloudcover", default="90", help="Cloudcover parameter")
@click.option("-min_nb_prods", default=40, help="Yearly minimum number of products")
def generate(
    ctx,
    input_data,
    season_start,
    season_end,
    season_processing_start,
    season_processing_end,
    annual_processing_start,
    annual_processing_end,
    prov,
    l8_sr,
    aez_id,
    user,
    visibility,
    season_type,
    detector_set,
    enable_sw,
    eodag_config_filepath,
    cloudcover,
    min_nb_prods,
):
    """
    Generate the workplan
    :param ctx:
    :param input_data: a list of S2 tiles, a csv file, a vector AOI file
    :param season_start: season start date of the AEZ
    :param season_end: season end date of the AEZ
    :param season_processing_start: season processing start date
    :param season_processing_end: season processing end date
    :param annual_processing_start: production start date
    :param annual_processing_end: production start date
    :param prov: provider (peps/creodias/astraea_eod)
    :param l8_sr: process L8 OLI bands or not
    :param aez_id: id of the AED
    :param user: username
    :param visibility: visibility (public/private)
    :param season_type: season type (winter/summer1/summer2)
    :param detector_set: detector set linked to season type
    :param enable_sw: process spring wheat or not
    :param eodag_config_filepath: path to the eodag yml config file
    :param cloudcover: cloud cover parameter
    :param min_nb_prods: Yearly minimum number of products
    """
    ctx.ensure_object(dict)

    if "." in input_data:
        if ".csv" in input_data:
            induced_type = "csv"
        else:
            supported_formats = [".shp", ".geojson", ".gpkg"]
            for format_type in supported_formats:
                if format_type in input_data:
                    induced_type = "aoi"
    else:
        # Managing l8_sr
        tiles_to_generate = input_data.split(",")
        induced_type = "S2_tiles"

    l8_split = l8_sr.split(",")
    for i, l8_sr_str in enumerate(l8_split):
        l8_split[i] = l8_sr_str == "True"
    if len(l8_split) > 1:
        l8_sr = l8_split
    else:
        l8_sr = l8_split[0]

    if induced_type == "S2_tiles":
        ctx.obj["wp"] = WorkPlan(
            tiles_to_generate,
            season_start,
            season_end,
            season_processing_start,
            season_processing_end,
            annual_processing_start,
            annual_processing_end,
            prov,
            l8_sr=l8_sr,
            aez_id=aez_id,
            user=user,
            visibility=visibility,
            season_type=season_type,
            detector_set=detector_set,
            enable_sw=enable_sw,
            eodag_config_filepath=eodag_config_filepath,
            min_nb_prd=min_nb_prods,
            cloudcover=cloudcover,
        )
    elif induced_type == "csv":  # To remove ?
        ctx.obj["wp"] = WorkPlan.from_csv(
            input_data,
            season_start,
            season_end,
            season_processing_start,
            season_processing_end,
            annual_processing_start,
            annual_processing_end,
            prov,
            l8_sr=l8_sr,
            aez_id=aez_id,
            user=user,
            visibility=visibility,
            season_type=season_type,
            detector_set=detector_set,
            enable_sw=enable_sw,
            eodag_config_filepath=eodag_config_filepath,
            min_nb_prd=min_nb_prods,
            cloudcover=cloudcover,
        )
    elif induced_type == "aoi":  # To remove ?
        ctx.obj["wp"] = WorkPlan.from_aoi(
            input_data,
            season_start,
            season_end,
            season_processing_start,
            season_processing_end,
            annual_processing_start,
            annual_processing_end,
            prov,
            l8_sr=l8_sr,
            aez_id=aez_id,
            user=user,
            visibility=visibility,
            season_type=season_type,
            detector_set=detector_set,
            enable_sw=enable_sw,
            eodag_config_filepath=eodag_config_filepath,
            min_nb_prd=min_nb_prods,
            cloudcover=cloudcover,
        )
    else:
        click.echo(f"Unrecognized {input_data} as input type")
        raise NotImplementedError


@click.command()
@click.pass_context
@click.argument("file", type=click.Path(exists=True))
def load(ctx, file):
    """
    Load the workplan
    """
    ctx.ensure_object(dict)
    ctx.obj["wp"] = WorkPlan.load(Path(file))


@click.command()
@click.pass_context
@click.argument("file", type=click.Path(exists=False))
def write(ctx, file):
    """
    Write the workplan
    """
    check_wp(ctx)
    ctx.obj["wp"].to_json(file)


@click.command()
@click.pass_context
def display(ctx):
    """
    Print the workplan
    """
    check_wp(ctx)
    click.echo(ctx.obj["wp"])


def check_wp(ctx):
    """
    Check the workplan
    """
    ctx.ensure_object(dict)
    if ctx.obj["wp"] is None:
        click.echo("The WorkPlan needs to be set")
        raise ValueError


@click.command()
@click.pass_context
def push(ctx):
    """
    Push the workplan to EwoC database
    """
    check_wp(ctx)
    ctx.obj["wp"].to_ewoc_db()


@click.command()
@click.pass_context
@click.option("-bucket", help="Bucket name")
@click.option("-path", help="Path in the bucket")
def reproc(ctx, bucket, path):
    """
    Reprocess the workplan for tiles that failed
    """
    check_wp(ctx)
    ctx.obj["wp"] = ctx.obj["wp"].reproc(bucket, path)


@click.group(chain=True)
@click.version_option(__version__)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbosity level default is warning, -v for info, -vv for debug",
)
def run(verbose):
    set_logger(verbose)


run.add_command(generate)
run.add_command(load)
run.add_command(write)
run.add_command(push)
run.add_command(reproc)
run.add_command(display)
run(obj={})
