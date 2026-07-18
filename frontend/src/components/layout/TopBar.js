import { Bell, Search, User } from 'lucide-react';
import styles from './Layout.module.css';

export default function TopBar() {
  return (
    <header className={styles.topbar}>
      <div className={styles.searchContainer}>
        <Search size={18} className={styles.searchIcon} />
        <input type="text" placeholder="Search fleet, suppliers, alerts..." className={styles.searchInput} />
      </div>
      <div className={styles.actions}>
        <button className={styles.iconButton}>
          <Bell size={20} />
          <span className={styles.badge}>3</span>
        </button>
        <div className={styles.userProfile}>
          <div className={styles.avatar}>
            <User size={18} />
          </div>
          <span>Fleet Admin</span>
        </div>
      </div>
    </header>
  );
}
