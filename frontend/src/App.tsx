import { Activity, ArrowUpRight, Cable, FileText, RefreshCw, ShieldCheck } from 'lucide-react';
import { useId } from 'react';
import { AgentTimeline } from './components/research/AgentTimeline';
import { ResearchInput } from './components/research/ResearchInput';
import { useResearchSocket } from './hooks/useResearchSocket';

function App() {
  const threadId = useId();
  const { isConnected, isConnecting, isResearching, error, agentStatus, report, startResearch, reconnect } = useResearchSocket(threadId);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="MAS Research Desk home"><span className="brand-mark"><Activity size={19} /></span><span>MAS <b>Research Desk</b></span></a>
        <div className="connection-pill"><span className={isConnected ? 'connection-dot connected' : 'connection-dot'} />{isConnected ? 'Gateway connected' : isConnecting ? 'Connecting...' : 'Gateway offline'}<span className="thread-id">#{threadId.replace(/:/g, '').slice(-6)}</span></div>
      </header>

      <section className="hero-section">
        <div className="hero-copy">
          <p className="eyebrow">Multi-agent intelligence / 01</p>
          <h1>Biến câu hỏi lớn thành <em>hiểu biết rõ ràng.</em></h1>
          <p className="hero-lede">Một không gian nghiên cứu trực tiếp, nơi bốn agent phối hợp tìm kiếm, kiểm chứng và viết báo cáo có nguồn dẫn.</p>
        </div>
        <div className="hero-signal"><Cable size={18} /><span>Realtime orchestration</span><ArrowUpRight size={17} /></div>
      </section>

      <section className="workspace-grid">
        <div className="primary-column">
          <div className="input-panel"><ResearchInput disabled={isResearching} isConnected={isConnected} onSubmit={startResearch} /></div>
          {error && <div className="error-banner" role="alert"><ShieldCheck size={18} /><span>{error}</span><button onClick={reconnect} type="button" title="Kết nối lại"><RefreshCw size={16} /></button></div>}
          <AgentTimeline statuses={agentStatus} />
          {report && <article className="report-preview"><div className="section-heading"><div><p className="eyebrow">Final output</p><h2>{report.title}</h2></div><FileText size={21} /></div><div className="report-content">{report.content}</div></article>}
        </div>
        <aside className="side-column">
          <div className="side-heading"><p className="eyebrow">Session notes</p><h2>Research control</h2></div>
          <div className="metric-block"><span>Agent coverage</span><strong>04 <small>agents</small></strong></div>
          <div className="metric-block"><span>Evidence mode</span><strong>Strict <small>grounding</small></strong></div>
          <div className="side-note"><span className="note-index">A1</span><p>Mỗi kết luận được nối với nguồn dữ liệu để bạn có thể kiểm tra lại.</p></div>
          <div className="side-footer"><span>Thread</span><code>{threadId}</code></div>
        </aside>
      </section>
    </main>
  );
}

export default App;
