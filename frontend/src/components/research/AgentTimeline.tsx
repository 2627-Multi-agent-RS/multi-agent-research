import { Check, CircleAlert, CircleDashed, LoaderCircle } from 'lucide-react';
import type { AgentName, AgentStatusEvent } from '../../types/research';

const agents: Array<{ id: AgentName; label: string; description: string }> = [
  { id: 'orchestrator', label: 'Lập kế hoạch', description: 'Phân rã câu hỏi nghiên cứu' },
  { id: 'researcher', label: 'Thu thập dữ liệu', description: 'Tìm kiếm và đọc nguồn gốc' },
  { id: 'analyst', label: 'Đối soát', description: 'Kiểm chứng và tìm mâu thuẫn' },
  { id: 'writer', label: 'Viết báo cáo', description: 'Tổng hợp kết quả và trích dẫn' },
];

interface AgentTimelineProps {
  statuses: Partial<Record<AgentName, AgentStatusEvent>>;
}

export function AgentTimeline({ statuses }: AgentTimelineProps) {
  return (
    <section className="timeline-panel" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Live pipeline</p>
          <h2 id="timeline-title">Tiến trình nghiên cứu</h2>
        </div>
        <span className="live-dot"><i /> LIVE</span>
      </div>
      <div className="timeline-list">
        {agents.map((agent, index) => {
          const event = statuses[agent.id];
          const status = event?.status ?? 'idle';
          const Icon = status === 'completed' ? Check : status === 'warning' || status === 'failed' ? CircleAlert : status === 'running' ? LoaderCircle : CircleDashed;
          return (
            <div className={`timeline-item status-${status}`} key={agent.id}>
              <div className="timeline-marker"><Icon size={18} className={status === 'running' ? 'spin' : ''} /></div>
              {index < agents.length - 1 && <div className="timeline-line" />}
              <div className="timeline-copy">
                <div className="timeline-title-row">
                  <div><strong>{agent.label}</strong><span>{agent.description}</span></div>
                  <span className="status-label">{status === 'idle' ? 'Chờ' : status === 'running' ? `${event?.progress ?? 0}%` : status === 'completed' ? 'Xong' : 'Cảnh báo'}</span>
                </div>
                {event?.message && <p>{event.message}</p>}
                {status === 'running' && <div className="progress-track"><div style={{ width: `${Math.min(100, Math.max(0, event?.progress ?? 0))}%` }} /></div>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
