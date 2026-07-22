'use client';

import { useEffect, useState } from 'react';
import { Factory, TrendingUp, GitBranch, AlertTriangle } from 'lucide-react';
import { api } from '../../lib/api';
import VehicleDetail from '../../components/vehicle/VehicleDetail';
import styles from './Quality.module.css';

export default function QualityIntelligence() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('detection');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [metrics, charts, drift, rootCause, flagged, suppliers, trace] = await Promise.all([
          api.getQmsMetrics(),
          api.getQmsControlCharts(),
          api.getQmsDrift(),
          api.getQmsRootCause(),
          api.getQmsFlaggedBatches(),
          api.getQmsSupplierQuality(),
          api.getQmsTraceability(),
        ]);
        setData({ metrics, charts, drift, rootCause, flagged, suppliers, trace });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="flex-center" style={{ height: '100%' }}>
      <div className="animate-pulse">Loading Quality Intelligence…</div>
    </div>;
  }
  if (error) return <div style={{ color: 'var(--danger)' }}>Error: {error}</div>;

  const { metrics, charts, drift, rootCause, flagged, suppliers, trace } = data;
  const early = metrics.early_warning;
  const spc = metrics.spc_baseline;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Manufacturing Quality Intelligence</h1>
        <p style={{ color: 'var(--text-muted)' }}>
          Correlating process parameters, incoming material and in-line inspection to catch quality
          escapes before cells reach pack assembly.
        </p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Defect Recall</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>
            {(early.recall * 100).toFixed(1)}%
          </div>
          <span className={styles.cardSub}>vs {(spc.recall * 100).toFixed(1)}% for SPC</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Precision</h3>
          <div className={styles.cardValue} style={{ color: 'var(--warning)' }}>
            {(early.precision * 100).toFixed(1)}%
          </div>
          <span className={styles.cardSub}>at {early.batches_flagged_pct}% of batches flagged</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>ROC-AUC</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>
            {early.roc_auc}
          </div>
          <span className={styles.cardSub}>{metrics.dataset.test_batches} held-out batches</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Extra Escapes Caught</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>
            +{metrics.comparison.additional_defects_caught}
          </div>
          <span className={styles.cardSub}>vs SPC, same batches</span>
        </div>
      </div>

      <div className={styles.provenance}>
        <strong>Synthetic data</strong> — no open cell-manufacturing defect corpus exists to train on.
        Figures are measured on {metrics.dataset.total_batches} generated batches
        ({metrics.dataset.defect_rate_pct}% defect rate, {metrics.dataset.validation}) with a known
        causal structure. The pipeline — feature construction, SPC baseline, held-out evaluation — is
        what transfers to real line data.
      </div>

      <div className={styles.tabBar}>
        {[
          ['detection', 'Detection vs SPC'],
          ['drift', `Process Drift (${drift.parameters_drifting})`],
          ['spc', 'Control Charts'],
          ['batches', 'Flagged Batches'],
          ['trace', 'Cell → Pack → Vehicle'],
        ].map(([k, label]) => (
          <button key={k} className={`${styles.tab} ${tab === k ? styles.tabActive : ''}`}
            onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>

      {tab === 'detection' && (
        <>
          <div className={`glass-card ${styles.panel}`}>
            <h2><Factory size={18} /> Detection Performance</h2>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Approach</th><th>Precision</th><th>Recall</th><th>F1</th>
                    <th>AUC</th><th>Flagged</th><th>Caught</th><th>Missed</th>
                  </tr>
                </thead>
                <tbody>
                  {[metrics.early_warning, metrics.full_model].map((m) => (
                    <tr key={m.name}>
                      <td>{m.name}</td>
                      <td className={styles.mono}>{m.precision}</td>
                      <td className={styles.mono} style={{ color: 'var(--success)' }}>{m.recall}</td>
                      <td className={styles.mono}>{m.f1}</td>
                      <td className={styles.mono}>{m.roc_auc}</td>
                      <td className={styles.mono}>{m.batches_flagged_pct}%</td>
                      <td className={styles.mono}>{m.confusion_matrix.true_positive}</td>
                      <td className={styles.mono}>{m.confusion_matrix.false_negative}</td>
                    </tr>
                  ))}
                  <tr className={styles.baselineRow}>
                    <td>{spc.name}</td>
                    <td className={styles.mono}>{spc.precision}</td>
                    <td className={styles.mono} style={{ color: 'var(--warning)' }}>{spc.recall}</td>
                    <td className={styles.mono}>{spc.f1}</td>
                    <td className={styles.mono}>—</td>
                    <td className={styles.mono}>{spc.batches_flagged_pct}%</td>
                    <td className={styles.mono}>{spc.confusion_matrix.true_positive}</td>
                    <td className={styles.mono}>{spc.confusion_matrix.false_negative}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className={styles.interpretation}>{metrics.comparison.interpretation}</p>
            <p className={styles.note}>Operating point: {early.operating_point}</p>
          </div>

          <div className={`glass-card ${styles.panel}`}>
            <h2><GitBranch size={18} /> Root Cause — what drives defects</h2>
            <div className={styles.barList}>
              {rootCause.features.slice(0, 8).map((f) => {
                const max = Math.abs(rootCause.features[0].coefficient) || 1;
                return (
                  <div key={f.feature} className={styles.barRow}>
                    <span className={styles.barLabel}>{f.feature}</span>
                    <div className={styles.barTrack}>
                      <div className={styles.barFill}
                        style={{
                          width: `${(Math.abs(f.coefficient) / max) * 100}%`,
                          backgroundColor: f.coefficient > 0 ? 'var(--danger)' : 'var(--success)',
                        }} />
                    </div>
                    <span className={styles.barValue}>{f.coefficient}</span>
                  </div>
                );
              })}
            </div>
            <p className={styles.note}>
              Standardised logistic coefficients. Positive values increase defect risk.
            </p>
          </div>

          <div className={`glass-card ${styles.panel}`}>
            <h2>Incoming Quality by Cell Supplier</h2>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr><th>Supplier</th><th>Batches</th><th>Defective</th><th>Defect rate</th>
                    <th>Mean purity</th><th>Mean moisture</th></tr>
                </thead>
                <tbody>
                  {suppliers.suppliers.map((s) => (
                    <tr key={s.supplier_id}>
                      <td>{s.supplier_name}</td>
                      <td className={styles.mono}>{s.batches}</td>
                      <td className={styles.mono}>{s.defective_batches}</td>
                      <td className={styles.mono} style={{
                        color: s.defect_rate_pct > 8 ? 'var(--danger)'
                          : s.defect_rate_pct > 5 ? 'var(--warning)' : 'var(--success)'
                      }}>{s.defect_rate_pct}%</td>
                      <td className={styles.mono}>{s.mean_purity_pct}%</td>
                      <td className={styles.mono}>{s.mean_moisture_ppm} ppm</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {tab === 'drift' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2><TrendingUp size={18} /> Process Drift — last {drift.window_batches} batches</h2>
          {drift.findings.length === 0 && (
            <p className={styles.note}>No parameter has drifted beyond 3 sigma from baseline.</p>
          )}
          {drift.findings.map((f) => (
            <div key={f.parameter} className={styles.driftCard} data-severity={f.severity}>
              <div className={styles.driftHead}>
                <strong>{f.parameter}</strong>
                <span className={styles.severityBadge} data-severity={f.severity}>{f.severity}</span>
                {f.still_in_spec && <span className={styles.inSpecBadge}>still in spec</span>}
              </div>
              <p>{f.message}</p>
              <div className={styles.driftStats}>
                <span>baseline {f.baseline_mean}</span>
                <span>→ recent {f.recent_mean}</span>
                <span className={styles.mono}>{f.shift_sigma}σ</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'spc' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2>SPC Control Limits & Capability</h2>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr><th>Parameter</th><th>Target</th><th>Mean</th><th>σ</th>
                  <th>LCL</th><th>UCL</th><th>Cpk</th><th>Capable</th><th>Out of spec</th></tr>
              </thead>
              <tbody>
                {charts.parameters.map((p) => (
                  <tr key={p.parameter}>
                    <td>{p.parameter}</td>
                    <td className={styles.mono}>{p.target}</td>
                    <td className={styles.mono}>{p.mean}</td>
                    <td className={styles.mono}>{p.sigma}</td>
                    <td className={styles.mono}>{p.lcl}</td>
                    <td className={styles.mono}>{p.ucl}</td>
                    <td className={styles.mono} style={{
                      color: p.capable ? 'var(--success)' : 'var(--danger)'
                    }}>{p.cpk}</td>
                    <td style={{ color: p.capable ? 'var(--success)' : 'var(--danger)' }}>
                      {p.capable ? 'yes' : 'no'}
                    </td>
                    <td className={styles.mono}>{p.out_of_spec_batches}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.note}>Automotive capability bar is Cpk ≥ 1.33.</p>
        </div>
      )}

      {tab === 'batches' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2><AlertTriangle size={18} /> Highest-Risk Batches</h2>
          <div className={styles.batchList}>
            {flagged.batches.map((b) => (
              <div key={b.batch_id} className={styles.batchCard} data-flagged={b.flagged}>
                <div className={styles.batchHead}>
                  <strong className={styles.mono}>{b.batch_id}</strong>
                  <span>{b.cell_line}</span>
                  <span className={styles.cardSub}>{b.supplier_name}</span>
                  <span className={styles.prob}>p={b.defect_probability}</span>
                  <span className={b.actual_defect ? styles.tpBadge : styles.fpBadge}>
                    {b.actual_defect ? 'defect confirmed' : 'no defect'}
                  </span>
                </div>
                <div className={styles.drivers}>
                  {b.top_drivers.map((d) => (
                    <span key={d.feature} className={styles.driverTag}>
                      {d.feature} = {d.value} ({d.contribution > 0 ? '+' : ''}{d.contribution})
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'trace' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2><GitBranch size={18} /> Traceability — {trace.flagged_links} of {trace.total_links} packs from flagged batches</h2>
          <p className={styles.note}>
            Click a row to open that vehicle&apos;s battery passport.
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr><th>Batch</th><th>Line</th><th>Supplier</th><th>BPAN</th>
                  <th>Vehicle</th><th>SoH</th><th>Status</th></tr>
              </thead>
              <tbody>
                {trace.links.map((l) => (
                  <tr key={l.bpan} className={styles.clickableRow}
                    onClick={() => setSelected(l.vehicle_id)}>
                    <td className={styles.mono}>{l.batch_id}</td>
                    <td>{l.cell_line}</td>
                    <td>{l.supplier_name}</td>
                    <td className={styles.mono}>{l.bpan}</td>
                    <td className={styles.mono}>{l.vehicle_id}</td>
                    <td className={styles.mono}>{l.soh_pct}%</td>
                    <td style={{ color: l.batch_flagged ? 'var(--danger)' : 'var(--success)' }}>
                      {l.batch_flagged ? 'from flagged batch' : 'clear'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selected && <VehicleDetail vehicleId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
