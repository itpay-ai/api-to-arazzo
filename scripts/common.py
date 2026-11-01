# SPDX-License-Identifier: MIT
"""Strict offline preparation primitives; no network or execution capabilities."""
import copy, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
class Blocked(Exception):
    def __init__(self, code, path='$'): self.code, self.path = code, path

def fail(code, path='$'): raise Blocked(code, path)
def pairs(items):
    result = {}
    for key, value in items:
        if key in result: fail('duplicate_key')
        result[key] = value
    return result
class StrictLoader(yaml.SafeLoader): pass
def mapping(loader, node):
    return pairs(loader.construct_pairs(node, deep=True))
StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
def load(path, limit=2*1024*1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file(): fail('unsafe_file')
    if path.stat().st_size > limit: fail('file_size')
    raw = path.read_text(encoding='utf-8')
    try:
        if path.suffix.lower() == '.json':
            obj = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: fail('nonfinite'))
        else:
            for token in yaml.scan(raw):
                if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken, yaml.tokens.TagToken)): fail('yaml_feature')
            obj = yaml.load(raw, Loader=StrictLoader)
    except Blocked: raise
    except Exception: fail('parse_error')
    count = 0
    def walk(x, depth):
        nonlocal count
        count += 1
        if depth > 48 or count > 100000: fail('structure_limit')
        if isinstance(x, dict):
            if any(not isinstance(k, str) for k in x): fail('nonstring_key')
            for v in x.values(): walk(v, depth+1)
        elif isinstance(x, list):
            for v in x: walk(v, depth+1)
        elif not isinstance(x, (str, int, float, bool, type(None))): fail('non_json_value')
        elif isinstance(x, float) and not __import__('math').isfinite(x): fail('nonfinite')
    walk(obj, 0)
    return obj

def dump(path, value): Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
CREDENTIAL = re.compile(r'authorization|api[-_]?key|(?:access[-_]?)?token|secret|password|credential', re.I)
SECRET = re.compile(r'\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._~-]{8,}|AKIA[A-Z0-9]{16}|-----BEGIN .*PRIVATE KEY-----)', re.I)
def fence(obj):
    def scan(x, path='$', sensitive=False, literal=False):
        if isinstance(x, dict):
            for k,v in x.items():
                if SECRET.search(k): fail('secret_literal')
                if literal and CREDENTIAL.search(k) and v not in (None,'',[],{}): fail('credential_literal')
                if k == '$ref' and (not isinstance(v,str) or not v.startswith('#/')): fail('unsupported_ref', '$')
                if sensitive and k in ('example','examples','default','enum','const','value') and v not in (None,'',[],{}): fail('credential_literal', '$')
                scan(v, path+'.'+k if not CREDENTIAL.search(k) else path+'.<credential>', sensitive or k == 'securitySchemes' or bool(CREDENTIAL.search(k)) or bool(CREDENTIAL.search(str(x.get('name','')))), literal or k in ('example','examples','default','enum','const','value','payload','test_input','headers'))
        elif isinstance(x,list):
            for i,v in enumerate(x): scan(v,path+f'[{i}]',sensitive,literal)
        elif isinstance(x,str) and SECRET.search(x): fail('secret_literal', '$')
    scan(obj)

def resolve_local(document):
    count=0
    def walk(x,stack=()):
        nonlocal count
        count+=1
        if count>100000 or len(stack)>48: fail('ref_limit')
        if isinstance(x,dict):
            if '$ref' in x:
                ref=x['$ref']
                if not isinstance(ref,str) or not ref.startswith('#/'): fail('unsupported_ref')
                if ref in stack: fail('ref_cycle')
                target=document
                try:
                    for part in ref[2:].split('/'): target=target[part.replace('~1','/').replace('~0','~')]
                except (KeyError,TypeError): fail('unresolved_ref')
                # Sibling constraints cannot be silently overwritten.
                if len(x)!=1: fail('ref_siblings_unsupported')
                return walk(target,stack+(ref,))
            return {k:walk(v,stack) for k,v in x.items()}
        if isinstance(x,list): return [walk(v,stack) for v in x]
        return x
    return walk(document)

def schema(s):
    if not isinstance(s,dict): fail('unsupported_schema')
    if 'nullable' in s or 'discriminator' in s or 'xml' in s: fail('unsupported_schema_dialect')
    try: Draft202012Validator.check_schema(s)
    except Exception: fail('invalid_input_schema')
    if s.get('type') not in ('object','array','string','integer','number','boolean'): fail('explicit_type_required')
    for k,v in s.get('properties',{}).items():
        if CREDENTIAL.search(k): fail('credential_business_input')
        schema(v)
    if 'items' in s: schema(s['items'])
    return copy.deepcopy(s)
def convert(api, source_key):
    fence(api)
    api=resolve_local(api)
    if not isinstance(api,dict) or not re.fullmatch(r'3\.[01]\.\d+',api.get('openapi','')): fail('openapi_version')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',source_key): fail('source_key')
    servers=api.get('servers',[])
    if len(servers)!=1: fail('single_server_required')
    u=urlsplit(servers[0].get('url',''))
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or '{' in u.geturl(): fail('fixed_https_server_required')
    credential_names={str(v.get('name','')).lower() for v in api.get('components',{}).get('securitySchemes',{}).values() if isinstance(v,dict) and v.get('type')=='apiKey'}
    workflows=[]; operations=[]; ids=set()
    for path,item in sorted(api.get('paths',{}).items()):
        if not isinstance(item,dict) or not path.startswith('/'): fail('invalid_path')
        if 'servers' in item: fail('path_servers_unsupported')
        for method,op in sorted(item.items()):
            if method in ('parameters','summary','description') or method.startswith('x-'): continue
            if method not in ('get','post','put','patch','delete'): fail('unsupported_method')
            if 'servers' in op or 'callbacks' in op: fail('operation_feature_unsupported')
            oid=op.get('operationId')
            if not isinstance(oid,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,199}',oid) or oid in ids: fail('unique_operation_id_required')
            ids.add(oid)
            props={}; required=[]; params=[]; seen=set()
            merged={}
            for p in item.get('parameters',[])+op.get('parameters',[]): merged[(p.get('in'),p.get('name'))]=p
            for (loc,name),p in sorted(merged.items()):
                if loc not in ('path','query','header') or not isinstance(name,str): fail('parameter_location_unsupported')
                if CREDENTIAL.search(name) or name.lower() in credential_names: fail('credential_parameter_requires_manual_binding')
                if 'content' in p or any(k in p for k in ('style','explode','allowReserved','allowEmptyValue')): fail('parameter_serialization_unsupported')
                s=schema(p.get('schema',{}))
                if s['type'] in ('object','array'): fail('complex_parameter_unsupported')
                key=loc+'_'+hashlib.sha256(name.encode()).hexdigest()[:16]
                props[key]=s
                if p.get('required') or loc=='path': required.append(key)
                params.append({'name':name,'in':loc,'value':'$inputs.'+key}); seen.add(name if loc=='path' else '')
            if set(re.findall(r'\{([^{}]+)\}',path)) != seen-{''}: fail('path_parameter_binding')
            step={'stepId':'call','operationId':'$sourceDescriptions.'+source_key+'.'+oid}
            if params: step['parameters']=params
            if 'requestBody' in op:
                body=op['requestBody']; content=body.get('content',{})
                if set(content)!={'application/json'}: fail('json_body_required')
                if 'encoding' in content['application/json']: fail('body_encoding_unsupported')
                props['body']=schema(content['application/json'].get('schema',{}))
                if body.get('required'): required.append('body')
                step['requestBody']={'contentType':'application/json','payload':'$inputs.body'}
            wid='operation_'+hashlib.sha256((method+' '+path).encode()).hexdigest()[:20]
            workflows.append({'workflowId':wid,'inputs':{'type':'object','properties':props,'required':required,'additionalProperties':False},'steps':[step]})
            operations.append({'source_path':'openapi.json','operation_id':oid,'selected':True,'test_input':{}})
    if not workflows: fail('operations_required')
    return {'arazzo':'1.0.1','info':{'title':'Prepared API workflows','version':'1.0.0'},'sourceDescriptions':[{'name':source_key,'url':'openapi.json','type':'openapi'}],'workflows':workflows},operations

def authoring(key,sid,name,operations):
    fence({'service_id':sid,'public_name':name})
    return {'version':'itpay.api-package.v1','service':{'service_id':sid,'public_name':name},'source':{'mode':'file','library_api_ids':[]},'credentials':{'source':'own','credential_ids':[],'required_keys':[]},'operations':operations,'workflow':{'instruction':'Offline draft; supply and review test inputs on the website. No requests were executed.','version_name':'draft','test_input':{},'selected_sources':['openapi.json']},'pricing':{'billing_mode':'free','currency':'CNY','amount_minor':0},'confirmations':[],'terms_version':'2026-06-12'}
