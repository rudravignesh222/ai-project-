import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownToLine, ArrowRight, Check, ChevronDown, Code2, FileCode2, FileText, Folder, Github, LoaderCircle, LockKeyhole, Rocket, ShieldCheck, Sparkles, UploadCloud, X } from 'lucide-react'

const API = '/api'
async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { credentials: 'include', ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`)
  return data
}
const languages = ['React + FastAPI', 'Python', 'JavaScript + Node.js', 'React + Node.js', 'HTML + CSS + JavaScript', 'Java + Spring Boot', 'C++', 'Custom / specify in requirements']

export default function App() {
  const [topic, setTopic] = useState('')
  const [language, setLanguage] = useState(languages[0])
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [project, setProject] = useState(null)
  const [files, setFiles] = useState({})
  const [selected, setSelected] = useState('')
  const [github, setGithub] = useState(false)
  const [repos, setRepos] = useState([])
  const [existingRepo, setExistingRepo] = useState('')
  const [repoName, setRepoName] = useState('my-ai-generated-project')
  const [description, setDescription] = useState('Generated with AI Project Builder')
  const [visibility, setVisibility] = useState('private')
  const [branch, setBranch] = useState('main')
  const [showPublish, setShowPublish] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api('/health').then(setHealth).catch(() => {})
    if (new URLSearchParams(location.search).get('github') === 'connected') {
      setGithub(true); setStatus('GitHub connected successfully.')
      history.replaceState({}, '', location.pathname)
      api('/github/repositories').then(setRepos).catch(e => setError(e.message))
    }
  }, [])
  const fileNames = useMemo(() => Object.keys(files).sort(), [files])
  const selectedContent = files[selected] || ''

  async function generate() {
    setError(''); setStatus('')
    if (topic.trim().length < 10 && !file) { setError('Enter at least 10 characters of project requirements or upload a document.'); return }
    setBusy(true); setStatus('Analyzing requirements and generating source files…')
    try {
      let finalTopic = topic
      if (file) {
        const form = new FormData(); form.append('file', file); form.append('topic', topic); form.append('language', language)
        const analyzed = await api('/projects/analyze', { method: 'POST', body: form })
        finalTopic = analyzed.topic
      }
      const result = await api('/projects/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic: finalTopic, language }) })
      const loaded = await api(`/projects/${result.project_id}/files`)
      setProject(result); setFiles(loaded.files); setSelected(Object.keys(loaded.files).sort()[0] || '')
      setRepoName((result.project_name || 'generated-project').toLowerCase().replace(/[^a-z0-9_.-]/g, '-').slice(0, 90))
      setStatus(`Generated ${result.file_count} files successfully. Review them before downloading or publishing.`)
    } catch (e) { setError(e.message); setStatus('') }
    finally { setBusy(false) }
  }
  async function connectGithub() {
    try {
      const response = await fetch(`${API}/github/login`, { credentials: 'include', redirect: 'manual' })
      // Browsers may hide cross-origin redirect details; navigate to the endpoint directly instead.
      if (response.status >= 400) { const d = await response.json().catch(() => ({})); throw new Error(d.detail || 'Could not start GitHub OAuth.') }
      location.href = `${API}/github/login`
    } catch (e) { setError(e.message) }
  }
  async function refreshRepos() {
    setError('')
    try { const data = await api('/github/repositories'); setRepos(data); setGithub(true); setStatus('GitHub repositories loaded.') }
    catch (e) { setError(e.message); setGithub(false) }
  }
  async function publish() {
    if (!project) return
    setError(''); setBusy(true); setStatus('Publishing files to GitHub…')
    try {
      const result = await api('/github/publish', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: project.project_id, repo_name: repoName, description, visibility, branch, existing_repo: existingRepo || null, confirm: true }) })
      setStatus(`Published ${result.files_published} files. Commit: ${result.commit_sha.slice(0, 7)}.`)
      window.open(result.repository_url, '_blank', 'noopener,noreferrer')
      setShowPublish(false)
    } catch (e) { setError(e.message); setStatus('') }
    finally { setBusy(false) }
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Code2 size={22}/></div><div><b>AI Project Builder</b><small>BUILD · REVIEW · SHIP</small></div></div>
      <div className="side-label">WORKSPACE</div>
      <a className="nav active"><Activity size={17}/> Project Builder <span className="nav-dot"/></a>
      <a className="nav"><Folder size={17}/> My projects <span className="soon">SOON</span></a>
      <div className="sidebar-bottom"><div className="secure-icon"><ShieldCheck size={18}/></div><b>Secure by design</b><p>API keys stay on the backend. Review generated code before running it.</p><div className="backend-status"><span className={health ? 'green-dot' : 'gray-dot'}/>{health ? 'Backend connected' : 'Checking backend…'}</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="crumb">Workspace <span>/</span> <b>Project Builder</b></div><div className="top-actions"><span className="status-pill"><span className="green-dot"/> {health?.ai_configured ? 'AI provider ready' : 'AI setup required'}</span><button className="github-top" onClick={connectGithub}><Github size={16}/> Connect GitHub</button></div></header>
      <div className="content">
        <section className="hero"><div className="hero-copy"><div className="eyebrow"><Sparkles size={14}/> YOUR IDEA, BUILT FASTER</div><h1>Turn your idea into<br/><span>working code.</span></h1><p>Describe what you want to build. Generate a structured codebase, inspect every file, then download it or publish directly to GitHub.</p><div className="hero-points"><span><Check size={15}/> Full project files</span><span><Check size={15}/> ZIP download</span><span><Check size={15}/> GitHub publishing</span></div></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="code-window"><div className="window-head"><i/><i/><i/><span>project.config</span></div><div className="code-lines"><div><em>01</em><span className="purple">const</span> <b>project</b> = {'{'}</div><div><em>02</em>&nbsp; <span className="blue">idea</span>: <span className="yellow">'your next big thing'</span>,</div><div><em>03</em>&nbsp; <span className="blue">quality</span>: <span className="green">"production-minded"</span>,</div><div><em>04</em>&nbsp; <span className="blue">status</span>: <span className="green">"ready to build"</span></div><div><em>05</em>{'}'}</div></div><div className="window-foot"><span><span className="green-dot"/> System ready</span><span>UTF-8</span></div></div><div className="floating-badge"><Sparkles size={16}/><span><b>AI-powered</b><small>Code generation</small></span></div></div></section>
        <section className="builder-grid">
          <div className="panel input-panel"><div className="panel-heading"><div className="step-icon">01</div><div><h2>Define your project</h2><p>Start with a clear description of the problem and solution.</p></div></div>
            <label className="field-label" htmlFor="topic">PROJECT REQUIREMENTS <span>REQUIRED</span></label>
            <textarea id="topic" value={topic} onChange={e => setTopic(e.target.value)} placeholder="Example: Build an AI-powered code vulnerability detection system that scans source code, identifies security issues, explains the risks, and recommends secure fixes…" rows={7}/>
            <div className="textarea-footer"><span>{topic.length.toLocaleString()} / 30,000 characters</span><span>Be specific for better results</span></div>
            <label className="upload-zone"><input type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0] || null)}/><div className="upload-icon"><UploadCloud size={20}/></div><div><b>{file ? file.name : 'Upload a project brief'}</b><small>{file ? `${(file.size / 1024).toFixed(0)} KB · selected` : 'PDF, DOCX, TXT or image · max 10 MB'}</small></div>{file ? <button type="button" className="remove-file" onClick={e => { e.preventDefault(); setFile(null) }}><X size={16}/></button> : <span className="browse">Browse files</span>}</label>
            <label className="field-label" htmlFor="language">PREFERRED LANGUAGE / FRAMEWORK</label><div className="select-wrap"><Code2 size={17}/><select id="language" value={language} onChange={e => setLanguage(e.target.value)}>{languages.map(l => <option key={l}>{l}</option>)}</select><ChevronDown size={16}/></div>
            <button className="primary-btn generate-btn" disabled={busy} onClick={generate}>{busy ? <LoaderCircle className="spin" size={18}/> : <Sparkles size={18}/>} {busy ? 'Generating project…' : 'Generate project'} <ArrowRight size={17}/></button>
            <p className="privacy-note"><LockKeyhole size={13}/> Your API keys are never exposed in the browser.</p>
          </div>
          <div className="panel output-panel"><div className="panel-heading"><div className="step-icon step-two">02</div><div><h2>Generated workspace</h2><p>Explore your source files and prepare to ship.</p></div>{project && <span className="file-count">{fileNames.length} FILES</span>}</div>
            {!project ? <div className="empty-workspace"><div className="empty-graphic"><div className="empty-file"><FileCode2 size={28}/></div><div className="empty-spark"><Sparkles size={17}/></div></div><h3>Your code workspace awaits</h3><p>Generated files will appear here, organized into a browsable project tree with a code preview.</p><div className="empty-steps"><span><i>1</i> Describe</span><ArrowRight size={13}/><span><i>2</i> Generate</span><ArrowRight size={13}/><span><i>3</i> Ship</span></div></div> :
              <><div className="file-explorer"><div className="tree-head"><Folder size={14}/> {project.project_name || 'generated-project'} <span>{fileNames.length} items</span></div><div className="file-list">{fileNames.map(name => <button key={name} className={`file-row ${selected === name ? 'selected' : ''}`} onClick={() => setSelected(name)}><FileText size={15}/><span>{name}</span>{selected === name && <span className="selected-dot"/>}</button>)}</div></div><div className="preview-head"><span><Code2 size={14}/> {selected || 'Select a file'}</span><span>PREVIEW</span></div><pre className="code-preview"><code>{selectedContent || 'Select a file to preview its contents.'}</code></pre>
              <div className="output-actions"><a className="secondary-btn" href={project ? `${API}/projects/${project.project_id}/download` : '#'} onClick={e => { if (!project) e.preventDefault() }}><ArrowDownToLine size={16}/> Download ZIP</a><button className="primary-btn publish-btn" onClick={() => { setShowPublish(true); setConfirmed(false) }}><Rocket size={16}/> Publish to GitHub</button></div></>}
          </div>
        </section>
        {(status || error) && <div className={`notice ${error ? 'notice-error' : 'notice-success'}`} role="status">{error ? <X size={17}/> : <Check size={17}/>}<span>{error || status}</span><button onClick={() => {setError('');setStatus('')}}><X size={15}/></button></div>}
        <section className="bottom-grid"><div className="info-card"><div className="info-icon purple-bg"><ShieldCheck size={19}/></div><div><h3>Review before you run</h3><p>AI-generated code can contain bugs or vulnerabilities. Inspect files and test in a safe environment before deployment.</p></div></div><div className="info-card"><div className="info-icon blue-bg"><Github size={19}/></div><div><h3>Your repository, your control</h3><p>GitHub publishing happens only after OAuth authorization and your explicit confirmation.</p></div></div></section>
        <footer>AI Project Builder <span>·</span> Built for ideas that deserve to ship <span className="footer-right">Version 1.0.0</span></footer>
      </div>
    </main>
    {showPublish && <div className="modal-backdrop" role="presentation" onMouseDown={e => { if(e.target === e.currentTarget) setShowPublish(false) }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="publish-title"><button className="modal-close" onClick={() => setShowPublish(false)}><X size={18}/></button><div className="modal-icon"><Github size={24}/></div><h2 id="publish-title">Publish to GitHub</h2><p className="modal-sub">Review the destination and confirm before files are committed.</p>
      {!github ? <div className="connect-box"><Github size={20}/><div><b>Connect your GitHub account</b><small>Authorize AI Project Builder to access repositories.</small></div><button className="secondary-btn" onClick={connectGithub}>Connect</button></div> : <div className="connected-line"><span className="green-dot"/> GitHub connected <button onClick={refreshRepos}>Refresh repositories</button></div>}
      <label className="field-label">DESTINATION</label><div className="select-wrap"><Folder size={16}/><select value={existingRepo} onChange={e => setExistingRepo(e.target.value)}><option value="">Create a new repository</option>{repos.map(r => <option key={r.full_name} value={r.full_name}>Existing: {r.full_name}{r.private ? ' (private)' : ''}</option>)}</select><ChevronDown size={15}/></div>
      {!existingRepo && <><label className="field-label">REPOSITORY NAME</label><input className="text-input" value={repoName} onChange={e => setRepoName(e.target.value)} maxLength={100}/><label className="field-label">DESCRIPTION</label><input className="text-input" value={description} onChange={e => setDescription(e.target.value)} maxLength={350}/><label className="field-label">VISIBILITY</label><div className="visibility-options"><button className={visibility === 'private' ? 'chosen' : ''} onClick={() => setVisibility('private')}><LockKeyhole size={15}/> Private</button><button className={visibility === 'public' ? 'chosen' : ''} onClick={() => setVisibility('public')}><Github size={15}/> Public</button></div></>}
      <label className="field-label">TARGET BRANCH</label><input className="text-input" value={branch} onChange={e => setBranch(e.target.value)} maxLength={100}/>
      <div className="review-box"><b>Files to publish ({fileNames.length})</b><div>{fileNames.slice(0, 5).map(f => <span key={f}><FileText size={13}/>{f}</span>)}{fileNames.length > 5 && <small>and {fileNames.length - 5} more files…</small>}</div></div>
      <label className="confirm-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed these files and confirm publishing them to GitHub.</label>
      <button className="primary-btn modal-publish" disabled={!github || !confirmed || busy || !project || !branch.trim() || (!existingRepo && !repoName.trim())} onClick={publish}>{busy ? <LoaderCircle className="spin" size={17}/> : <Rocket size={17}/>} {busy ? 'Publishing…' : 'Confirm and publish'} </button>
      <small className="modal-warning"><LockKeyhole size={12}/> Secret files are blocked by the backend before publishing.</small>
    </div></div>}
  </div>
}
