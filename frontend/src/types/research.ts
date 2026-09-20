export type AgentName = 'orchestrator' | 'researcher' | 'analyst' | 'writer';
export type AgentStatus = 'idle' | 'running' | 'completed' | 'warning' | 'failed';

export interface Source {
  url: string;
  title: string;
  snippet?: string;
  published_at?: string;
}

export interface Citation {
  id: number;
  title: string;
  url: string;
  snippet: string;
}

export interface WriterOutput {
  status: 'complete' | 'partial';
  title: string;
  content: string;
  citations: Citation[];
  warnings: string[];
}

export interface AgentStatusEvent {
  event_id?: string;
  thread_id?: string;
  type: 'agent_status';
  agent: AgentName;
  status: Exclude<AgentStatus, 'idle'>;
  progress: number;
  message: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
}

export interface WebSocketMessage {
  type: 'connection_ack' | 'agent_status' | 'sources_updated' | 'analysis_summary' | 'final_report' | 'error';
  agent?: AgentName;
  payload?: unknown;
  detail?: string;
  message?: string;
}

export interface ResearchState {
  isConnected: boolean;
  isConnecting: boolean;
  isResearching: boolean;
  error: string | null;
  agentStatus: Partial<Record<AgentName, AgentStatusEvent>>;
  sources: Source[];
  report: WriterOutput | null;
}
