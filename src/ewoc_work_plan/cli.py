import click
import logging
import sys
from pathlib import Path


from ewoc_work_plan import __version__
from ewoc_work_plan.workplan import WorkPlan
from ewoc_work_plan.plan.reproc import reproc_wp

__author__ = "Mathis Germa"
__copyright__ = "CS Group France"
__license__ = "TBD"

_logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option('-input', help="Input: a list of S2 tiles eg: '31TCJ,30STF', a csv file, a vector AOI file")
@click.option('-sd', help="Start date, format YYYY-mm-dd")
@click.option('-ed', help="End date, format YYYY-mm-dd")
@click.option('-prov', help="Provider (peps/creodias/astraea_eod)")
@click.option('-l8_sr', help="Process L8 OLI bands or not", default="False")
@click.option('-aez_id', default=0, type=int, help="ID of the AED")
@click.option('-user', default="EWoC_admin", help="Username")
@click.option('-visibility', default="public", help="Visibility, public or private")
@click.option('-season_type', default="cropland", help="Season type")
@click.option('-eodag_config_filepath', help="Path to the Eodag yml config file")
@click.option('-cloudcover', default="90", help="Cloudcover parameter")
def generate(ctx, input, sd, ed, prov, l8_sr, aez_id,user,visibility,season_type,eodag_config_filepath,cloudcover):
    ctx.ensure_object(dict)

    if "." in input :
        if ".csv" in input:
            induced_type = "csv"
        else:
            supported_formats = ['.shp', '.geojson', '.gpkg']
            for format in supported_formats:
                if format in input:
                    induced_type = "aoi"
    else:
        # Managing l8_sr
        tiles_to_generate = input.split(",")
        induced_type = "S2_tiles"


    l8_split = l8_sr.split(",")
    for i, l8_sr_str in enumerate(l8_split):
        l8_split[i] = l8_sr_str == "True"
    if len(l8_split)>1:
        l8_sr = l8_split
    else:
        l8_sr = l8_split[0]

    if induced_type == "S2_tiles":
        ctx.obj["wp"] = WorkPlan(tiles_to_generate, sd, ed, prov, l8_sr)
    elif induced_type == "csv":
        ctx.obj["wp"] = WorkPlan.from_csv(input, sd, ed, prov, l8_sr)
    elif induced_type == "aoi":
        ctx.obj["wp"] = WorkPlan.from_aoi(input, sd, ed, prov, l8_sr)
    else:
        click.echo(f"Unrecognized {input} as input type")
        raise NotImplementedError


@click.command()
@click.pass_context
@click.argument('file', type=click.Path(exists=True))
def load(ctx, file):
    ctx.ensure_object(dict)
    ctx.obj["wp"] = WorkPlan.load(Path(file))


@click.command()
@click.pass_context
@click.argument('file', type=click.Path(exists=False))
def write(ctx, file):
    check_wp(ctx)
    ctx.obj["wp"].to_json(file)


@click.command()
@click.pass_context
def print(ctx):
    check_wp(ctx)
    click.echo(ctx.obj["wp"])


def check_wp(ctx):
    ctx.ensure_object(dict)
    if ctx.obj["wp"] is None:
        click.echo("The WorkPlan needs to be set")
        raise ValueError


@click.command()
@click.pass_context
@click.option('-nb_of_products', default=100, type=int, help="Maximum number of product per line in the Database")
def push(ctx, nb_of_products):
    check_wp(ctx)
    ctx.obj["wp"].to_ewoc_db(nb_of_products=nb_of_products)


@click.command()
@click.pass_context
@click.option('-bucket', help="Bucket name")
@click.option('-path', help="Path in the bucket")
def reproc(ctx, bucket, path):
    check_wp(ctx)
    ctx.obj["wp"] = ctx.obj["wp"].reproc(bucket, path)


@click.group(chain=True)
def run():
    pass

run.add_command(generate)
run.add_command(load)
run.add_command(write)
run.add_command(push)
run.add_command(reproc)
run.add_command(print)
run(obj={})