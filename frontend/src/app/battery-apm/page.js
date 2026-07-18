'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import styles from './Battery.module.css';

export default function BatteryAPM() {
  const [healthData, setHealthData] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [health, alertData] = await Promise.all([
          api.getFleetHealth(),
          api.getBatteryAlerts()
        ]);
        setHealthData(health);
        setAlerts(alertData);
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
              <div key={idx} className={styles.alertCard} data-severity={alert.severity}>
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
    </div>
  );
}
