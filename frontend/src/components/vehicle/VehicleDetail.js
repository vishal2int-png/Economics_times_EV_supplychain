'use client';

import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { X, Battery, ShieldCheck, ShieldAlert, Recycle } from 'lucide-react';
import { api } from '../../lib/api';
import styles from './VehicleDetail.module.css';

/**
 * Slide-over detail for a single EV: measured-vs-forecast degradation curve
 * out to end of life, plus its battery passport and safety posture.
 */
export default function VehicleDetail({ vehicleId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!vehicleId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const [forecast, passport, battery] = await Promise.all([
          api.getForecast(vehicleId),
          api.getBpanPassport(vehicleId),
          api.getVehicleBattery(vehicleId),
        ]);
        if (!cancelled) setData({ forecast, passport, battery });
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load vehicle detail');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [vehicleId]);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!vehicleId) return null;

  // Stitch observed and forecast onto one continuous axis.
  let chartData = [];
  if (data) {
    const { observed, forecast } = data.forecast;
    chartData = [
      ...observed.map((o) => ({
        x: o.month_index, observed: o.soh, fitted: o.fitted,
      })),
      ...forecast.map((f) => ({ x: f.month_index, forecast: f.soh })),
    ];
  }

  const safety = data?.passport?.dynamic?.safety;

  return (
    <>
      <div className={styles.backdrop} onClick={onClose} />
      <aside className={styles.panel} role="dialog" aria-label={`Detail for ${vehicleId}`}>
        <div className={styles.header}>
          <div>
            <h2>{vehicleId}</h2>
            {data && (
              <p className={styles.subtitle}>
                {data.battery.model} · {data.battery.city} · {data.battery.route_name}
              </p>
            )}
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {loading && <div className="animate-pulse" style={{ padding: 24 }}>Loading vehicle detail…</div>}
        {error && <div className={styles.error}>{error}</div>}

        {data && (
          <div className={styles.body}>
            {/* ── Headline stats ─────────────────────────────────────── */}
            <div className={styles.statRow}>
              <div className={styles.stat}>
                <span className={styles.statLabel}>State of Health</span>
                <span className={styles.statValue}>{data.battery.battery.soh_pct}%</span>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Forecast RUL</span>
                <span className={styles.statValue}>
                  {data.forecast.forecast_rul_months ?? '—'}
                  <small> mo</small>
                </span>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Cycles</span>
                <span className={styles.statValue}>{data.battery.battery.cycle_count}</span>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Pack Temp</span>
                <span className={styles.statValue}>
                  {data.battery.battery.temperature_c}<small>°C</small>
                </span>
              </div>
            </div>

            {/* ── Degradation curve ──────────────────────────────────── */}
            <section className={styles.section}>
              <h3><Battery size={16} /> Degradation — measured vs forecast to EOL</h3>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="x" stroke="#94a3b8" tick={{ fontSize: 11 }}
                      label={{ value: 'month', position: 'insideBottomRight', fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis domain={[60, 100]} stroke="#94a3b8" tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#334155' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <ReferenceLine y={data.forecast.eol_threshold} stroke="#ef4444"
                      strokeDasharray="4 4"
                      label={{ value: `EOL ${data.forecast.eol_threshold}%`, fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }} />
                    <Line type="monotone" dataKey="observed" name="Measured" stroke="#3b82f6"
                      strokeWidth={2} dot={false} connectNulls={false} />
                    <Line type="monotone" dataKey="fitted" name="Model fit" stroke="#22c55e"
                      strokeWidth={1.5} strokeDasharray="3 3" dot={false} connectNulls={false} />
                    <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#f59e0b"
                      strokeWidth={2} strokeDasharray="6 3" dot={false} connectNulls={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className={styles.note}>
                Fit: a·√t = {data.forecast.coefficients.a_calendar_sei} (SEI calendar),
                b·t = {data.forecast.coefficients.b_cycling} (cycling)
                {data.forecast.weighting_selected
                  ? ` · recency weighting 1/${data.forecast.weighting_selected} selected`
                  : ' · unweighted fit selected'}
              </p>
            </section>

            {/* ── Battery passport ───────────────────────────────────── */}
            <section className={styles.section}>
              <h3><Recycle size={16} /> Battery Pack Aadhaar</h3>
              <div className={styles.bpanCode}>{data.passport.bpan}</div>
              <div className={styles.kvGrid}>
                <div><span>Chemistry</span><strong>{data.passport.static.bds.chemistry_full}</strong></div>
                <div><span>Capacity</span><strong>{data.passport.static.bds.nominal_capacity_kwh} kWh</strong></div>
                <div><span>Manufacturer</span><strong>{data.passport.static.bmi.manufacturer}</strong></div>
                <div><span>Made</span><strong>{data.passport.static.bmi.manufacture_date}</strong></div>
                <div><span>Cobalt-free</span><strong>{data.passport.static.bmcs.cobalt_free ? 'Yes' : 'No'}</strong></div>
                <div><span>Embedded CO₂e</span><strong>{data.passport.static.bcf.embedded_kg_co2e} kg</strong></div>
              </div>
              <div className={styles.lifecycle} data-status={data.passport.dynamic.lifecycle_status}>
                <strong>{data.passport.dynamic.lifecycle_status.replace(/_/g, ' ')}</strong>
                <p>{data.passport.dynamic.lifecycle_detail}</p>
              </div>
            </section>

            {/* ── Safety ─────────────────────────────────────────────── */}
            <section className={styles.section}>
              <h3>
                {safety.compliant ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />}
                {' '}AIS-156 Phase 2
              </h3>
              <div className={styles.safetyRow} data-ok={safety.compliant}>
                {safety.compliant ? 'Compliant' : `${safety.findings.length} finding(s)`}
                <span className={styles.safetyMeta}>
                  {safety.temperature_sensors} sensors · {safety.thermal_events_total} thermal events
                  ({safety.thermal_events_severe} severe)
                </span>
              </div>
              {safety.findings.length > 0 && (
                <ul className={styles.findings}>
                  {safety.findings.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              )}
            </section>
          </div>
        )}
      </aside>
    </>
  );
}
