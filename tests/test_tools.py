# SPDX-License-Identifier: MIT
import copy, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import Blocked, load, convert, dump
from prepare import prepare
from validate import validate
ROOT=Path(__file__).resolve().parents[1]
class ToolsTests(unittest.TestCase):
    def setUp(self): self.api=load(ROOT/'assets/examples/openapi.json')
    def test_roundtrip_preserves_source_and_unset_consent(self):
        self.api['x-custom']={'kept':True}
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'src.json'; dump(src,self.api); out=Path(t)/'out'
            prepare(src,out,'inventory','inventory','Inventory')
            self.assertEqual(load(out/'openapi.json'),self.api)
            self.assertEqual(load(out/'itpay-manifest.json')['authoring']['confirmations'],[])
            self.assertEqual(load(out/'itpay-manifest.json')['authoring']['workflow']['selected_sources'],['openapi.json'])
            self.assertTrue(validate(out)['ok'])
            f=load(out/'workflow.arazzo.json'); f['workflows'][0]['steps'][0]['parameters']=[]; dump(out/'workflow.arazzo.json',f)
            with self.assertRaises(Blocked): validate(out)
    def test_unsupported_and_secret(self):
        for change in ('http','trace','ref','credential'):
            a=copy.deepcopy(self.api)
            if change=='http': a['servers'][0]['url']='http://example.com'
            if change=='trace': a['paths']['/items/{id}']['trace']=a['paths']['/items/{id}']['get']
            if change=='ref': a['paths']['/items/{id}']['get']['parameters'][0]['schema']={'$ref':'https://example.com/schema'}
            if change=='credential': a['paths']['/items/{id}']['get']['parameters'][0]['name']='Authorization'
            with self.assertRaises(Blocked): convert(a,'inventory')
    def test_body_types_and_source_constraints(self):
        op=self.api['paths']['/items/{id}']['get']
        op['parameters'].append({'name':'limit','in':'query','required':True,'schema':{'type':'integer','minimum':2,'maximum':10,'examples':[3]}})
        op['requestBody']={'required':True,'content':{'application/json':{'schema':{'type':'object','required':['enabled'],'properties':{'enabled':{'type':'boolean'}},'additionalProperties':False}}}}
        flow,ops=convert(self.api,'inventory')
        inputs=flow['workflows'][0]['inputs']; self.assertEqual(len(inputs['required']),3)
        self.assertEqual(inputs['properties']['body'],op['requestBody']['content']['application/json']['schema'])
        self.assertEqual(ops[0]['test_input'],{})
        self.assertIn('$inputs.',flow['workflows'][0]['steps'][0]['requestBody']['payload'])
    def test_modified_version_and_future_reference_rejected(self):
        for mutation in ('version','future','consent'):
            with tempfile.TemporaryDirectory() as t:
                src=Path(t)/'src.json'; dump(src,self.api); out=Path(t)/'out'; prepare(src,out,'inventory','inventory','Inventory')
                if mutation=='consent':
                    m=load(out/'itpay-manifest.json'); m['authoring']['confirmations']=['terms']; dump(out/'itpay-manifest.json',m)
                else:
                    f=load(out/'workflow.arazzo.json')
                    if mutation=='version': f['arazzo']='1.0.2'
                    else: f['workflows'][0]['steps'][0]['parameters'][0]['value']='$steps.future.outputs.value'
                    dump(out/'workflow.arazzo.json',f)
                with self.assertRaises(Blocked): validate(out)
    def test_composed_local_refs_enriched_authoring(self):
        op=self.api['paths']['/items/{id}']['get']
        shape={'type':'integer','minimum':1}
        self.api['components']={'schemas':{'Identifier':shape}}
        op['parameters'][0]['schema']={'$ref':'#/components/schemas/Identifier'}
        op['responses']['200']['content']={'application/json':{'schema':{'type':'object','properties':{'id':shape},'required':['id']}}}
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'src.json'; dump(src,self.api); out=Path(t)/'out'; prepare(src,out,'inventory','inventory','Inventory')
            flow=load(out/'workflow.arazzo.json'); w=flow['workflows'][0]
            w['steps'][0]['outputs']={'id':'$response.body#/id'}
            second=copy.deepcopy(w['steps'][0]); second['stepId']='second'; second.pop('outputs'); second['parameters'][0]['value']='$steps.call.outputs.id'; w['steps'].append(second)
            dump(out/'workflow.arazzo.json',flow)
            m=load(out/'itpay-manifest.json'); a=m['authoring']; a['pricing']={'billing_mode':'per_call','currency':'USD','amount_minor':5}; a['credentials']['credential_ids']=['my-reference']; a['service']['icon']={'media_type':'image/png','data_base64':'AAAA'}; dump(out/'itpay-manifest.json',m)
            self.assertTrue(validate(out)['ok'])
            w['inputs']['properties'][next(iter(w['inputs']['properties']))]['type']='string'; dump(out/'workflow.arazzo.json',flow)
            with self.assertRaises(Blocked): validate(out)
    def test_local_ref_cycle(self):
        self.api['components']={'schemas':{'A':{'$ref':'#/components/schemas/A'}}}
        with self.assertRaises(Blocked): convert(self.api,'inventory')
    def test_hostile_parsers(self):
        for text,suffix in [('{"x":1,"x":2}','json'),('{"x":NaN}','json'),('x: &x [1]\ny: *x','yaml'),('x: !!str 1','yaml')]:
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/('x.'+suffix); p.write_text(text)
                with self.assertRaises(Blocked): load(p)
    def test_secret_value_contexts_block_without_spillage(self):
        from common import fence
        cases=[{'example':{'password':'plain-live-password','api_key':'plain-live-key'}},
               {'examples':[{'credentials':{'password':'plain-live-password'}}]},
               {'default':{'token':['plain-live-token']}},
               {'enum':[{'api_key':'plain-live-key'}]},
               {'headers':{'Authorization':'plain-live-header'}},
               {'name':'X-Api-Key','schema':{'enum':['plain-live-key']}}]
        for value in cases:
            with self.subTest(value=value):
                a=copy.deepcopy(self.api)
                a['paths']['/items/{id}']['get']['responses']['200']['content']={'application/json':value}
                with self.assertRaises(Blocked) as ctx: convert(a,'inventory')
                self.assertNotIn('plain-live',str(ctx.exception))
        fence({'schema':{'type':'object','properties':{'password':{'type':'string'},'api_key':{'type':'string'}}}})
    def test_no_secret_in_error(self):
        self.api['x-note']='Bearer abcdefghijklmnop'
        with self.assertRaises(Blocked) as ctx: convert(self.api,'inventory')
        self.assertNotIn('abcdefghijklmnop',ctx.exception.path)
if __name__=='__main__': unittest.main()
