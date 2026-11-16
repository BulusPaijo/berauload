"""Version 1 mapping was inspected against LAPORAN BEBAN FORM NOVEMBER 2026.xlsx.

Upper table: rows 9..32, columns B:O and R:AF.
Lower recap: rows 36..59, columns B:O and raw auxiliary R:AC.
One row = one hour, one numeric cell = one metric reading. No inferred zeros.
"""
ASSETS = [
 ('pltu_lati','PLTU Lati','pembangkit'), ('sewa_tama','Sewa Tama','pembangkit'),
 ('pltd','PLTD','pembangkit'), ('pltu_berau','PLTU Berau','pembangkit'),
 ('gi','Incoming GI','incoming'), ('sistem','Sistem Berau','sistem'),
 *[(f'feeder_{i}',f'Feeder {i}','feeder') for i in range(1,6)],
]
# code, label, unit, group, mode, asset
METRICS = [
 ('pltu_lati_cb33_kw','PLTU Lati CB-33','kW','PEMBANGKIT','input','pltu_lati'),
 ('pltu_lati_cb31_kw','PLTU Lati CB-31','kW','PEMBANGKIT','input','pltu_lati'),
 ('sewa_tama_1_kw','Sewa Tama 1','kW','PEMBANGKIT','input','sewa_tama'),
 ('sewa_tama_2_kw','Sewa Tama 2','kW','PEMBANGKIT','input','sewa_tama'),
 ('pltd_kw','PLTD','kW','PEMBANGKIT','input','pltd'),
 ('pltu_berau_unit1_kw','PLTU Berau Unit 1','kW','PEMBANGKIT','input','pltu_berau'),
 ('pltu_berau_unit2_kw','PLTU Berau Unit 2','kW','PEMBANGKIT','input','pltu_berau'),
 ('pltu_berau_og3_kw','PLTU Berau OG-3','kW','PEMBANGKIT','input','pltu_berau'),
 ('pltu_berau_og4_kw','PLTU Berau OG-4','kW','PEMBANGKIT','input','pltu_berau'),
 ('frequency_hz','Frekuensi','Hz','KUALITAS','input','sistem'),
 ('voltage_r_kv','Tegangan PLTD R','kV','KUALITAS','input','sistem'),
 ('voltage_s_kv','Tegangan PLTD S','kV','KUALITAS','input','sistem'),
 ('voltage_t_kv','Tegangan PLTD T','kV','KUALITAS','input','sistem'),
 ('jumlah_beban_kw','Jumlah Beban (bagian atas Excel)','kW','REKAP','computed','sistem'),
 ('pltu_lati_total_kw','PLTU Lati (rekap)','kW','REKAP','computed','pltu_lati'),
 ('pltu_berau_total_kw','PLTU Berau (rekap)','kW','REKAP','computed','pltu_berau'),
 ('sewa_tama_total_kw','Sewa Tama (rekap)','kW','REKAP','computed','sewa_tama'),
 ('pltd_total_kw','PLTD (rekap)','kW','REKAP','computed','pltd'),
 ('tambang_lapor_kw','Tambang (lapor)','kW','REKAP','input','sistem'),
 ('incoming_gi_kw','Incoming GI','kW','REKAP','input','gi'),
 ('daya_pasok_pembangkit_kw','Daya Pasok Pembangkit','kW','REKAP','computed','sistem'),
 ('total_incoming_gi_kw','Total + Incoming GI','kW','REKAP','computed','sistem'),
 ('beban_sistem_kw','Beban Sistem','kW','REKAP','computed','sistem'),
 ('sistem_plus_tambang_kw','Sistem + Tambang','kW','REKAP','computed','sistem'),
 ('tambang_lati_kw','Tambang Lati','kW','REKAP','imported','sistem'),
 ('beban_suaran_kw','Beban Suaran','kW','REKAP','input','sistem'),
 ('pltd_berau_kw','PLTD Berau','kW','REKAP','input','pltd'),
 ('beban_padam_kw','Beban Padam','kW','REKAP','input','sistem'),
]
for i in range(1,6):
 for phase in ('r','s','t'):
  METRICS.append((f'feeder_{i}_{phase}_a',f'Feeder {i} Arus {phase.upper()}','A','FEEDER','input',f'feeder_{i}'))
for c in 'RSTUVWXYZ':
 METRICS.append((f'rekap_{c.lower()}','Rekap kolom '+c+' (sumber Excel)','—','REKAP_LAIN','input','sistem'))
for c in ('AA','AB','AC'):
 METRICS.append((f'rekap_{c.lower()}','Rekap kolom '+c+' (sumber Excel)','—','REKAP_LAIN','input','sistem'))

UPPER = { 'B':'pltu_lati_cb33_kw','C':'pltu_lati_cb31_kw','D':'sewa_tama_1_kw',
 'E':'sewa_tama_2_kw','F':'pltd_kw','G':'pltu_berau_unit1_kw','H':'pltu_berau_unit2_kw',
 'I':'pltu_berau_og3_kw','J':'pltu_berau_og4_kw','K':'frequency_hz',
 'L':'voltage_r_kv','M':'voltage_s_kv','N':'voltage_t_kv','O':'jumlah_beban_kw'}
for i, offset in enumerate([18,21,24,27,30],start=1):
 for phase, ci in zip('rst',range(offset,offset+3)):
  import openpyxl.utils
  UPPER[openpyxl.utils.get_column_letter(ci)] = f'feeder_{i}_{phase}_a'
LOWER = dict(zip('BCDEFGHIJKLMNO', [
 'pltu_lati_total_kw','pltu_berau_total_kw','sewa_tama_total_kw','pltd_total_kw',
 'tambang_lapor_kw','incoming_gi_kw','daya_pasok_pembangkit_kw','total_incoming_gi_kw',
 'beban_sistem_kw','sistem_plus_tambang_kw','tambang_lati_kw','beban_suaran_kw',
 'pltd_berau_kw','beban_padam_kw']))
for c in 'RSTUVWXYZ': LOWER[c]=f'rekap_{c.lower()}'
for c in ['AA','AB','AC']: LOWER[c]=f'rekap_{c.lower()}'
# Legacy V1.1 manual metric: not used by capacity-vs-load chart.
# Source of truth for daya mampu is recap H: daya_pasok_pembangkit_kw.
METRICS.append(('daya_mampu_sistem_kw','Daya Mampu Manual (Legacy V1.1)','kW','REKAP','input','sistem'))
CODE_MAP = {m[0]:m for m in METRICS}

# Carefully limited calculation engine: matches known formula structure; does not
# invent values for rows with unavailable source components.
def calculate(raw:dict[str,float]) -> dict[str,float]:
 def present(*codes): return any(c in raw for c in codes)
 def s(*codes): return round(sum(raw.get(c,0) for c in codes),5)
 d = {}
 if present('pltu_lati_cb33_kw','pltu_lati_cb31_kw','sewa_tama_1_kw','sewa_tama_2_kw','pltd_kw','pltu_berau_og3_kw','pltu_berau_og4_kw'):
  d['jumlah_beban_kw'] = s('pltu_lati_cb33_kw','pltu_lati_cb31_kw','sewa_tama_1_kw','sewa_tama_2_kw','pltd_kw','pltu_berau_og3_kw','pltu_berau_og4_kw')
 if present('pltu_lati_cb33_kw','pltu_lati_cb31_kw') and 'beban_suaran_kw' in raw:
  d['pltu_lati_total_kw'] = s('pltu_lati_cb33_kw','pltu_lati_cb31_kw','beban_suaran_kw')
 if present('pltu_berau_og3_kw','pltu_berau_og4_kw'):
  d['pltu_berau_total_kw'] = round(s('pltu_berau_og3_kw','pltu_berau_og4_kw') - raw.get('pltd_berau_kw',0),5)
 if present('sewa_tama_1_kw','sewa_tama_2_kw'):
  d['sewa_tama_total_kw'] = s('sewa_tama_1_kw','sewa_tama_2_kw')
 if 'pltd_kw' in raw: d['pltd_total_kw'] = raw['pltd_kw']
 # Excel H36: =B36+C36+D36+E36+N36
 items=('pltu_lati_total_kw','pltu_berau_total_kw','sewa_tama_total_kw','pltd_total_kw')
 vals={**raw,**d}
 if all(c in vals for c in items):
  d['daya_pasok_pembangkit_kw']=round(sum(vals[c] for c in items)+raw.get('pltd_berau_kw',0),5)
 if 'daya_pasok_pembangkit_kw' in d and 'incoming_gi_kw' in raw:
  d['total_incoming_gi_kw']=round(d['daya_pasok_pembangkit_kw']+raw['incoming_gi_kw'],5)
  d['beban_sistem_kw']=d['total_incoming_gi_kw']
 if 'beban_sistem_kw' in d and 'tambang_lati_kw' in raw:
  d['sistem_plus_tambang_kw']=round(d['beban_sistem_kw']+raw['tambang_lati_kw'],5)
 return d
