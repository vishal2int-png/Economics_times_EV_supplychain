'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import styles from './Carbon.module.css';

export default function NetZeroTracker() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [summary, emissions, nextBestAction] = await Promise.all([
          api.getCarbonSummary(),
          api.getEmissions(),
          api.getNextBestAction()
        ]);
        setData({ summary, emissions, nextBestAction });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="flex-center" style={{ height: '100%' }}><div className="animate-pulse">Loading Carbon Data...</div></div>;

  // Merge monthly and counterfactual data for the chart
  const mergedData = data.emissions.monthly.map((m, i) => ({
    month: m.month,
    actual: m.total_kg,
    counterfactual: data.emissions.counterfactual[i].total_kg
  }));

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Net Zero & Carbon Intelligence</h1>
        <p style={{ color: 'var(--text-muted)' }}>Track emissions and discover the most impactful electrification actions.</p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Annual Emissions</h3>
          <div className={styles.cardValue} style={{ color: 'var(--warning)' }}>{data.summary.total_annual_emissions_tons} <span style={{fontSize: '16px'}}>Tons</span></div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Carbon Saved (vs all-diesel)</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>{data.summary.carbon_savings_tons} <span style={{fontSize: '16px'}}>Tons</span></div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Electrification Progress</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>{data.summary.electrification_pct}%</div>
        </div>
      </div>

      <div className={styles.mainGrid}>
        <div className={`glass-card ${styles.chartPanel}`}>
          <h2>Monthly Fleet Emissions vs Counterfactual</h2>
          <div style={{ width: '100%', height: '320px', marginTop: '16px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mergedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCounter" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="month" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#334155' }} />
                <Area type="monotone" dataKey="counterfactual" stroke="#f59e0b" fillOpacity={1} fill="url(#colorCounter)" name="If 100% Diesel (kg)" />
                <Area type="monotone" dataKey="actual" stroke="#3b82f6" fillOpacity={1} fill="url(#colorActual)" name="Actual Emissions (kg)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={`glass-card ${styles.actionsPanel}`}>
          <h2>Next Best Actions (AI Priority)</h2>
          <div className={styles.actionList}>
            {data.nextBestAction.actions.slice(0, 4).map((action, idx) => (
              <div key={idx} className={styles.actionCard}>
                <div className={styles.actionHeader}>
                  <div className={styles.actionRank}>#{action.rank}</div>
                  <span style={{ fontWeight: '600' }}>{action.vehicle_id}</span>
                </div>
                <p className={styles.actionDesc}>Electrify route: {action.route_name}</p>
                <div className={styles.actionImpact}>
                  <span className={styles.impactValue}>{action.estimated_annual_co2_saved_tons} Tons CO₂/yr saved</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
