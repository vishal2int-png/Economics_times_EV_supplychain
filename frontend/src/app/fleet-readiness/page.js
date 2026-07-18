'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import styles from './Fleet.module.css';

export default function FleetReadiness() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const scores = await api.getReadinessScores();
        setData(scores);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="flex-center" style={{ height: '100%' }}><div className="animate-pulse">Loading Fleet Readiness...</div></div>;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Fleet Electrification Readiness</h1>
        <p style={{ color: 'var(--text-muted)' }}>AI-driven analysis to identify the best candidates for EV replacement.</p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Ready Now (ERI {">"} 80)</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>{data.summary.ready_now}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Total Potential Savings</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>₹{data.summary.total_potential_savings_lakh}L</div>
        </div>
      </div>

      <div className={`glass-card ${styles.tablePanel}`}>
        <h2>Vehicle Readiness Index (ERI)</h2>
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Vehicle ID</th>
                <th>City & Route</th>
                <th>Current Diesel</th>
                <th>ERI Score</th>
                <th>Recommended EV</th>
                <th>TCO Savings /yr</th>
              </tr>
            </thead>
            <tbody>
              {data.vehicles.map((v) => (
                <tr key={v.id}>
                  <td style={{ fontWeight: 600 }}>{v.id}</td>
                  <td>{v.city} <br/><span className={styles.textSmall}>{v.route_name}</span></td>
                  <td>{v.model}</td>
                  <td>
                    <div className={styles.scoreContainer}>
                      <span className={`${styles.grade} ${styles['grade' + v.eri_grade]}`}>{v.eri_grade}</span>
                      <span>{v.eri_score}</span>
                    </div>
                  </td>
                  <td>{v.recommended_ev}</td>
                  <td style={{ color: 'var(--success)' }}>₹{v.tco_savings_lakh}L</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
