import { useCallback, useEffect, useRef, useState } from 'react';
import { FileDown, FlaskConical, Loader2, Printer, RefreshCw } from 'lucide-react';
import { Checklist } from './components/Checklist';
import { ConflictExplorer } from './components/ConflictExplorer';
import { CoverageMatrix } from './components/CoverageMatrix';
import { Overview } from './components/Overview';
import { SimpleView } from './components/SimpleView';
import { SourceDiscovery } from './components/SourceDiscovery';
import { PdfUpload } from './components/PdfUpload';
import { AskGapLens } from './components/AskGapLens';
import { SuggestedQuestions } from './components/SuggestedQuestions';
import { EMPTY_FORM, ResearchInput, type ResearchForm } from './components/ResearchInput';
import { SourceDrawer } from './components/SourceDrawer';
import { Warnings } from './components/Warnings';
import { DashboardLayout, Landing, pages } from './components/Shell';
import { EvidenceGraph } from './components/EvidenceGraph';
import { DashboardHome, EmptyResearch, GapList, ResearchHistory, SourceLibrary } from './components/WorkspaceViews';
import { api, ApiError } from './lib/api';
import { downloadReport, loadResearch, saveResearch, STORAGE_KEY, type SavedResearch } from './lib/workspace';
import type { AnalyzeRequest, HealthResponse, SourceRecord } from './lib/types';

export default function App() {
  const [path,setPath]=useState(window.location.pathname.replace(/\/$/,'') || '/');
  const navigate=useCallback((to:string)=>{window.history.pushState({},'',to);setPath(to);window.scrollTo(0,0);},[]);
  useEffect(()=>{
    const pop=()=>setPath(window.location.pathname.replace(/\/$/,'') || '/');
    const click=(e:MouseEvent)=>{const a=(e.target as Element).closest?.('a');if(!a||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target||a.hasAttribute('download'))return;const url=new URL(a.href);if(url.origin===location.origin&&!url.hash&&(url.pathname==='/'||url.pathname.startsWith('/dashboard'))){e.preventDefault();navigate(url.pathname);}};
    window.addEventListener('popstate',pop);document.addEventListener('click',click);
    return ()=>{window.removeEventListener('popstate',pop);document.removeEventListener('click',click);};
  },[navigate]);
  const [initial]=useState(loadResearch);
  const [reports,setReports]=useState(initial.reports);
  const reportsRef=useRef(reports);
  const [storageBlocked,setStorageBlocked]=useState(!!initial.error);
  const [storageError,setStorageError]=useState(initial.error);
  const [selected,setSelected]=useState(()=>{try{const id=sessionStorage.getItem('gaplens.active');return initial.reports.some(r=>r.id===id)?id!:initial.reports[0]?.id??'';}catch{return initial.reports[0]?.id??'';}});
  useEffect(()=>{try{sessionStorage.setItem('gaplens.active',selected);}catch{/* Selection still works in memory. */}},[selected]);
  const active=reports.find(r=>r.id===selected) ?? null;
  const result=active?.result ?? null;
  const persist=(next:SavedResearch[])=>{reportsRef.current=next;setReports(next);if(!storageBlocked)setStorageError(saveResearch(next));};
  const [dark,setDark]=useState(()=>{try{return localStorage.getItem('gaplens.theme')==='dark';}catch{return false;}});
  useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';try{localStorage.setItem('gaplens.theme',dark?'dark':'light');}catch{/* Theme still works in memory. */}},[dark]);
  const [mode,setMode]=useState<'live'|'demo'>('live');
  const [view,setView]=useState<'simple'|'research'>('simple');
  const [form,setForm]=useState<ResearchForm>(EMPTY_FORM);
  const [phase,setPhase]=useState<'idle'|'loading'|'error'|'done'>('idle');
  const [error,setError]=useState<string|null>(null);
  const [formError,setFormError]=useState<string|null>(null);
  const [lastPayload,setLastPayload]=useState<AnalyzeRequest|null>(null);
  const [drawer,setDrawer]=useState<{source:SourceRecord;focusQuestionId?:string}|null>(null);
  const closeDrawer=useCallback(()=>setDrawer(null),[]);
  const openSource=(source:SourceRecord,focusQuestionId?:string)=>setDrawer({source,focusQuestionId});
  const [health,setHealth]=useState<HealthResponse|null>(null);
  const [healthError,setHealthError]=useState<string|null>(null);
  const [discoveryAvailable,setDiscoveryAvailable]=useState<boolean|null>(null);
  const [resetConfirm,setResetConfirm]=useState(false);
  const checkHealth=useCallback(()=>{setHealthError(null);api.health().then(setHealth).catch((e:unknown)=>{setHealth(null);setHealthError(e instanceof Error?e.message:'Backend unreachable.');});api.capabilities().then(c=>{if(c)setDiscoveryAvailable(c.discovery_available);});},[]);
  useEffect(checkHealth,[checkHealth]);
  const running=useRef(false);
  const runAnalysis=async(payload:AnalyzeRequest)=>{
    if(running.current)return;
    running.current=true;setPhase('loading');setError(null);setLastPayload(payload);
    try{
      const response=await api.analyze(payload);
      const report:SavedResearch={id:crypto.randomUUID(),title:response.goal,result:response,completed:[]};
      persist([report,...reportsRef.current]);setSelected(report.id);setPhase('done');navigate('/dashboard/reports');
    }catch(e){setError(e instanceof ApiError?e.message:'Analysis failed. Your inputs are still available.');setPhase('error');}
    finally{running.current=false;}
  };
  const submit=()=>{
    setFormError(null);
    if(mode==='demo'){void runAnalysis({mode:'offline_sample'});return;}
    const goal=form.goal.trim();
    if(goal.length<3){setFormError('Add a research goal of at least 3 characters.');return;}
    const urls=form.urls.map(u=>u.trim()).filter(Boolean);
    if(urls.some(u=>{try{return !['http:','https:'].includes(new URL(u).protocol);}catch{return true;}})){setFormError('Use valid public URLs starting with http:// or https://.');return;}
    const texts=form.texts.filter(t=>t.text.trim()).map(t=>({...(t.title.trim()?{title:t.title.trim()}:{}),text:t.text}));
    if(!urls.length&&!texts.length){setFormError('Add at least one source URL or pasted text. Two or more sources allow comparison.');return;}
    if(urls.length+texts.length>20){setFormError('At most 20 sources per analysis.');return;}
    const questions=form.questions.map(q=>q.trim()).filter(Boolean);
    void runAnalysis({mode:'live',goal,urls,texts,...(questions.length?{questions}:{})});
  };
  const openReport=(id:string)=>{setSelected(id);setDrawer(null);navigate('/dashboard/reports');};
  const page=path==='/dashboard'?'':path.replace('/dashboard/','');
  const title=pages.find(p=>p[0]===page)?.[1] ?? 'Page not found';
  useEffect(()=>{document.title=path==='/'?'GapLens — Discover what your research is missing':`${title} · GapLens`;},[path,title]);
  const updateCompleted=(completed:number[])=>{if(active)persist(reports.map(r=>r.id===active.id?{...r,completed}:r));};
  const checklist=result&&active?<Checklist key={active.id} result={result} done={new Set(active.completed)} onChange={done=>updateCompleted([...done])} onOpenSource={openSource}/>:null;
  const reportPage=['gaps','conflicts','graph','freshness','checklist','sources','reports'].includes(page);
  const startFromLanding=(goal:string,demo:boolean)=>{setMode(demo?'demo':'live');if(goal)setForm({...EMPTY_FORM,goal,questions:['']});setFormError(null);setError(null);setPhase('idle');navigate('/dashboard/new-research');};
  return <><a className="skip-link" href="#main-content">Skip to content</a>{path==='/'?<Landing dark={dark} toggle={()=>setDark(!dark)} onStart={startFromLanding}/>:<DashboardLayout page={page} dark={dark} toggle={()=>setDark(!dark)} connected={!!health}>
    {storageError&&<div className="notice warning" role="alert">{storageError}</div>}
    {phase==='loading'&&page!=='new-research'&&<div className="notice" role="status"><Loader2 className="animate-spin" size={18}/> Analysis is running. Your report will open when it finishes.</div>}
    {phase==='error'&&page!=='new-research'&&<div className="notice warning" role="alert">{error}<a href="/dashboard/new-research">Return to inputs</a></div>}
    {page===''&&<DashboardHome reports={reports} open={openReport}/>}
    {page!==''&&<div className="page-heading"><div><p className="eyebrow">RESEARCH INTELLIGENCE</p><h1>{title}</h1><p>{page==='new-research'?'Start with a question worth answering.':page==='my-research'?'Pick up where your last investigation left off.':'Every finding is a starting point for verification.'}</p></div></div>}
    {page==='new-research'&&<>
      <div className="mode-switch" role="group" aria-label="Analysis mode"><button disabled={phase==='loading'} aria-pressed={mode==='live'} onClick={()=>{setMode('live');setFormError(null);}}>Live sources</button><button disabled={phase==='loading'} aria-pressed={mode==='demo'} onClick={()=>{setMode('demo');setFormError(null);}}><FlaskConical size={16}/> Demo sample</button></div>
      <p className="section-description mb-5">{mode==='demo'?'Bundled fictional scholarship sources. No pages are fetched.':'Free deterministic source analysis. Optional AI suggests questions only; your source text is not sent to the AI provider.'}</p>
      {mode==='live'&&<div className="mb-5 space-y-5"><p className="text-sm text-inksoft">Choose how to collect sources — any combination works, and none of them requires a search provider: <strong>Add Website Links</strong> (Step 3 below), <strong>Upload Documents</strong>, or <strong>Find Sources Automatically</strong> (optional).</p><SourceDiscovery goal={form.goal} searchConfigured={discoveryAvailable ?? !!health?.search_configured} onAdd={(urls)=>{const existing=form.urls.filter(u=>u.trim());const merged=[...existing,...urls.filter(u=>!existing.includes(u))];setForm({...form,urls:[...merged,'']});}}/><PdfUpload onAdd={(title,text)=>setForm({...form,texts:[...form.texts,{title,text}]})}/></div>}
      <ResearchInput mode={mode} form={form} onChange={setForm} onAnalyze={submit} onClear={()=>{setForm(EMPTY_FORM);setFormError(null);setError(null);setPhase('idle');}} analyzing={phase==='loading'} formError={formError}/>
      {phase==='loading'&&<section className="panel mt-5" role="status"><h2><Loader2 size={20} className="animate-spin"/> Reading and comparing your sources…</h2><p className="section-description">Waiting for the complete backend response. No estimated progress is shown.</p><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="loading-sweep h-full w-2/5 rounded-full bg-indigoaccent"/></div></section>}
      {phase==='error'&&<section className="notice warning mt-5" role="alert"><div><strong>Analysis failed</strong><p>{error}</p><p>Your existing reports and current inputs are preserved.</p></div><button className="secondary-button" onClick={()=>lastPayload&&void runAnalysis(lastPayload)}><RefreshCw size={16}/> Retry</button></section>}
    </>}
    {page==='my-research'&&<ResearchHistory reports={reports} open={openReport} remove={id=>{persist(reports.filter(r=>r.id!==id));if(id===selected)setSelected(reports.find(r=>r.id!==id)?.id??'');}} rename={(id,title)=>persist(reports.map(r=>r.id===id?{...r,title}:r))}/>}
    {reportPage&&<>
      {reports.length>0&&<div className="report-selector"><label htmlFor="active-report">Active research</label><select id="active-report" value={active?.id??''} onChange={e=>{setSelected(e.target.value);setDrawer(null);}}>{!active&&<option value="">Choose a report</option>}{reports.map(r=><option key={r.id} value={r.id}>{r.result.mode==='offline_sample'?'[Demo] ':''}{r.title} · {new Date(r.result.analyzed_at).toLocaleString()}</option>)}</select></div>}
      {!result?<EmptyResearch/>:<div className="report-content space-y-6" key={active!.id}>
        {result.mode==='offline_sample'&&<div className="notice warning" role="note"><FlaskConical size={20}/><div><strong>Demo data — not a live result</strong><p>{result.disclaimer}</p></div></div>}
        {page==='reports'&&<><div className="report-actions"><button className="secondary-button" onClick={()=>downloadReport(active!)}><FileDown size={17}/> Export JSON</button><button className="secondary-button" onClick={()=>window.print()}><Printer size={17}/> Print / save PDF</button><a className="secondary-button" href="/dashboard/graph">Explore evidence graph</a></div><div className="mode-switch" role="group" aria-label="Report view"><button aria-pressed={view==='simple'} onClick={()=>setView('simple')}>Simple view</button><button aria-pressed={view==='research'} onClick={()=>setView('research')}>Research view</button></div><p className="section-description mb-5">{view==='simple'?'Plain language, same evidence and same counts as Research view.':'Full evidence, coverage matrix, graph, and checklist.'}</p>{view==='simple'?<SimpleView result={result}/>:<><Overview result={result}/><section className="panel"><h2>Evidence-backed passages</h2><p className="section-description">Extractive highlights, not generated answers. Quotations match the collected text; that does not establish their truth.</p>{result.coverage.filter(c=>c.evidence.length).map(c=><article className="evidence-highlight" key={c.question_id}><h3>{c.question}</h3>{c.evidence.slice(0,2).map((e,i)=><blockquote key={i}><button className="source-chip" onClick={()=>{const s=result.sources.find(s=>s.id===e.source_id);if(s)openSource(s,c.question_id);}}>{e.source_id}</button> “{e.quote}”</blockquote>)}</article>)}</section></>}</>}
        {(page==='gaps'||(page==='reports'&&view==='research'))&&<><CoverageMatrix result={result} onOpenSource={openSource}/><GapList result={result} onOpenSource={openSource}/></>}
        {(page==='conflicts'||(page==='reports'&&view==='research'))&&<ConflictExplorer result={result} onOpenSource={openSource}/>}
        {page==='graph'&&<EvidenceGraph result={result} onOpenSource={openSource}/>}
        {(page==='freshness'||(page==='reports'&&view==='research'))&&<Warnings result={result} onOpenSource={openSource}/>}
        {(page==='checklist'||(page==='reports'&&view==='research'))&&checklist}
        {(page==='sources'||(page==='reports'&&view==='research'))&&<SourceLibrary result={result} onOpenSource={openSource}/>}
        {page==='reports'&&<SuggestedQuestions result={result} onAdd={(question)=>{setMode('live');setForm({...EMPTY_FORM,goal:result.goal,questions:[question]});setFormError(null);setError(null);setPhase('idle');navigate('/dashboard/new-research');}}/>}
        {page==='reports'&&<AskGapLens result={result} onOpenSource={openSource}/>}
        <p className="report-disclaimer">{result.disclaimer} A matched quote validates provenance, not accuracy. Sources may share an origin; multiple matches do not establish independent corroboration.</p>
      </div>}
    </>}
    {page==='settings'&&<div className="space-y-5"><section className="panel"><h2>Appearance</h2><p className="section-description">Choose a comfortable workspace.</p><button className="secondary-button mt-4" onClick={()=>setDark(!dark)}>Switch to {dark?'light':'dark'} theme</button></section><section className="panel"><h2>Analysis connection</h2><p className="section-description">{health?`Backend ${health.version} is connected. ${health.groq_configured?'Optional AI question suggestions are configured; provider availability is checked on each run.':'No AI key configured. Free deterministic analysis and template questions are available.'}`:healthError??'Checking connection…'}</p><button className="secondary-button mt-4" onClick={checkHealth}><RefreshCw size={16}/> Check connection</button></section><section className="panel"><h2>Your local data</h2><p className="section-description">Reports, quoted passages, source URLs and checklist progress are saved in this browser. They are not synced between devices. Full source text is processed per request by the backend. Export reports before clearing browser data.</p><button className="secondary-button mt-4" onClick={()=>setResetConfirm(true)}>Clear saved research</button>{resetConfirm&&<div className="notice warning mt-4" role="alert"><p>Remove all GapLens reports and verification progress from this browser?</p><button className="secondary-button" onClick={()=>{try{localStorage.removeItem(STORAGE_KEY);setStorageBlocked(false);setStorageError(null);setReports([]);reportsRef.current=[];setSelected('');setResetConfirm(false);}catch{setStorageError('Browser storage could not be cleared.');}}}>Clear all reports</button><button className="secondary-button" onClick={()=>setResetConfirm(false)}>Cancel</button></div>}</section><section className="panel"><h2>GapLens 2.0</h2><p className="section-description">A local evidence workspace for Digital Dark Spot. Keyword coverage can miss paraphrases and can match irrelevant text. Numeric or stance differences are possible conflicts, not confirmed contradictions. Publication dates are metadata, not proof of accuracy.</p></section></div>}
    {!pages.some(p=>p[0]===page)&&<section className="panel"><h2>Page not found</h2><a className="primary-button mt-4" href="/dashboard">Return to dashboard</a></section>}
  </DashboardLayout>}
  <SourceDrawer source={drawer?.source??null} result={result} focusQuestionId={drawer?.focusQuestionId} onClose={closeDrawer}/>
  </>;
}
