'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import styles from './SupplyChain.module.css';

export default function SupplyChainRisk() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const overview = await api.getSupplyChainOverview();
        setData(overview);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="flex-center" style={{ height: '100%' }}><div className="animate-pulse">Loading Supply Chain Data...</div></div>;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Supply Chain Risk Intelligence</h1>
        <p style={{ color: 'var(--text-muted)' }}>Multi-tier traceability and disruption risk alerts for battery materials.</p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Total Suppliers</h3>
          <div className={styles.cardValue}>{data.summary.total_suppliers}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Critical Risk Nodes</h3>
          <div className={styles.cardValue} style={{ color: 'var(--danger)' }}>{data.summary.critical_risks}</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>China Dependency</h3>
          <div className={styles.cardValue} style={{ color: 'var(--warning)' }}>{data.summary.china_dependency_pct}%</div>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>India Localization</h3>
          <div className={styles.cardValue} style={{ color: 'var(--success)' }}>{data.summary.india_localization_pct}%</div>
        </div>
      </div>

      <div className={`glass-card ${styles.mapPanel}`}>
        <h2>Supply Chain Nodes Tracker</h2>
        <div className={styles.placeholderMap}>
          <div className={styles.nodesList}>
             <div className={styles.tier}>
               <h4>Tier 1: Cells</h4>
               <span className={styles.nodeCount}>{data.tier_breakdown.tier_1_cells} Suppliers</span>
             </div>
             <div className={styles.tier}>
               <h4>Tier 2: Cathode/Anode</h4>
               <span className={styles.nodeCount}>{data.tier_breakdown.tier_2_components} Suppliers</span>
             </div>
             <div className={styles.tier}>
               <h4>Tier 3: Refining</h4>
               <span className={styles.nodeCount}>{data.tier_breakdown.tier_3_refining} Suppliers</span>
             </div>
             <div className={styles.tier}>
               <h4>Tier 4: Mining</h4>
               <span className={styles.nodeCount}>{data.tier_breakdown.tier_4_mining} Suppliers</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
