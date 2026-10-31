import { useState } from 'react';
import { Network, ArrowUpRight } from 'lucide-react';
import type { AnalysisResponse, SourceRecord } from '../lib/types';

type Node = {id:string; x:number; y:number; label:string; kind:string; detail:string; sourceId?:string};
export function EvidenceGraph({ result, onOpenSource }: {result:AnalysisResponse; onOpenSource:(source:SourceRecord, question?:string)=>void}) {
  const [questionId, setQuestionId] = useState(result.coverage[0]?.question_id ?? '');
  const [selected, setSelected] = useState('question');
  const [zoom, setZoom] = useState(1);
  const row = result.coverage.find(c=>c.question_id===questionId) ?? result.coverage[0];
  if(!row) return <section className="panel">No questions are available for this report.</section>;
  const gaps=result.gaps.filter(g=>g.question_id===row.question_id);
  const conflicts=result.conflicts.filter(c=>c.question_id===row.question_id);
  const height=Math.max(390,row.evidence.length*90+100,(gaps.length+conflicts.length)*85+140);
  const nodes:Node[]=[{id:'question',x:20,y:height/2-26,label:row.question_id+' · Research question',kind:'question',detail:row.question}];
  const edges:{from:string;to:string}[]=[];
  row.evidence.forEach((e,i)=>{
    const source=result.sources.find(s=>s.id===e.source_id);
    nodes.push({id:'claim'+i,x:290,y:35+i*90,label:'Passage '+(i+1),kind:'passage',detail:e.quote,sourceId:e.source_id});
    nodes.push({id:'source'+i,x:640,y:35+i*90,label:e.source_id+' · '+(source?.title ?? 'Source'),kind:'source',detail:source?.text_excerpt ?? 'No opening excerpt.',sourceId:e.source_id});
    edges.push({from:'question',to:'claim'+i},{from:'claim'+i,to:'source'+i});
  });
  gaps.forEach((g,i)=>{nodes.push({id:'gap'+i,x:20,y:35+i*65,label:g.severity+' · '+g.kind.replace(/_/g,' '),kind:'gap',detail:g.detail});edges.push({from:'question',to:'gap'+i});});
  conflicts.forEach((c,i)=>{nodes.push({id:'conflict'+i,x:290,y:height-65,label:'Possible conflict',kind:'conflict',detail:c.detail});edges.push({from:'question',to:'conflict'+i});c.values.forEach(v=>{const index=row.evidence.findIndex(e=>e.source_id===v.source_id);if(index>=0)edges.push({from:'conflict'+i,to:'claim'+index});});});
  const node=nodes.find(n=>n.id===selected) ?? nodes[0];
  const source=result.sources.find(s=>s.id===node.sourceId);
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">FOLLOW THE SOURCE</p><h2><Network size={23}/> Evidence graph</h2><p>Explore one question at a time. Every passage links to a real collected source.</p></div></div>
    <div className="graph-controls"><label>Research question<select value={row.question_id} onChange={e=>{setQuestionId(e.target.value);setSelected('question');}}>{result.coverage.map(c=><option key={c.question_id} value={c.question_id}>{c.question_id} · {c.question}</option>)}</select></label><label>Zoom {Math.round(zoom*100)}%<input type="range" aria-label="Graph zoom" min="0.7" max="1.5" step="0.1" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label></div>
    <div className="graph-legend"><span>Question</span><span>Quoted passage</span><span>Source</span><span>Potential gap / conflict</span></div>
    <div className="graph-canvas"><svg width={900*zoom} height={height*zoom} viewBox={`0 0 900 ${height}`} aria-label={`Evidence graph for ${row.question}`}>
      {edges.map((edge,i)=>{const a=nodes.find(n=>n.id===edge.from)!, b=nodes.find(n=>n.id===edge.to)!;return <path key={i} d={`M ${a.x+110} ${a.y+26} C ${a.x+240} ${a.y+26}, ${b.x-80} ${b.y+26}, ${b.x+110} ${b.y+26}`} className={selected===a.id || selected===b.id ? 'graph-edge selected' : 'graph-edge'}/>;})}
      {nodes.map(n=><g key={n.id} role="button" tabIndex={0} aria-label={`${n.kind}: ${n.label}`} aria-pressed={node.id===n.id} className={`graph-node ${n.kind} ${node.id===n.id ? 'selected' : ''}`} onClick={()=>setSelected(n.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(n.id);}}}><title>{n.label}</title><rect x={n.x} y={n.y} width="220" height="52" rx="12"/><text x={n.x+14} y={n.y+31}>{n.label.length>27 ? n.label.slice(0,26)+'…' : n.label}</text></g>)}
    </svg></div>
    <div className="graph-detail" aria-live="polite"><p className="eyebrow">{node.kind === 'passage' ? 'VERBATIM MATCH · NOT FACT VERIFICATION' : node.kind.toUpperCase()}</p><h3>{node.kind==='question' ? row.question : node.label}</h3><p className={node.kind==='passage' ? 'quote-text' : ''}>{node.detail}</p>{source && <button className="secondary-button" onClick={()=>onOpenSource(source,row.question_id)}>Inspect {source.id} · {source.title} <ArrowUpRight size={16}/></button>}{node.kind==='conflict' && conflicts.flatMap(c=>c.values).map((v,i)=><blockquote key={i} className="quote-text">{v.source_id}: “{v.quote}”</blockquote>)}</div>
  </section>;
}
