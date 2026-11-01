# SPDX-License-Identifier: MIT
"""Conservative semantic checks for locally composed HTTP workflows."""
import re
from jsonschema import Draft202012Validator
from common import fail, fence, schema, resolve_local

def check(flow, expected, api, key):
    if flow.get('arazzo')!='1.0.1' or flow.get('sourceDescriptions')!=expected['sourceDescriptions']: fail('source_binding')
    if set(flow)-{'arazzo','info','sourceDescriptions','workflows'}: fail('workflow_feature_unsupported')
    definitions={w['steps'][0]['operationId']:w for w in expected['workflows']}
    resolved=resolve_local(api)
    response_schemas={}
    for item in resolved['paths'].values():
        for method,op in item.items():
            if method not in ('get','post','put','patch','delete'): continue
            rs=op.get('responses',{}).get('200',{}).get('content',{}).get('application/json',{}).get('schema')
            response_schemas['$sourceDescriptions.'+key+'.'+op['operationId']]=rs
    ids=[w['workflowId'] for w in flow['workflows']]
    if len(set(ids))!=len(ids): fail('duplicate_workflow_id')
    graph={w['workflowId']:w.get('dependsOn',[]) for w in flow['workflows']}
    def visit(n,stack):
        if n not in graph: fail('unknown_workflow_dependency')
        if n in stack: fail('workflow_cycle')
        for dep in graph[n]: visit(dep,stack+[n])
    for n in ids: visit(n,[])
    for w in flow['workflows']:
        if set(w)-{'workflowId','summary','description','inputs','steps','dependsOn','outputs'}: fail('workflow_feature_unsupported')
        inp=schema(w.get('inputs',{'type':'object'}))
        if inp['type']!='object': fail('object_inputs_required')
        steps={}; seen=set()
        def expression_type(value):
            if value.startswith('$inputs.'):
                name=value[len('$inputs.'):]
                if name not in inp.get('properties',{}): fail('unknown_input')
                return inp['properties'][name],name in inp.get('required',[])
            match=re.fullmatch(r'\$steps\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)',value)
            if match:
                sid,output=match.groups()
                if sid not in steps or output not in steps[sid]: fail('future_or_unknown_step_output')
                return steps[sid][output],True
            fail('runtime_expression_unsupported')
        def binding(value,target,required):
            if isinstance(value,str) and value.startswith('$'):
                source,present=expression_type(value)
                if source!=target: fail('mapping_schema_mismatch')
                if required and not present: fail('required_mapping_optional_input')
            elif not Draft202012Validator(target).is_valid(value): fail('literal_type_or_constraint')
        for step in w['steps']:
            if set(step)-{'stepId','operationId','parameters','requestBody','outputs','description'}: fail('step_feature_unsupported')
            sid=step['stepId']
            if not re.fullmatch(r'[A-Za-z0-9_-]+',sid) or sid in seen: fail('duplicate_or_invalid_step_id')
            seen.add(sid)
            if step.get('operationId') not in definitions: fail('unknown_operation_binding')
            d=definitions[step['operationId']]; original=d['steps'][0]; props=d['inputs']['properties']; required=d['inputs']['required']
            mappings={(p.get('in'),p.get('name')):p for p in step.get('parameters',[])}
            if len(mappings)!=len(step.get('parameters',[])): fail('duplicate_parameter_mapping')
            allowed={(p['in'],p['name']):p for p in original.get('parameters',[])}
            if set(mappings)-set(allowed): fail('unknown_parameter_mapping')
            for loc,p in allowed.items():
                inputkey=p['value'][len('$inputs.'):]
                if loc not in mappings:
                    if inputkey in required: fail('required_parameter_mapping')
                else:
                    if set(mappings[loc])!={'name','in','value'}: fail('parameter_feature_unsupported')
                    binding(mappings[loc]['value'],props[inputkey],inputkey in required)
            if 'body' in props:
                body=step.get('requestBody')
                if body is None:
                    if 'body' in required: fail('required_body_mapping')
                else:
                    if set(body)!={'contentType','payload'} or body['contentType']!='application/json': fail('body_feature_unsupported')
                    binding(body['payload'],props['body'],'body' in required)
            elif 'requestBody' in step: fail('unexpected_body')
            outputs={}
            for name,value in step.get('outputs',{}).items():
                rs=response_schemas.get(step['operationId'])
                if not rs or not isinstance(value,str) or not value.startswith('$response.body'): fail('output_schema_unavailable')
                suffix=value[len('$response.body'):]
                if suffix:
                    if not suffix.startswith('#/'): fail('output_expression_unsupported')
                    for part in suffix[2:].split('/'):
                        try:
                            namepart=part.replace('~1','/').replace('~0','~')
                            if namepart not in rs.get('required',[]): fail('optional_response_output')
                            rs=rs['properties'][namepart]
                        except (KeyError,TypeError): fail('output_schema_unavailable')
                outputs[name]=schema(rs)
            steps[sid]=outputs
        for value in w.get('outputs',{}).values(): expression_type(value)
    fence(flow)
