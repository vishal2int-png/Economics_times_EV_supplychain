'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Zap, Truck, ShieldAlert, Leaf, Bot } from 'lucide-react';
import styles from './Layout.module.css';

const navItems = [
  { name: 'Command Center', path: '/', icon: Activity },
  { name: 'Agent Console', path: '/agent-console', icon: Bot },
  { name: 'Battery APM', path: '/battery-apm', icon: Zap },
  { name: 'Fleet Readiness', path: '/fleet-readiness', icon: Truck },
  { name: 'Supply Chain Risk', path: '/supply-chain', icon: ShieldAlert },
  { name: 'Net Zero Tracker', path: '/net-zero', icon: Leaf },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <div className={styles.logoContainer}>
          <Zap className={styles.logoIcon} />
          <h2>VoltEdge AI</h2>
        </div>
      </div>
      <nav className={styles.nav}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link key={item.name} href={item.path} className={`${styles.navItem} ${isActive ? styles.active : ''}`}>
              <Icon size={20} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
