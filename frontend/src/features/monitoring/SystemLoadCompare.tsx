import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, BarChart3, Check, RotateCcw, Settings2 } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, isoWita, months, num, qs, type Catalog, type Metric, type User } from '../../api';
import './monitoring.css';

type WindowType = 'hour' | 'day' | 'month' | 'year';
type ComparisonRow = {
  period: string; load_kw: number | null; capacity_kw: number | null;
  paired_load_kw: number | null; load_hours: number; paired_hours: number;
};
type ComparisonResponse = { data: ComparisonRow[] };
type AnalyticsResponse = { data: { period: string; avg: number }[] };
type ChartSettings = {
  system: string[]; personal: string[] | null; effective: string[];
  source: 'system' | 'personal'; max_series: number;
};
type ChartRow = { period: string; label: string; [key: string]: string | number | null };

const COLORS = ['#1e8b69', '#eb7b40', '#2f74b5', '#9b60b1'];

const errorText = (error: unknown) => error instanceof Error ? error.message : String(error);

function timeRange(window: WindowType, day: string, year: number, month: number) {
  if (window === 'hour') return { start: day, end: day, granularity: 'hour' };
  if (window === 'day') return {
    start: `${year}-${String(month).padStart(2, '0')}-01`,
    end: `${year}-${String(month).padStart(2, '0')}-${new Date(year, month, 0).getDate()}`,
    granularity: 'day',
  };
  if (window === 'month') return { start: `${year}-01-01`, end: `${year}-12-31`, granularity: 'month' };
  return { start: `${Math.max(2020, year - 9)}-01-01`, end: `${year}-12-31`, granularity: 'year' };
}

function labelFor(period: string, window: WindowType) {
  if (window === 'hour') return period.slice(-5);
  if (window === 'day') return period.slice(-2);
  if (window === 'month') return months[Number(period.slice(5)) - 1]?.slice(0, 3) || period;
  return period;
}

async function loadChart(
  codes: string[], parameters: ReturnType<typeof timeRange>, window: WindowType, CAPACITY: string, LOAD: string,
): Promise<{ rows: ChartRow[]; paired: number; loadHours: number }> {
  const isSystemMetric = (code: string) => Boolean(CAPACITY&&LOAD&&(code === CAPACITY || code === LOAD));
  const needsPair = codes.some(isSystemMetric);
  const other = codes.filter(code => !isSystemMetric(code));
  const [comparison, analytic] = await Promise.all([
    needsPair ? api<ComparisonResponse>(`/monitoring/capacity-vs-load?${qs(parameters)}`) : Promise.resolve(null),
    Promise.all(other.map(code => api<AnalyticsResponse>(`/analytics?${qs({ ...parameters, metric: code })}`))),
  ]);
  const points = new Map<string, Record<string, number | null>>();
  let paired = 0;
  let loadHours = 0;
  for (const item of comparison?.data || []) {
    const row: Record<string, number | null> = points.get(item.period) || {};
    const alignedLoad = item.capacity_kw === null ? item.load_kw : item.paired_load_kw;
    if (codes.includes(CAPACITY)) row[CAPACITY] = item.capacity_kw;
    if (codes.includes(LOAD)) row[LOAD] = alignedLoad;
    paired += item.paired_hours;
    loadHours += item.load_hours;
    points.set(item.period, row);
  }
  analytic.forEach((result, index) => {
    for (const item of result.data) {
      const row: Record<string, number | null> = points.get(item.period) || {};
      row[other[index]] = item.avg;
      points.set(item.period, row);
    }
  });
  const rows = [...points.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([period, values]) => ({
    period, label: labelFor(period, window), ...values,
  }));
  return { rows, paired, loadHours };
}

export default function SystemLoadCompare({ year, month, catalog, user }: {
  year: number; month: number; catalog: Catalog; user: User;
}) {
  const [window, setWindow] = useState<WindowType>('day');
  const [day, setDay] = useState(isoWita());
  const CAPACITY=catalog.roles?.['system.capacity']||'';
  const LOAD=catalog.roles?.['system.load']||'';
  const [selected, setSelected] = useState<string[]>([CAPACITY,LOAD].filter(Boolean));
  const [settings, setSettings] = useState<ChartSettings | null>(null);
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState<Awaited<ReturnType<typeof loadChart>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectionNotice, setSelectionNotice] = useState('');
  const parameters = useMemo(() => timeRange(window, day, year, month), [window, day, year, month]);
  const available = catalog.metrics.filter(m => m.active && m.code !== 'daya_mampu_sistem_kw');
  const selectedMetrics = selected.map(code => available.find(m => m.code === code)).filter((m): m is Metric => Boolean(m));
  const displayUnit = selectedMetrics[0]?.unit || 'kW';
  const chartUnit = displayUnit === 'kW' ? 'MW' : displayUnit;
  const divisor = displayUnit === 'kW' ? 1000 : 1;
  const bothSystem = Boolean(CAPACITY&&LOAD&&selected.includes(CAPACITY) && selected.includes(LOAD));

  async function reloadSettings(resetSelection = true) {
    const latest = await api<ChartSettings>('/dashboard-charts');
    setSettings(latest);
    if (resetSelection) setSelected(latest.effective);
  }
  useEffect(() => {
    let alive = true;
    api<ChartSettings>('/dashboard-charts').then(r => {
      if (alive) { setSettings(r); setSelected(r.effective); }
    }).catch(e => { if (alive) setError(errorText(e)); });
    return () => { alive = false; };
  }, [user.id]);
  const chosenKey = selected.join('|');
  useEffect(() => {
    if (!settings || selected.length === 0) { setData(null); return; }
    let live = true;
    setLoading(true);
    loadChart(selected, parameters, window, CAPACITY, LOAD).then(value => {
      if (live) { setData(value); setError(''); }
    }).catch(e => { if (live) { setError(errorText(e)); setData(null); } })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [chosenKey, parameters, window, settings?.source, CAPACITY, LOAD]);

  function toggle(code: string) {
    const metric = available.find(m => m.code === code);
    if (!metric) return;
    setSelectionNotice(''); setMessage('');
    if (selected.includes(code)) { setSelected(current => current.filter(item => item !== code)); return; }
    if (selected.length >= (settings?.max_series || 4)) {
      setSelectionNotice('Maksimal empat parameter dalam satu grafik.'); return;
    }
    if (selectedMetrics.length && metric.unit !== selectedMetrics[0].unit) {
      setSelectionNotice(`Satuan ${metric.unit} berbeda dari ${selectedMetrics[0].unit}; pilihan diganti menjadi ${metric.name}.`);
      setSelected([code]); return;
    }
    setSelected(current => [...current, code]);
  }

  async function saveSettings(scope: 'system' | 'mine') {
    if (!selected.length) { setSelectionNotice('Pilih setidaknya satu parameter.'); return; }
    setSaving(true); setError(''); setMessage('');
    try {
      await api(`/dashboard-charts/${scope}`, {
        method: 'PUT', body: JSON.stringify({ metric_codes: selected }),
      });
      await reloadSettings(false);
      setMessage(scope === 'system' ? 'Default sistem berhasil disimpan.' : 'Pilihan grafik pribadi berhasil disimpan.');
    } catch (e) { setError(errorText(e)); }
    finally { setSaving(false); }
  }
  async function resetPersonal() {
    setSaving(true); setError(''); setMessage('');
    try {
      await api('/dashboard-charts/mine', { method: 'DELETE' });
      await reloadSettings(); setMessage('Pilihan pribadi direset ke default sistem.');
    } catch (e) { setError(errorText(e)); }
    finally { setSaving(false); }
  }

  const rows = (data?.rows || []).map(row => {
    const result: ChartRow = { ...row };
    for (const code of selected) {
      const value = row[code];
      result[code] = typeof value === 'number' ? value / divisor : null;
    }
    return result;
  });
  const title = bothSystem && selected.length === 2
    ? 'Daya Mampu Sistem vs Beban Sistem' : 'Grafik Parameter Pilihan';

  return <section className="panel compare-panel">
    {(!CAPACITY||!LOAD)&&<p className="notice info">Parameter utama belum diatur. {user.role==='admin'&&<a href="#/settings" onClick={()=>sessionStorage.setItem('berauload_settings_tab','primary')}>Buka Pengaturan → Parameter utama unit</a>}</p>}
    <div className="compare-header">
      <div><h3><BarChart3 size={20}/> {title}</h3>
        <p>{bothSystem ? 'Kolom H (daya mampu) dibandingkan dengan kolom J (beban sistem) pada periode yang sama.' : 'Rata-rata setiap parameter untuk interval yang dipilih; tidak mencampur satuan.'}</p></div>
      <div className="compare-modes">{([['hour', '24 Jam'], ['day', 'Bulanan'], ['month', 'Tahunan'], ['year', 'Multi-Tahun']] as const).map(([key, label]) =>
        <button type="button" className={window === key ? 'active' : ''} key={key} onClick={() => setWindow(key)}>{label}</button>)}
      </div>
    </div>
    <div className="chart-preference-bar">
      <div><b>{selectedMetrics.length} parameter</b><small>{settings?.source === 'personal' ? 'Default pribadi' : 'Default sistem'} · {chartUnit}</small></div>
      <button type="button" className="btn secondary sm" onClick={() => setEditing(v => !v)}><Settings2 size={15}/> Pilih Parameter</button>
    </div>
    {editing && <div className="chart-selector">
      <div className="chart-selector-top"><b>Parameter yang ditampilkan</b><span>Maksimal {settings?.max_series || 4}, satuan harus sama</span></div>
      <div className="chart-selector-grid">{available.map(metric => <label key={metric.code} className="chart-option">
        <input type="checkbox" checked={selected.includes(metric.code)} onChange={() => toggle(metric.code)}/>
        <span><b>{metric.name}</b><small>{metric.code} · {metric.unit}</small></span>
      </label>)}</div>
      {selectionNotice && <div className="notice info">{selectionNotice}</div>}
      <div className="chart-selector-actions">
        <button className="btn secondary sm" type="button" onClick={() => { setSelected(settings?.system || [CAPACITY, LOAD].filter(Boolean)); setSelectionNotice(''); }}><RotateCcw size={14}/> Muat Default Sistem</button>
        <button className="btn secondary sm" type="button" disabled={saving || !settings?.personal} onClick={resetPersonal}>Reset Pilihan Pribadi</button>
        <button className="btn primary sm" type="button" disabled={saving || selected.length === 0} onClick={() => saveSettings('mine')}><Check size={14}/> Simpan Pilihan Saya</button>
        {user.role === 'admin' && <button className="btn secondary sm" type="button" disabled={saving || selected.length === 0} onClick={() => saveSettings('system')}>Jadikan Default Sistem</button>}
      </div>
    </div>}
    {window === 'hour' && <div className="compare-date"><label>Pilih tanggal <input type="date" value={day} onChange={e => setDay(e.target.value)}/></label></div>}
    {window !== 'hour' && <p className="compare-range">{window === 'day' ? `${months[month - 1]} ${year}` : window === 'month' ? `Januari–Desember ${year}` : `10 tahun hingga ${year}`}</p>}
    {error && <div className="notice error" role="alert">{error}</div>}
    {message && <div className="notice success" role="status">{message}</div>}
    {!selected.length ? <div className="empty">Pilih setidaknya satu parameter untuk menampilkan grafik.</div>
      : loading ? <div className="empty">Memuat grafik parameter...</div>
      : rows.length ? <div className="compare-chart"><ResponsiveContainer width="100%" height={330}>
        <LineChart data={rows} margin={{ top: 15, right: 16, left: 5, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 4" stroke="#e5eff1" vertical={false}/>
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={20}/>
          <YAxis tick={{ fontSize: 11 }} width={55} tickFormatter={v => num(Number(v), 1)} unit={` ${chartUnit}`}/>
          <Tooltip formatter={value => [`${num(Number(value), 3)} ${chartUnit}`, '']} labelFormatter={v => `Periode: ${v}`}/>
          <Legend/>{selectedMetrics.map((metric, i) => <Line key={metric.code} name={metric.name} dataKey={metric.code} stroke={COLORS[i % COLORS.length]} strokeWidth={2.6} dot={rows.length < 13} connectNulls={false} isAnimationActive={false}/>)}
        </LineChart>
      </ResponsiveContainer></div> : <div className="empty">Tidak ada pembacaan untuk parameter terpilih pada periode ini.</div>}
    {bothSystem && (data?.loadHours || 0) > 0 && data?.paired === 0 &&
      <div className="compare-warning"><AlertCircle size={16}/> Daya mampu (kolom H) belum tersedia; data kosong tidak dianggap nol.</div>}
    <p className="compare-help">{bothSystem
      ? `${data?.paired || 0} jam memiliki pasangan daya mampu dan beban. Grafik H/J memakai pembacaan berpasangan; parameter lain memakai rata-rata masing-masing periode.`
      : 'Periode agregat menampilkan rata-rata pembacaan valid per parameter. Titik tanpa data tetap kosong.'}
    </p>
  </section>;
}
