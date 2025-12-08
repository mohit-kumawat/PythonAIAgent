"use client";

import { useState, useEffect } from 'react';

type Action = {
  id: string;
  action_type: string;
  reasoning: string;
  status: string;
  created_at: string;
  executed_at?: string;
  is_proactive?: boolean;
  data: any;
  result?: string;
  error?: string;
};

type MemoryStats = {
  decisions: number;
  threads: number;
  knowledge: number;
  actions: number;
};

export default function Dashboard() {
  const [status, setStatus] = useState<any>({});
  const [context, setContext] = useState<string>('');
  const [actions, setActions] = useState<Action[]>([]);
  const [history, setHistory] = useState<Action[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [memoryStats, setMemoryStats] = useState<MemoryStats>({ decisions: 0, threads: 0, knowledge: 0, actions: 0 });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  const fetchData = async () => {
    try {
      const [statusRes, contextRes, actionsRes, historyRes, logsRes, memoryRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/context'),
        fetch('/api/actions'),
        fetch('/api/history?status=COMPLETED&limit=20'),
        fetch('/api/logs'),
        fetch('/api/memory')
      ]);

      setStatus(await statusRes.json());
      const ctx = await contextRes.json();
      setContext(ctx.content);
      const acts = await actionsRes.json();
      setActions(acts.filter((a: Action) => a.status === 'PENDING'));
      const hist = await historyRes.json();
      setHistory(hist);
      const logsData = await logsRes.json();
      setLogs(logsData.logs || []);
      const memData = await memoryRes.json();
      setMemoryStats(memData.stats || { decisions: 0, threads: 0, knowledge: 0, actions: 0 });
      setLoading(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id: string, action: 'APPROVE' | 'REJECT') => {
    await fetch('/api/actions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, action })
    });
    fetchData();
  };

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'EXECUTED': return 'text-green-400';
      case 'FAILED': return 'text-red-400';
      case 'REJECTED': case 'REJECTED_LOGGED': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const renderActionData = (action: Action) => {
    const { action_type, data } = action;

    if (action_type === 'proactive_followup' || data.source === 'stale_task_detection') {
      return (
        <div className="bg-black/30 p-3 rounded text-sm space-y-2 mb-4 border border-gray-700">
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wider">Original Task</span>
            <div className="text-gray-300 mt-1">{data.original_content}</div>
          </div>
          <div>
            <span className="text-purple-400 text-xs uppercase tracking-wider">Suggested Action</span>
            <div className="text-purple-200 mt-1 font-medium">{data.suggested_action}</div>
          </div>
          {data.days_old && (
            <div className="text-xs text-gray-600 mt-2">
              ⚠️ Inactive for {data.days_old} days
            </div>
          )}
        </div>
      );
    }

    if (action_type === 'schedule_reminder') {
      return (
        <div className="bg-black/30 p-3 rounded text-sm space-y-2 mb-4 border border-gray-700">
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wider">Reminder Message</span>
            <div className="text-gray-300 mt-1">{data.message_text || action.reasoning}</div>
          </div>
          <div>
            <span className="text-blue-400 text-xs uppercase tracking-wider">Scheduled For</span>
            <div className="text-blue-200 mt-1 font-mono">{new Date(data.time_iso).toLocaleString()}</div>
          </div>
          <div className="text-xs text-gray-600 mt-1">
            Channel: {data.target_channel_id}
          </div>
        </div>
      );
    }

    if (action_type === 'send_message' || action_type === 'draft_reply') {
      return (
        <div className="bg-black/30 p-3 rounded text-sm space-y-2 mb-4 border border-gray-700">
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wider">Message Content</span>
            <div className="text-gray-300 mt-1 whitespace-pre-wrap border-l-2 border-gray-600 pl-3">{data.message_text}</div>
          </div>
          <div className="text-xs text-gray-600 mt-1">
            Target Channel: {data.target_channel_id}
          </div>
        </div>
      );
    }

    if (action_type === 'send_email_summary' || action_type === 'weekly_report') {
      return (
        <div className="bg-black/30 p-3 rounded text-sm space-y-2 mb-4 border border-gray-700">
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wider">Report Type</span>
            <div className="text-gray-300 mt-1">{action_type === 'weekly_report' ? 'Weekly Status Report' : 'Email Summary'}</div>
          </div>
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wider">Recipient</span>
            <div className="text-gray-300 mt-1">{data.recipient || 'Me'}</div>
          </div>
        </div>
      );
    }

    // Default Fallback
    return (
      <div className="bg-black/30 p-2 rounded text-xs font-mono text-gray-400 mb-4 overflow-x-auto max-h-24 overflow-y-auto">
        {JSON.stringify(data, null, 2)}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans p-6">
      {/* Header */}
      <header className="mb-6 flex justify-between items-center bg-gray-800 p-5 rounded-xl shadow-lg border border-gray-700">
        <div>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            The Real PM
          </h1>
          <p className="text-gray-400 text-sm mt-1">Command Center v2</p>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Status</div>
          <div className={`inline-flex items-center px-3 py-1 rounded-full border ${status.status === 'THINKING' ? 'bg-yellow-900/30 border-yellow-500 text-yellow-300' :
            status.status === 'EXECUTING' ? 'bg-green-900/30 border-green-500 text-green-300' :
              'bg-gray-700 border-gray-600 text-gray-300'
            }`}>
            <span className={`w-2 h-2 rounded-full mr-2 ${status.status === 'THINKING' ? 'bg-yellow-400 animate-pulse' :
              status.status === 'EXECUTING' ? 'bg-green-400 animate-pulse' :
                'bg-gray-400'
              }`}></span>
            {status.status || 'OFFLINE'}
          </div>
          <p className="text-xs text-gray-500 mt-1">{status.detail}</p>
        </div>
      </header>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-2xl font-bold text-blue-400">{actions.length}</div>
          <div className="text-xs text-gray-500 uppercase">Pending Actions</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-2xl font-bold text-green-400">{memoryStats.actions}</div>
          <div className="text-xs text-gray-500 uppercase">Actions Executed</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-2xl font-bold text-purple-400">{memoryStats.decisions}</div>
          <div className="text-xs text-gray-500 uppercase">Decisions Logged</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="text-2xl font-bold text-cyan-400">{memoryStats.knowledge}</div>
          <div className="text-xs text-gray-500 uppercase">Knowledge Entries</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Context & Logs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Project Context */}
          <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-5">
            <h2 className="text-lg font-semibold mb-3 text-blue-300 flex items-center">
              🧠 Project Brain
            </h2>
            <div className="prose prose-invert max-w-none text-sm bg-gray-900/50 p-4 rounded-lg border border-gray-800 h-72 overflow-y-auto whitespace-pre-wrap font-mono">
              {context}
            </div>
          </div>

          {/* System Logs */}
          <div className="bg-black rounded-xl border border-gray-800 p-4">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold text-gray-300">📜 System Logs</h2>
              <span className="text-xs text-gray-600">{logs.length} lines</span>
            </div>
            <div className="font-mono text-xs h-48 overflow-y-auto space-y-1">
              {logs.length === 0 ? (
                <div className="text-gray-600">No logs yet...</div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className={`${log.includes('Error') || log.includes('failed') ? 'text-red-400' :
                    log.includes('successfully') || log.includes('Added') ? 'text-green-400' :
                      log.includes('Starting') || log.includes('Running') ? 'text-yellow-400' :
                        'text-gray-500'
                    }`}>
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Actions */}
        <div className="space-y-6">
          {/* Tab Navigation */}
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('pending')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${activeTab === 'pending'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              Pending ({actions.length})
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${activeTab === 'history'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              History
            </button>
          </div>

          {/* Action Queue / History */}
          <div className={`bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-5 ${activeTab === 'pending' && actions.length > 0 ? 'ring-2 ring-blue-500/50' : ''
            }`}>

            {activeTab === 'pending' ? (
              <div className="space-y-4">
                {actions.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 border-2 border-dashed border-gray-700 rounded-lg">
                    No pending actions.
                    <br /><span className="text-xs text-gray-600">Bot is sleeping. 😴</span>
                  </div>
                ) : (
                  actions.map((action) => (
                    <div key={action.id} className={`bg-gray-900 p-4 rounded-lg shadow-md ${action.is_proactive ? 'border-l-4 border-purple-500' : 'border-l-4 border-blue-500'
                      }`}>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-blue-400 bg-blue-900/30 px-2 py-0.5 rounded">
                            {action.action_type}
                          </span>
                          {action.is_proactive && (
                            <span className="text-xs font-mono text-purple-400 bg-purple-900/30 px-2 py-0.5 rounded">
                              🔮 Proactive
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(action.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-200 mb-3">{action.reasoning}</p>

                      {renderActionData(action)}

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleAction(action.id, 'APPROVE')}
                          className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded text-sm font-medium transition-colors"
                        >
                          ✓ Approve
                        </button>
                        <button
                          onClick={() => handleAction(action.id, 'REJECT')}
                          className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-300 py-2 rounded text-sm font-medium transition-colors"
                        >
                          ✕ Reject
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {history.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">No action history yet.</div>
                ) : (
                  history.map((action) => (
                    <div key={action.id} className="bg-gray-900 p-3 rounded-lg border border-gray-800">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-xs font-mono text-gray-400">
                          {action.action_type}
                        </span>
                        <span className={`text-xs font-medium ${getStatusColor(action.status)}`}>
                          {action.status === 'EXECUTED' ? '✓' : action.status === 'FAILED' ? '✕' : '⊘'} {action.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-300 mb-1 line-clamp-2">{action.reasoning}</p>
                      <div className="text-xs text-gray-600">
                        {action.executed_at
                          ? new Date(action.executed_at).toLocaleString()
                          : new Date(action.created_at).toLocaleString()
                        }
                      </div>
                      {action.error && (
                        <div className="mt-1 text-xs text-red-400 bg-red-900/20 p-1 rounded">
                          {action.error}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
