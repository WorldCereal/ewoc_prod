from plan.prep_all import PlanProc

def main(aoi, start_date,end_date,out_file,eodag_creds,eodag_provider,process_l8):
    plan = PlanProc(aoi, eodag_creds,eodag_provider)
    plan.run(start_date,end_date,process_l8=process_l8)
    plan.write_plan(out_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Prepare the pre-processing workflow')
    parser.add_argument("--aoi",help="AOI file path geojson/shapefile")
    parser.add_argument("--sd",help="Start date, format YYYY-mm-dd")
    parser.add_argument("--ed", help="End date, format YYYY-mm-dd")
    parser.add_argument("--o",help="Path to output json file")
    parser.add_argument("--creds",help="EOdag creds yaml file path")
    parser.add_argument("--provider", help="peps/creodias/astraea_eod")
    parser.add_argument("--process_l8", help="Process L8 OLI bands or not")
    args = parser.parse_args()
    main(args.aoi,args.sd,args.ed,args.o,args.creds,args.provider,args.process_l8)

