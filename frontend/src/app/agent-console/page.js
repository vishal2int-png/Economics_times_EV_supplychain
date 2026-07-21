'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Bot, Workflow, AlertTriangle, Send, ChevronRight } from 'lucide-react';
import styles from './Agent.module.css';

const SAMPLE_QUERIES = [
  'Are we exposed to a cobalt disruption?',
  'Which diesel vehicles should we electrify first?',
  'How accurate are our battery RUL predictions?',
  'What is our AIS-156 compliance posture?',
];

export default function AgentConsole() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState(null);
  const [askError, setAskError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [agents, compound] = await Promise.all([
          api.getAgents(),
          api.getCompoundRisk(),
        ]);
        setData({ agents, compound });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function runQuery(q) {
    const text = (q ?? query).trim();
    if (!text || asking) return;
    setAsking(true);
    setAskError(null);
    setResult(null);
    try {
      setResult(await api.askAgents(text));
    } catch (err) {
      setAskError(err.message || 'Agent request failed');
    } finally {
      setAsking(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-center" style={{ height: '100%' }}>
        <div className="animate-pulse">Loading Agent Intelligence...</div>
      </div>
    );
  }

  if (!data) {
    return <div style={{ color: 'var(--danger)' }}>Could not reach the intelligence API.</div>;
  }

  const { agents, compound } = data;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Agent Intelligence Console</h1>
        <p style={{ color: 'var(--text-muted)' }}>
          Specialist agents reason over live tool results — and correlate signals no single module would flag.
        </p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Specialist Agents</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>{agents.agents.length}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Compound Risks</h3>
          <div className={styles.cardValue} style={{ color: 'var(--warning)' }}>{compound.summary.total_findings}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Modules Correlated</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>{compound.summary.modules_correlated.length}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Orchestrator Mode</h3>
          <div className={styles.modeValue}>{agents.orchestrator_mode}</div>
        </div>
      </div>

      {/* ── Ask the agents ─────────────────────────────────────────────── */}
      <div className={`glass-card ${styles.askPanel}`}>
        <h2><Bot size={18} /> Ask the Agent Network</h2>

        <div className={styles.askRow}>
          <input
            className={styles.askInput}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runQuery()}
            placeholder="Ask across battery, supply chain, procurement, carbon and compliance..."
            disabled={asking}
          />
          <button className={styles.askButton} onClick={() => runQuery()} disabled={asking || !query.trim()}>
            <Send size={16} /> {asking ? 'Routing...' : 'Ask'}
          </button>
        </div>

        <div className={styles.chips}>
          {SAMPLE_QUERIES.map((q) => (
            <button key={q} className={styles.chip} onClick={() => { setQuery(q); runQuery(q); }} disabled={asking}>
              {q}
            </button>
          ))}
        </div>

        {askError && <div className={styles.errorBox}>{askError}</div>}

        {result && (
          <div className={styles.resultBox}>
            <div className={styles.traceHeader}>
              <Workflow size={15} />
              <span>
                Planner: <strong>{result.trace.planner}</strong> &nbsp;·&nbsp;
                {result.trace.agents_engaged.length} agent(s) &nbsp;·&nbsp; {result.trace.elapsed_ms} ms
              </span>
            </div>

            <div className={styles.traceSteps}>
              {result.trace.steps.map((step) => (
                <div key={step.agent} className={styles.traceStep}>
                  <div className={styles.traceStepHead}>
                    <ChevronRight size={14} />
                    <strong>{step.agent_name}</strong>
                  </div>
                  <div className={styles.toolTags}>
                    {step.tools_called.map((t) => (
                      <span key={t} className={styles.toolTag}>{t}</span>
                    ))}
                  </div>
                  <p className={styles.traceFinding}>{step.finding}</p>
                </div>
              ))}
            </div>

            <div className={styles.answerBox}>
              <h4>Synthesised Answer</h4>
              <p>{result.answer}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Compound risk findings ─────────────────────────────────────── */}
      <div className={`glass-card ${styles.compoundPanel}`}>
        <h2><AlertTriangle size={18} /> Compound Risk — Cross-Module Correlation</h2>
        <p className={styles.panelSub}>
          Each finding combines signals from different modules. Individually unalarming; together, actionable.
        </p>

        <div className={styles.findingList}>
          {compound.findings.map((f) => (
            <div key={f.id} className={styles.finding} data-severity={f.severity}>
              <div className={styles.findingHead}>
                <span className={styles.severityBadge} data-severity={f.severity}>{f.severity}</span>
                <strong className={styles.findingTitle}>{f.title}</strong>
                <span className={styles.confidence}>conf {(f.confidence * 100).toFixed(0)}%</span>
              </div>

              <p className={styles.findingSummary}>{f.summary}</p>

              <div className={styles.evidenceBlock}>
                <span className={styles.evidenceLabel}>Evidence chain</span>
                {f.evidence.map((e, i) => (
                  <div key={i} className={styles.evidenceRow}>
                    <span className={styles.evidenceModule}>{e.module}</span>
                    <span className={styles.evidenceSignal}>{e.signal}</span>
                  </div>
                ))}
              </div>

              <div className={styles.missBox}>
                <span className={styles.missLabel}>Why one module misses it</span>
                <p>{f.single_module_would_miss}</p>
              </div>

              <div className={styles.actionsBlock}>
                <span className={styles.evidenceLabel}>Recommended actions</span>
                <ul>
                  {f.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Agent roster ───────────────────────────────────────────────── */}
      <div className={`glass-card ${styles.rosterPanel}`}>
        <h2><Bot size={18} /> Agent Roster & Tools</h2>
        <div className={styles.rosterGrid}>
          {agents.agents.map((a) => (
            <div key={a.key} className={styles.agentCard}>
              <strong>{a.name}</strong>
              <p className={styles.agentRole}>{a.role}</p>
              <div className={styles.toolTags}>
                {a.tools.map((t) => (
                  <span key={t.name} className={styles.toolTag} title={t.description}>{t.name}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
