'use client';

import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import KPICard from '../components/dashboard/KPICard';
import { Zap, Truck, ShieldAlert, Leaf } from 'lucide-react';
import styles from './page.module.css';

export default function Home() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const dashboardData = await api.getDashboard();
        setData(dashboardData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (loading) return <div className="flex-center" style={{ height: '100%' }}><div className="animate-pulse">Loading Command Center...</div></div>;
  if (error) return <div className="flex-center" style={{ color: 'var(--danger)' }}>Error: {error}</div>;

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <h1 className="text-gradient">VoltEdge Command Center</h1>
        <p className={styles.subtitle}>Fleet Operations & Supply Chain Intelligence</p>
      </header>

      <div className={styles.kpiGrid}>
        <KPICard 
          title="Battery APM (Avg SoH)" 
          value={`${data.battery_apm.avg_soh}%`} 
          subtitle={`${data.battery_apm.critical_count} critical vehicles`}
          icon={Zap}
        />
        <KPICard 
          title="Fleet Readiness (Avg ERI)" 
          value={data.fleet_readiness.avg_eri} 
          subtitle={`${data.fleet_readiness.ready_for_ev} ready for EV transition`}
          icon={Truck}
        />
        <KPICard 
          title="Supply Chain Risks" 
          value={data.supply_chain.critical_risks + data.supply_chain.high_risks} 
          subtitle={`${data.supply_chain.china_dependency_pct}% China dependency`}
          icon={ShieldAlert}
          trend={-12}
        />
        <KPICard 
          title="Net Zero Progress" 
          value={`${data.net_zero.electrification_pct}%`} 
          subtitle={`${data.net_zero.carbon_savings_tons} tons CO₂ saved`}
          icon={Leaf}
          trend={4.5}
        />
      </div>

      <div className={styles.contentGrid}>
        <div className={`glass-card ${styles.mainPanel}`}>
          <h2>Fleet Overview</h2>
          <div className={styles.fleetStats}>
            <div className={styles.statBox}>
              <span className={styles.statValue}>{data.fleet_overview.total_vehicles}</span>
              <span className={styles.statLabel}>Total Vehicles</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statValue}>{data.fleet_overview.ev_count}</span>
              <span className={styles.statLabel}>EVs Active</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statValue}>{data.fleet_overview.diesel_count}</span>
              <span className={styles.statLabel}>Diesel Fleet</span>
            </div>
          </div>
          <div className={styles.placeholderChart}>
            <p style={{ color: 'var(--text-muted)' }}>Select a module from the sidebar for detailed analytics.</p>
          </div>
        </div>
        
        <div className={`glass-card ${styles.sidePanel}`}>
          <h2>Active Alerts</h2>
          <div className={styles.alertList}>
            {data.supply_chain.active_alerts > 0 && (
              <div className={styles.alertItem}>
                <ShieldAlert size={16} style={{ color: 'var(--danger)' }} />
                <span>{data.supply_chain.active_alerts} Supply Chain Alerts</span>
              </div>
            )}
            {data.battery_apm.critical_count > 0 && (
              <div className={styles.alertItem}>
                <Zap size={16} style={{ color: 'var(--danger)' }} />
                <span>{data.battery_apm.critical_count} Battery Health Warnings</span>
              </div>
            )}
            <div className={styles.alertItem}>
              <Truck size={16} style={{ color: 'var(--warning)' }} />
              <span>3 EVs due for maintenance</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
