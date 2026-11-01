# SPDX-License-Identifier: MIT
"""Prepare a local draft; never fetch, upload, probe, or grant consent."""
import argparse, json
from pathlib import Path
from common import Blocked, load, dump, convert, authoring, fail
from validate import validate

def prepare(source,out,key,sid,name):
    api=load(source); workflow,operations=convert(api,key)
    draft=authoring(key,sid,name,operations)
    from validate import check_schema, ROOT
    s=load(ROOT/'references/itpay-api-package.schema.json')
    check_schema(draft,{'$defs':s['$defs'],'$ref':'#/$defs/BYOKAuthoring'},'authoring_schema')
    p=Path(out)
    if p.exists() and any(p.iterdir()): fail('output_not_empty')
    p.mkdir(parents=True,exist_ok=True)
    dump(p/'openapi.json',api); dump(p/'workflow.arazzo.json',workflow)
    dump(p/'itpay-manifest.json',{'format':'itpay.api-package.v1','source_key':key,'revision':'','entry_path':'openapi.json','authoring':draft})
    report=validate(p); dump(p/'validation-report.json',report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('openapi','out','source-key','service-id','name'): p.add_argument('--'+name,required=True)
    a=p.parse_args()
    try: report=prepare(a.openapi,a.out,a.source_key,a.service_id,a.name)
    except Blocked as e: report={'ok':False,'issues':[{'code':e.code,'path':e.path}]}
    except Exception: report={'ok':False,'issues':[{'code':'invalid_input','path':'$'}]}
    print(json.dumps(report)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
