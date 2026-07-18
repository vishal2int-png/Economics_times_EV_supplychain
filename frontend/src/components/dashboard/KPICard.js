import styles from './Dashboard.module.css';

export default function KPICard({ title, value, subtitle, icon: Icon, trend }) {
  return (
    <div className={`glass-card ${styles.kpiCard}`}>
      <div className={styles.kpiHeader}>
        <span className={styles.kpiTitle}>{title}</span>
        {Icon && <Icon size={20} className={styles.kpiIcon} />}
      </div>
      <div className={styles.kpiBody}>
        <span className={styles.kpiValue}>{value}</span>
        {trend && (
          <span className={`${styles.kpiTrend} ${trend > 0 ? styles.trendUp : styles.trendDown}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      {subtitle && <div className={styles.kpiSubtitle}>{subtitle}</div>}
    </div>
  );
}
