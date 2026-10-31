import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/workspace.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { loadResearch, saveResearch, STORAGE_KEY } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
let values;
test.beforeEach(() => {
  values = new Map();
  globalThis.localStorage = { getItem: key => values.get(key) ?? null, setItem: (key,value) => values.set(key,value) };
});
const report = () => ({id:'test',title:'Fixture',completed:[1],result:{mode:'live',goal:'Fixture',analyzed_at:'2026-10-31T10:00:00Z',summary:'Test',disclaimer:'Fixture only',analysis_method:'deterministic',coverage_percent:0,questions_analyzed:0,notes:[],inaccessible_source_ids:[],unanswered_questions:[],sources:[],coverage:[],actions:[{rank:1,action:'Verify',reason:'Test',priority:'high',source_ids:[],question_ids:[]}],gaps:[],conflicts:[],freshness_warnings:[]}});
test('starts with an empty workspace', () => assert.deepEqual(loadResearch(), {reports:[],error:null}));
test('reports and checklist progress survive serialization', () => {
  const item=report();assert.equal(saveResearch([item]),null);assert.deepEqual(loadResearch().reports,[item]);
});
test('bad JSON is reported and original data is preserved', () => {
  values.set(STORAGE_KEY,'{broken');assert.ok(loadResearch().error);assert.equal(values.get(STORAGE_KEY),'{broken');
});
test('corrupt nested evidence cannot crash the workspace', () => {
  const item=report();item.result.coverage=[{question_id:'Q1',question:'Test',status:'covered',supporting_source_ids:[],evidence:[null]}];
  saveResearch([item]);assert.ok(loadResearch().error);assert.deepEqual(loadResearch().reports,[]);
});
test('quota failures keep the last saved report intact', () => {
  saveResearch([report()]);const before=values.get(STORAGE_KEY);
  globalThis.localStorage.setItem=()=>{throw new Error('QuotaExceeded');};
  assert.match(saveResearch([]),/memory only/);assert.equal(values.get(STORAGE_KEY),before);
});
test('duplicate and invalid completion ranks do not inflate progress', () => {
  const item=report();item.completed=[1,1,99];saveResearch([item]);assert.deepEqual(loadResearch().reports[0].completed,[1]);
});
test('unsafe persisted source links are rejected', () => {
  const item=report();item.result.sources=[{id:'S1',fetch_status:'ok',text_length:1,title:'Test',url:'javascript:alert(1)',text_excerpt:'x',error:null,published_date:null}];
  saveResearch([item]);assert.ok(loadResearch().error);
});
