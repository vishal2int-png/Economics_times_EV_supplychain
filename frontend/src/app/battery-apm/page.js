'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import VehicleDetail from '../../components/vehicle/VehicleDetail';
import styles from './Battery.module.css';

export default function BatteryAPM() {
  const [healthData, setHealthData] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [realValidation, setRealValidation] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [health, alertData, accuracyData, realData] = await Promise.all([
          api.getFleetHealth(),
          api.getBatteryAlerts(),
          api.getDegradationAccuracy(),
          api.getRealValidation()
        ]);
        setHealthData(health);
        setAlerts(alertData);
        setAccuracy(accuracyData);
        setRealValidation(realData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="flex-center" style={{ height: '100%' }}><div className="animate-pulse">Loading Battery Data...</div></div>;
  if (error) return <div style={{ color: 'var(--danger)' }}>Error: {error}</div>;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Battery Asset Performance Management</h1>
        <p style={{ color: 'var(--text-muted)' }}>Predictive health monitoring and degradation tracking for your EV fleet.</p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Fleet Average SoH</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>{healthData.summary.avg_soh}%</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Critical Vehicles</h3>
          <div className={styles.cardValue} style={{ color: 'var(--danger)' }}>{healthData.summary.critical_count}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Healthy Vehicles</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>{healthData.summary.healthy_count}</div>
        </div>
      </div>

      {realValidation && realValidation.summary.evaluated_cells > 0 && (
        <div className={`glass-card ${styles.accuracyPanel}`}>
          <h2>
            Degradation Model — Validated on Real Cells
            <span className={styles.realBadge}>REAL DATA</span>
          </h2>
          <p className={styles.accuracySub}>
            {realValidation.summary.model}
            <br />
            {realValidation.summary.dataset} &nbsp;·&nbsp;{' '}
            {realValidation.summary.evaluated_cells} cells,{' '}
            {realValidation.summary.total_cycles} measured cycles &nbsp;·&nbsp;{' '}
            {realValidation.summary.validation}
          </p>

          <div className={styles.accuracyGrid}>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Model RMSE</span>
              <span className={styles.metricValue} style={{ color: 'var(--success)' }}>
                {realValidation.summary.model_rmse_pct_soh}
              </span>
              <span className={styles.metricUnit}>% SoH</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Baseline RMSE</span>
              <span className={styles.metricValue} style={{ color: 'var(--text-muted)' }}>
                {realValidation.summary.baseline_rmse_pct_soh}
              </span>
              <span className={styles.metricUnit}>% SoH (persistence)</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Improvement</span>
              <span className={styles.metricValue} style={{ color: 'var(--primary)' }}>
                {realValidation.summary.rmse_improvement_pct}%
              </span>
              <span className={styles.metricUnit}>vs baseline</span>
            </div>
            <div className={styles.metric}>
              <span className={styles.metricLabel}>RUL Error</span>
              <span className={styles.metricValue} style={{ color: 'var(--primary)' }}>
                {realValidation.summary.rul_mean_abs_error_cycles}
              </span>
              <span className={styles.metricUnit}>
                cycles ({realValidation.summary.rul_mean_error_pct_of_cell_life}% of cell life)
              </span>
            </div>
          </div>

          <table className={styles.cellTable}>
            <thead>
              <tr>
                <th>Cell</th>
                <th>Cycles</th>
                <th>Measured fade</th>
                <th>Model RMSE</th>
                <th>Baseline</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {realValidation.per_cell.map((c) => {
                const meta = realValidation.cells?.find((m) => m.cell === c.cell);
                const wins = c.model_rmse < c.baseline_rmse;
                return (
                  <tr key={c.cell}>
                    <td className={styles.mono}>{c.cell}</td>
                    <td>{c.cycles}</td>
                    <td>{meta ? `${meta.total_fade_pct}%` : '—'}</td>
                    <td className={styles.mono}>{c.model_rmse}</td>
                    <td className={styles.mono}>{c.baseline_rmse}</td>
                    <td style={{ color: wins ? 'var(--success)' : 'var(--warning)' }}>
                      {wins ? `beats baseline (${c.rmse_improvement_pct}%)` : 'misses baseline'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {accuracy && accuracy.summary.evaluated_vehicles > 0 && (
            <p className={styles.syntheticNote}>
              For reference, the same model scores {accuracy.summary.model_rmse_pct_soh} % SoH RMSE
              ({accuracy.summary.rmse_improvement_pct}% over baseline) on the simulated fleet — higher,
              because that data is generated by a process the model structurally matches. The real-cell
              figures above are the honest measure.
            </p>
          )}
        </div>
      )}

      <div className={styles.mainGrid}>
        <div className={`glass-card ${styles.chartPanel}`}>
          <h2>Fleet SoH Distribution</h2>
          <div style={{ width: '100%', height: '320px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={healthData.vehicles.map(v => ({ name: v.id, soh: v.soh_pct }))} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{fontSize: 12}} />
                <YAxis domain={[60, 100]} stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#334155' }} />
                <Line type="monotone" dataKey="soh" stroke="#3b82f6" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={`glass-card ${styles.alertsPanel}`}>
          <h2>Active Alerts</h2>
          <div className={styles.alertList}>
            {alerts.alerts.map((alert, idx) => (
              <div
                key={idx}
                className={styles.alertCard}
                data-severity={alert.severity}
                onClick={() => setSelected(alert.vehicle_id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelected(alert.vehicle_id)}
                title={`Open ${alert.vehicle_id}`}
              >
                <div className={styles.alertHeader}>
                  <span>{alert.vehicle_id}</span>
                  <span className={styles.alertBadge}>{alert.severity}</span>
                </div>
                <p className={styles.alertMessage}>{alert.message}</p>
                <div className={styles.alertAction}>Recommended: {alert.recommended_action}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={`glass-card ${styles.fleetPanel}`}>
        <h2>EV Fleet — click any vehicle for its degradation forecast and passport</h2>
        <div className={styles.tableWrap}>
          <table className={styles.fleetTable}>
            <thead>
              <tr>
                <th>Vehicle</th>
                <th>Model</th>
                <th>City</th>
                <th>SoH</th>
                <th>RUL</th>
                <th>Cycles</th>
                <th>Temp</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {healthData.vehicles.map((v) => (
                <tr
                  key={v.id}
                  onClick={() => setSelected(v.id)}
                  className={styles.clickableRow}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setSelected(v.id)}
                >
                  <td className={styles.mono}>{v.id}</td>
                  <td>{v.model}</td>
                  <td>{v.city}</td>
                  <td className={styles.mono} style={{
                    color: v.soh_pct < 75 ? 'var(--danger)'
                      : v.soh_pct < 85 ? 'var(--warning)' : 'var(--success)'
                  }}>{v.soh_pct}%</td>
                  <td className={styles.mono}>{v.predicted_rul_months} mo</td>
                  <td className={styles.mono}>{v.cycle_count}</td>
                  <td className={styles.mono}>{v.temperature_c}°C</td>
                  <td>{v.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <VehicleDetail vehicleId={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
