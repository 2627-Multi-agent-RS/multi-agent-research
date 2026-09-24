import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  AgentName,
  AgentStatusEvent,
  ResearchState,
  Source,
  WebSocketMessage,
  WriterOutput,
} from '../types/research';

const SOCKET_URL =
  import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/research';

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY = 800;

const isAgentName = (value: unknown): value is AgentName =>
  ['orchestrator', 'researcher', 'analyst', 'writer'].includes(value as string);

export function useResearchSocket(threadId: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const reconnectAttemptRef = useRef(0);
  const manualCloseRef = useRef(false);

  const [state, setState] = useState<ResearchState>({
    isConnected: false,
    isConnecting: true,
    isResearching: false,
    error: null,
    agentStatus: {},
    sources: [],
    report: null,
  });

  const connect = useCallback(() => {
    if (manualCloseRef.current) return;

    const currentSocket = socketRef.current;

    // Không tạo connection mới nếu socket hiện tại
    // đang CONNECTING hoặc OPEN.
    if (
      currentSocket &&
      (currentSocket.readyState === WebSocket.CONNECTING ||
        currentSocket.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    setState((current) => ({
      ...current,
      isConnecting: true,
    }));

    const socket = new WebSocket(SOCKET_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      // Bỏ qua event của socket cũ.
      if (socketRef.current !== socket) return;

      reconnectAttemptRef.current = 0;

      setState((current) => ({
        ...current,
        isConnected: true,
        isConnecting: false,
        error: null,
      }));
    };

    socket.onmessage = (event) => {
      // Bỏ qua message của socket cũ.
      if (socketRef.current !== socket) return;

      try {
        const message = JSON.parse(event.data) as WebSocketMessage;

        if (
          message.type === 'agent_status' &&
          isAgentName(message.agent)
        ) {
          const status = message as unknown as AgentStatusEvent;

          setState((current) => ({
            ...current,
            isResearching:
              status.status !== 'completed' &&
              status.status !== 'failed',
            agentStatus: {
              ...current.agentStatus,
              [status.agent]: status,
            },
          }));
        } else if (message.type === 'sources_updated') {
          const payload = message.payload as
            | { sources?: Source[] }
            | undefined;

          setState((current) => ({
            ...current,
            sources: payload?.sources ?? [],
          }));
        } else if (message.type === 'final_report') {
          setState((current) => ({
            ...current,
            isResearching: false,
            report: message.payload as WriterOutput,
          }));
        } else if (message.type === 'error') {
          setState((current) => ({
            ...current,
            isResearching: false,
            error:
              message.detail ??
              message.message ??
              'Backend error',
          }));
        }
      } catch {
        setState((current) => ({
          ...current,
          error: 'Không đọc được dữ liệu từ máy chủ.',
        }));
      }
    };

    socket.onerror = () => {
      // Bỏ qua lỗi của socket cũ.
      if (socketRef.current !== socket) return;

      setState((current) => ({
        ...current,
        error: 'Không thể kết nối tới backend research.',
      }));
    };

    socket.onclose = () => {
      // Nếu đây không còn là socket hiện tại,
      // không được thay đổi state hoặc socketRef.
      if (socketRef.current !== socket) return;

      socketRef.current = null;

      setState((current) => ({
        ...current,
        isConnected: false,
        isConnecting: false,
      }));

      if (
        !manualCloseRef.current &&
        reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        const delay =
          INITIAL_RECONNECT_DELAY *
          2 ** reconnectAttemptRef.current;

        reconnectAttemptRef.current += 1;

        reconnectTimerRef.current = window.setTimeout(
          connect,
          delay,
        );
      }
    };
  }, []);

  useEffect(() => {
    manualCloseRef.current = false;

    connect();

    return () => {
      manualCloseRef.current = true;

      if (reconnectTimerRef.current !== undefined) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = undefined;
      }

      const socket = socketRef.current;

      if (socket) {
        socketRef.current = null;
        socket.close();
      }
    };
  }, [connect, threadId]);

  const startResearch = useCallback(
    (topic: string) => {
      const socket = socketRef.current;

      if (
        !socket ||
        socket.readyState !== WebSocket.OPEN
      ) {
        setState((current) => ({
          ...current,
          error:
            'Kết nối chưa sẵn sàng. Vui lòng thử lại.',
        }));

        return false;
      }

      setState((current) => ({
        ...current,
        isResearching: true,
        error: null,
        report: null,
        sources: [],
        agentStatus: {},
      }));

      socket.send(
        JSON.stringify({
          topic,
          thread_id: threadId,
        }),
      );

      return true;
    },
    [threadId],
  );

  return {
    ...state,
    startResearch,
    reconnect: connect,
  };
}