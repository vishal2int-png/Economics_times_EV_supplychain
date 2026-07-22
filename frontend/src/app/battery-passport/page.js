'use client';

import { useEffect, useState } from 'react';
import { Search, ShieldCheck, ShieldAlert, Recycle, QrCode } from 'lucide-react';
import { api } from '../../lib/api';
import VehicleDetail from '../../components/vehicle/VehicleDetail';
import styles from './Passport.module.css';

export default function BatteryPassport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [lookup, setLookup] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [tab, setTab] = useState('registry');

  useEffect(() => {
    async function load() {
      try {
        const [registry, compliance, secondLife] = await Promise.all([
          api.getBpanRegistry(),
          api.getBpanCompliance(),
          api.getSecondLife(),
        ]);
        setData({ registry, compliance, secondLife });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function runLookup() {
    const code = lookup.trim();
    if (!code) return;
    setLookupResult({ status: 'searching' });
    try {
      const res = await api.getBpanPassport(code);
      setLookupResult({ status: 'found', passport: res });
    } catch {
      setLookupResult({ status: 'not_found', code });
    }
  }

  if (loading) {
    return <div className="flex-center" style={{ height: '100%' }}>
      <div className="animate-pulse">Loading Battery Passports…</div>
    </div>;
  }
  if (error) return <div style={{ color: 'var(--danger)' }}>Error: {error}</div>;

  const { registry, compliance, secondLife } = data;
  const s = registry.summary;

  return (
    <div className={styles.container}>
      <header>
        <h1 className="text-gradient">Battery Pack Aadhaar — Lifecycle Traceability</h1>
        <p style={{ color: 'var(--text-muted)' }}>
          A 21-character identity per pack, with immutable manufacturing facts and a living
          operational ledger. Built for compliance-readiness against MoRTH&apos;s draft BPAN scheme.
        </p>
      </header>

      <div className={styles.summaryCards}>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Packs Traced</h3>
          <div className={styles.cardValue} style={{ color: 'var(--primary)' }}>
            {s.total_packs}
          </div>
          <span className={styles.cardSub}>{s.traceability_coverage_pct}% coverage</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>AIS-156 Flagged</h3>
          <div className={styles.cardValue} style={{ color: s.ais156_flagged ? 'var(--warning)' : 'var(--success)' }}>
            {s.ais156_flagged}
          </div>
          <span className={styles.cardSub}>{s.ais156_compliant} compliant</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Cobalt Exposure</h3>
          <div className={styles.cardValue} style={{ color: 'var(--warning)' }}>
            {s.cobalt_exposure_pct}%
          </div>
          <span className={styles.cardSub}>{s.cobalt_exposed_packs} NMC packs</span>
        </div>
        <div className={`glass-card ${styles.card}`}>
          <h3 className={styles.cardTitle}>Embedded Carbon</h3>
          <div className={styles.cardValue} style={{ color: 'var(--text)' }}>
            {s.embedded_carbon_tons}
          </div>
          <span className={styles.cardSub}>t CO₂e, cradle-to-gate</span>
        </div>
      </div>

      {/* ── Passport lookup ─────────────────────────────────────────── */}
      <div className={`glass-card ${styles.lookupPanel}`}>
        <h2><QrCode size={18} /> Passport Lookup</h2>
        <p className={styles.panelSub}>
          Scan a pack&apos;s QR code or enter its 21-character BPAN — or just a vehicle id.
        </p>
        <div className={styles.lookupRow}>
          <input
            className={styles.lookupInput}
            value={lookup}
            onChange={(e) => setLookup(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runLookup()}
            placeholder="e.g. EV-001 or INTAMLLF021325Y07ZF9P"
          />
          <button className={styles.lookupButton} onClick={runLookup} disabled={!lookup.trim()}>
            <Search size={16} /> Look up
          </button>
        </div>

        {lookupResult?.status === 'not_found' && (
          <div className={styles.notFound}>
            No pack registered under &ldquo;{lookupResult.code}&rdquo;.
          </div>
        )}
        {lookupResult?.status === 'found' && (
          <div className={styles.lookupHit}>
            <div>
              <div className={styles.bpanCode}>{lookupResult.passport.bpan}</div>
              <span className={styles.cardSub}>
                {lookupResult.passport.vehicle_id} · {lookupResult.passport.static.bds.chemistry_full}
                {' · '}SoH {lookupResult.passport.dynamic.soh_pct}%
                {' · checksum '}
                {lookupResult.passport.bpan_valid ? 'valid' : 'INVALID'}
              </span>
            </div>
            <button className={styles.openButton}
              onClick={() => setSelected(lookupResult.passport.vehicle_id)}>
              Open full passport
            </button>
          </div>
        )}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────── */}
      <div className={styles.tabBar}>
        {[
          ['registry', `Registry (${registry.packs.length})`],
          ['compliance', `AIS-156 (${compliance.flagged} flagged)`],
          ['secondlife', `Second Life (${secondLife.total_candidates})`],
        ].map(([key, label]) => (
          <button key={key}
            className={`${styles.tab} ${tab === key ? styles.tabActive : ''}`}
            onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'registry' && (
        <div className={`glass-card ${styles.panel}`}>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>BPAN</th><th>Vehicle</th><th>Chemistry</th><th>Capacity</th>
                  <th>Manufacturer</th><th>SoH</th><th>Lifecycle</th><th>AIS-156</th>
                </tr>
              </thead>
              <tbody>
                {registry.packs.map((p) => (
                  <tr key={p.bpan} className={styles.clickableRow}
                    onClick={() => setSelected(p.vehicle_id)}>
                    <td className={styles.mono}>{p.bpan}</td>
                    <td className={styles.mono}>{p.vehicle_id}</td>
                    <td>{p.chemistry}</td>
                    <td className={styles.mono}>{p.capacity_kwh} kWh</td>
                    <td>{p.manufacturer}</td>
                    <td className={styles.mono} style={{
                      color: p.soh_pct < 75 ? 'var(--danger)'
                        : p.soh_pct < 85 ? 'var(--warning)' : 'var(--success)'
                    }}>{p.soh_pct}%</td>
                    <td>{p.lifecycle_status.replace(/_/g, ' ')}</td>
                    <td style={{ color: p.ais156_compliant ? 'var(--success)' : 'var(--warning)' }}>
                      {p.ais156_compliant ? 'ok' : 'flagged'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'compliance' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2>
            {compliance.flagged ? <ShieldAlert size={18} /> : <ShieldCheck size={18} />}
            {' '}{compliance.standard} — {compliance.compliant} of {compliance.total_packs} compliant
          </h2>
          {compliance.flagged_packs.length === 0 && (
            <p className={styles.panelSub}>No open safety findings across the fleet.</p>
          )}
          {compliance.flagged_packs.map((p) => (
            <div key={p.bpan} className={styles.flagCard}
              onClick={() => setSelected(p.vehicle_id)}>
              <div className={styles.flagHead}>
                <strong className={styles.mono}>{p.vehicle_id}</strong>
                <span className={styles.mono}>{p.bpan}</span>
                <span className={styles.cardSub}>
                  SoH {p.soh_pct}% · {p.thermal_events_severe} severe thermal events
                </span>
              </div>
              <ul>{p.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
          ))}
        </div>
      )}

      {tab === 'secondlife' && (
        <div className={`glass-card ${styles.panel}`}>
          <h2><Recycle size={18} /> Second-Life Inventory</h2>
          <p className={styles.panelSub}>
            {secondLife.total_candidates} packs past traction duty ·{' '}
            {secondLife.total_usable_kwh} kWh usable · ₹
            {Number(secondLife.total_residual_value_inr).toLocaleString('en-IN')} residual value
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>BPAN</th><th>Vehicle</th><th>Chemistry</th><th>SoH</th>
                  <th>Usable</th><th>Residual</th><th>Recommended application</th>
                </tr>
              </thead>
              <tbody>
                {secondLife.candidates.map((c) => (
                  <tr key={c.bpan} className={styles.clickableRow}
                    onClick={() => setSelected(c.vehicle_id)}>
                    <td className={styles.mono}>{c.bpan}</td>
                    <td className={styles.mono}>{c.vehicle_id}</td>
                    <td>{c.chemistry}</td>
                    <td className={styles.mono}>{c.soh_pct}%</td>
                    <td className={styles.mono}>{c.usable_kwh} kWh</td>
                    <td className={styles.mono}>
                      ₹{Number(c.residual_value_inr).toLocaleString('en-IN')}
                    </td>
                    <td>{c.recommended_application}</td>
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
