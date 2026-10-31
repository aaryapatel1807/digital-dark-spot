import { ArrowRight, BookOpen, CheckCheck, Clock3, FileText, GitCompareArrows, House, LayoutDashboard, Menu, Moon, Network, Plus, ScanSearch, Settings, ShieldCheck, Sun, X } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';

export const pages = [
  ['', 'Overview', LayoutDashboard], ['new-research', 'New research', Plus], ['my-research', 'My research', BookOpen],
  ['gaps', 'Gap detector', ScanSearch], ['conflicts', 'Conflict analyzer', GitCompareArrows],
  ['graph', 'Evidence graph', Network], ['freshness', 'Freshness monitor', Clock3],
  ['checklist', 'Verification checklist', CheckCheck], ['sources', 'Source library', FileText],
  ['reports', 'Reports', FileText], ['settings', 'Settings', Settings],
] as const;

export function Brand() { return <span className="brand"><span className="brand-icon"><ScanSearch size={23}/></span>GapLens<span className="version">2.0</span></span>; }
export function ThemeButton({ dark, toggle }: { dark: boolean; toggle: () => void }) {
  return <button className="icon-button" onClick={toggle} aria-label={dark ? 'Use light theme' : 'Use dark theme'}>{dark ? <Sun size={19}/> : <Moon size={19}/>}</button>;
}
export function Landing({ dark, toggle }: { dark: boolean; toggle: () => void }) {
  const [menu, setMenu] = useState(false);
  return <>
    <header className="landing-nav"><a href="/" aria-label="GapLens home"><Brand/></a><nav className={menu ? 'landing-links is-open' : 'landing-links'} aria-label="Main navigation">
      <a href="#features" onClick={() => setMenu(false)}>Features</a><a href="#how-it-works" onClick={() => setMenu(false)}>How it works</a><a href="#about" onClick={() => setMenu(false)}>About</a>
    </nav><div className="flex items-center gap-2"><ThemeButton dark={dark} toggle={toggle}/><a className="primary-button nav-launch" href="/dashboard">Launch dashboard <ArrowRight size={16}/></a><button className="icon-button mobile-menu" onClick={() => setMenu(!menu)} aria-label="Toggle navigation" aria-expanded={menu}>{menu ? <X/> : <Menu/>}</button></div></header>
    <main id="main-content">
      <section className="hero"><div className="hero-copy rise-in"><p className="eyebrow"><span/> EVIDENCE FIRST. ASSUMPTIONS LAST.</p><h1>Discover what your research is <em>missing.</em></h1><p className="hero-description">Connect your sources. See where they agree, where they differ, and which questions still need an answer.</p><div className="flex flex-wrap gap-3"><a className="primary-button" href="/dashboard/new-research">Start research <ArrowRight size={18}/></a><a className="secondary-button" href="#features">Explore the tools</a></div><p className="hero-note"><ShieldCheck size={16}/> Traceable quotes · Free local analysis · No account needed</p></div>
      <div className="hero-visual rise-in-late"><div className="flex items-center justify-between"><span className="eyebrow">THE EVIDENCE TRAIL</span><span className="small-tag">Illustrative workflow</span></div><div className="visual-question"><ScanSearch size={22}/><span>What do we actually know?</span></div><div className="visual-branches"><div>Source A<br/><small>Original passage</small></div><div>Source B<br/><small>Another perspective</small></div></div><div className="visual-finding"><GitCompareArrows size={20}/><div><strong>A difference worth checking</strong><p>Compare the claims in their original context.</p></div></div><div className="visual-finding"><CheckCheck size={20}/><div><strong>A clear next step</strong><p>Turn uncertainty into a verification task.</p></div></div><p className="hero-note">Your real evidence appears after an analysis.</p></div></section>
      <section id="features" className="landing-section"><p className="eyebrow">LESS GUESSWORK. MORE CONTEXT.</p><h2>A research workspace that shows its work.</h2><div className="feature-grid">{[[ScanSearch,'Find the gaps','Compare questions against collected passages. See missing, partial, and single-source coverage.','gaps'],[GitCompareArrows,'Inspect disagreements','Read competing quotations side by side. Differences are signals to verify, never a verdict.','conflicts'],[Network,'Follow the evidence','Explore connections between questions, source passages, gaps, and possible conflicts.','graph'],[CheckCheck,'Decide what to check next','Keep a prioritized checklist alongside each saved report, with progress stored in your browser.','checklist']].map(([Icon,title,body,page]) => { const I = Icon as typeof ScanSearch; return <a className="feature-card" key={String(title)} href={`/dashboard/${page}`}><I size={24}/><h3>{String(title)}</h3><p>{String(body)}</p><ArrowRight size={18}/></a>; })}</div></section>
      <section id="how-it-works" className="landing-section"><p className="eyebrow">FROM SOURCES TO NEXT STEPS</p><h2>Bring the question. Build the picture.</h2><div className="steps-grid">{[['Frame your goal','Add the specific questions you need to answer.'],['Collect your sources','Paste text or add public webpage URLs.'],['Inspect the findings','Review matching passages, coverage and differences.'],['Verify and export','Track your checks and save a report.']].map(([title,body],i)=><div key={title}><span className="step-number">0{i+1}</span><h3>{title}</h3><p>{body}</p></div>)}</div></section>
      <section id="about" className="landing-section about-section"><div><p className="eyebrow">BUILT FOR THE DIGITAL DARK SPOT</p><h2>The unanswered question matters.</h2><p>GapLens makes uncertainty visible. Findings use transparent keyword and numeric rules, with quotations checked against collected text. Optional AI can suggest research questions. Source matching is not fact-checking, and independent review still matters.</p></div><a className="primary-button" href="/dashboard/new-research">Launch GapLens <ArrowRight size={18}/></a></section>
    </main><footer className="site-footer"><Brand/><span>SHINCHAN Online Hackathon 2026 · Digital Dark Spot</span><a href="#how-it-works">How it works</a></footer>
  </>;
}

export function DashboardLayout({ page, dark, toggle, children, connected }: {page: string; dark:boolean; toggle:()=>void; children:ReactNode; connected:boolean}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => { setMobile(false); }, [page]);
  useEffect(() => {
    if (!mobile) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    navRef.current?.querySelector<HTMLElement>('button')?.focus();
    const key = (e:KeyboardEvent) => {
      if(e.key === 'Escape') {setMobile(false); trigger.current?.focus();}
      if(e.key === 'Tab') {
        const items = Array.from(navRef.current?.querySelectorAll<HTMLElement>('a,button') ?? []).filter(el=>el.offsetParent!==null);
        const first=items[0], last=items[items.length-1];
        if(e.shiftKey && document.activeElement===first){e.preventDefault();last?.focus();}
        else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first?.focus();}
      }
    };
    document.addEventListener('keydown',key);
    return ()=>{document.body.style.overflow=previous;document.removeEventListener('keydown',key);};
  },[mobile]);
  return <div className={`dashboard-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    {mobile && <button className="mobile-scrim" aria-label="Close navigation" onClick={()=>{setMobile(false);trigger.current?.focus();}}/>}
    <aside ref={navRef} className={`sidebar ${mobile ? 'is-open' : ''}`} aria-label="Workspace navigation" role={mobile ? 'dialog' : undefined} aria-modal={mobile || undefined}>
      <div className="sidebar-brand"><a href="/" aria-label="GapLens home"><Brand/></a><button className="icon-button mobile-menu" aria-label="Close navigation" onClick={()=>{setMobile(false);trigger.current?.focus();}}><X/></button></div>
      <p className="sidebar-label">WORKSPACE</p><nav>{pages.map(([id,label,Icon])=><a key={id} href={`/dashboard${id ? '/'+id : ''}`} title={label} className={page===id ? 'active' : ''} aria-current={page===id ? 'page' : undefined}><Icon size={19}/><span>{label}</span></a>)}</nav>
      <div className="sidebar-bottom"><ShieldCheck size={19}/><span>Evidence, with context.<small>Stored on this browser</small></span></div>
    </aside>
    <div className="dashboard-body"><header className="workspace-header"><div className="flex items-center gap-3"><button className="icon-button desktop-menu" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={()=>setCollapsed(!collapsed)}><Menu size={20}/></button><button ref={trigger} className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={mobile} onClick={()=>setMobile(true)}><Menu size={20}/></button><span className="text-sm text-inksoft">Workspace <span className="mx-2">/</span> <strong className="text-ink">{pages.find(p=>p[0]===page)?.[1] ?? 'Page not found'}</strong></span></div><div className="flex items-center gap-3"><span className="connection-label"><span className={connected ? 'connected-dot' : 'disconnected-dot'}/>{connected ? 'Backend connected' : 'Backend offline'}</span><ThemeButton dark={dark} toggle={toggle}/><a href="/" className="icon-button" aria-label="Home"><House size={19}/></a></div></header><main id="main-content" className="workspace-main">{children}</main></div>
  </div>;
}
