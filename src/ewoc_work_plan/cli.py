import logging
from pathlib import Path

import click

from ewoc_work_plan import __version__
from ewoc_work_plan.utils import set_logger
from ewoc_work_plan.workplan import WorkPlan

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
@click.option(
    "-meta",
    help="All the meta data that will be passed on to the DB",
    default={}
)
@click.option(
    "-wp_processing_start", help="Workplan processing start date, format YYYY-mm-dd"
)
@click.option(
    "-wp_processing_end", help="Workplan processing end date, format YYYY-mm-dd"
)
@click.option("-prov", help="Provider (peps/creodias/astraea_eod)", multiple=True)
@click.option("-strategy", help="Fusion strategy (L2A,L1C)", multiple=True)
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
@click.option("-enable_sw", default=False, help="Process spring wheat or not")
@click.option(
    "-eodag_config_filepath", default=None, help="Path to the Eodag yml config file"
)
@click.option("-cloudcover", default=90, help="Cloudcover parameter")
@click.option("-min_nb_prods", default=50, help="Yearly minimum number of products")
@click.option("-rm_l1c", default=False, help="Remove L1C products or not")
def generate(
    ctx,
    input_data,
    meta,
    wp_processing_start,
    wp_processing_end,
    prov,
    strategy,
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
    rm_l1c,
):
    """
    Generate the workplan
    :param ctx:
    :param input_data: a list of S2 tiles, a csv file, a vector AOI file
    :param meta: Metadata dictionary
    :param wp_processing_start: workplan processing start date
    :param wp_processing_end: workplan processing end date
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
    :param rm_l1c: remove L1C products or not
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
            meta,
            wp_processing_start,
            wp_processing_end,
            prov,
            strategy=strategy,
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
            rm_l1c=rm_l1c,
        )
    elif induced_type == "csv":  # To remove ?
        ctx.obj["wp"] = WorkPlan.from_csv(
            input_data,
            meta,
            wp_processing_start,
            wp_processing_end,
            prov,
            strategy=strategy,
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
            rm_l1c=rm_l1c,
        )
    elif induced_type == "aoi":  # To remove ?
        ctx.obj["wp"] = WorkPlan.from_aoi(
            input_data,
            meta,
            wp_processing_start,
            wp_processing_end,
            prov,
            strategy=strategy,
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
            rm_l1c=rm_l1c,
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
        raise ValueError("The WorkPlan needs to be set")


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
