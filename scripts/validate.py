# SPDX-License-Identifier: MIT
"""Validate the deliberately bounded generated subset, without network access."""
import argparse
from pathlib import Path
from common import ROOT, Blocked, load, dump, fail, convert, authoring
from jsonschema import Draft202012Validator

def check_schema(obj, schema, code):
    # Vendored schemas must remain entirely local. Never install remote resolvers.
    def refs(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k=='$ref' and not v.startswith('#') and v != 'https://json-schema.org/draft/2020-12/schema': fail('schema_remote_ref')
                refs(v)
        elif isinstance(x,list):
            for v in x: refs(v)
    refs(schema)
    if next(Draft202012Validator(schema, registry=__import__('jsonschema_specifications').REGISTRY).iter_errors(obj),None): fail(code)

def validate(directory):
    p=Path(directory)
    files=[x for x in p.iterdir() if x.name not in ('validation-report.json','upload.json')]
    if len(files)>32 or sum(x.stat().st_size for x in files)>16*1024*1024: fail('bundle_size')
    if {x.name for x in files}!={'openapi.json','workflow.arazzo.json','itpay-manifest.json'}: fail('bundle_files')
    api=load(p/'openapi.json'); flow=load(p/'workflow.arazzo.json'); manifest=load(p/'itpay-manifest.json',1024*1024)
    if set(manifest)!={'format','source_key','revision','entry_path','authoring'} or manifest.get('format')!='itpay.api-package.v1' or manifest.get('entry_path')!='workflow.arazzo.json' or manifest.get('revision')!='': fail('manifest_binding')
    expected,operations=convert(api,manifest['source_key'])
    from semantics import check
    check(flow,expected,api,manifest['source_key'])
    check_schema(flow,load(ROOT/'references/arazzo-1.0.1.schema.yaml'), 'arazzo_schema')
    schema=load(ROOT/'references/itpay-api-package.schema.json')
    check_schema(manifest['authoring'],{'$defs':schema['$defs'],'$ref':'#/$defs/Authoring'},'authoring_schema')
    a=manifest['authoring']
    from common import fence
    fence(a)
    if a.get('confirmations',[]) != []: fail('consent_must_be_unset')
    allowed={o['operation_id'] for o in operations}
    for op in a['operations']:
        if op['source_path']!='openapi.json' or op['operation_id'] not in allowed: fail('authoring_operation_binding')
    if a['workflow']['selected_sources'] != ['openapi.json']: fail('authoring_source_binding')
    return {'ok':True,'scope':'offline-generated-subset-only','issues':[], 'evidence':{'schema':'Arazzo 1.0.1','network_requests':0,'live_tests':0,'consent':'unset','publication':'not_performed','test_inputs':'needs_user_test_input','http_methods':sorted({m.upper() for item in api.get('paths',{}).values() for m in item if m in ('get','post','put','patch','delete')})}}
def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('directory'); args=parser.parse_args()
    try: report=validate(args.directory)
    except Blocked as e: report={'ok':False,'scope':'offline-generated-subset-only','issues':[{'code':e.code,'path':e.path}]}
    except Exception: report={'ok':False,'scope':'offline-generated-subset-only','issues':[{'code':'invalid_bundle','path':'$'}]}
    dump(Path(args.directory)/'validation-report.json',report)
    print(__import__('json').dumps(report)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
