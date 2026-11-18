"""Owner-provided provisional defaults, each stored as editable expressions.

Thresholds are NOT certified PLN standards. Never rewrite admin edits on restart.
"""
CONSTANTS = [
    ('v_ll_nominal', 'Tegangan antar fasa nominal', 400, 'V'),
    ('v_ln_nominal', 'Tegangan fasa-netral nominal', 231, 'V'),
    ('batas_grounding', 'Batas grounding sementara', 5, 'ohm'),
]

COLUMNS = [
    ('total_r', 'Total arus fasa R', 'A', 'SUM_JURUSAN(i_r)'),
    ('total_s', 'Total arus fasa S', 'A', 'SUM_JURUSAN(i_s)'),
    ('total_t', 'Total arus fasa T', 'A', 'SUM_JURUSAN(i_t)'),
    ('total_n', 'Total arus netral', 'A', 'SUM_JURUSAN(i_n)'),
    ('rata_fasa', 'Rata-rata arus fasa', 'A', 'AVG(total_r, total_s, total_t)'),
    ('arus_nominal', 'Arus nominal (In)', 'A',
     'IF(fase = 3, kva * 1000 / (1.732 * v_ll_nominal), kva * 1000 / v_ln_nominal)'),
    ('beban_kva', 'Beban (kVA)', 'kVA',
     'IF(fase = 3, rata_fasa * 1.732 * v_ll_nominal / 1000, total_r * v_ln_nominal / 1000)'),
    ('persen_beban', 'Persen beban', '%', 'beban_kva / kva * 100'),
    ('tak_seimbang', 'Ketidakseimbangan (%)', '%',
     'MAX(ABS(total_r - rata_fasa), ABS(total_s - rata_fasa), ABS(total_t - rata_fasa)) / rata_fasa * 100'),
    ('rasio_netral', 'Rasio arus netral (%)', '%', 'total_n / rata_fasa * 100'),
    ('v_rel_rata', 'Rata-rata tegangan rel (V)', 'V', 'AVG(v_r0, v_s0, v_t0)'),
    ('v_ujung_min', 'Tegangan ujung minimum (V)', 'V',
     'MIN(v_end_rn, v_end_sn, v_end_tn)'),
    ('jatuh_tegangan', 'Jatuh tegangan ujung (V)', 'V', 'v_rel_rata - v_ujung_min'),
]

RULES = [
    ('underload', 'Underload', 'category', 'persen_beban < 60', '#2d72ba', 'circle'),
    ('normal', 'Normal', 'category', 'AND(persen_beban >= 60, persen_beban < 80)', '#07896c', 'circle'),
    ('tinggi', 'Tinggi', 'category', 'AND(persen_beban >= 80, persen_beban <= 100)', '#e58a00', 'circle'),
    ('overload', 'Overload', 'category', 'persen_beban > 100', '#b62823', 'circle'),
    ('tidak_seimbang', 'Tidak seimbang', 'finding',
     'OR(OR(total_r < rata_fasa * 0.8, total_r > rata_fasa * 1.15), OR(total_s < rata_fasa * 0.8, total_s > rata_fasa * 1.15), OR(total_t < rata_fasa * 0.8, total_t > rata_fasa * 1.15))',
     '#344850', 'diamond'),
    ('overload_1_fasa', 'Overload 1 fasa', 'finding',
     'MAX(total_r, total_s, total_t) > arus_nominal', '#b62823', 'triangle'),
    ('netral_tinggi', 'Netral tinggi', 'finding', 'rasio_netral > 25', '#344850', 'diamond'),
    ('tegangan_drop', 'Tegangan drop', 'finding', 'v_ujung_min < 198', '#8546a7', 'square'),
    ('jatuh_tegangan_tinggi', 'Jatuh tegangan > 10 V', 'finding',
     'jatuh_tegangan > 10', '#8546a7', 'square'),
    ('grounding', 'Grounding tidak normal', 'finding',
     'OR(ground_tr > batas_grounding, FLAG(ground_tr, PUTUS))', '#b62823', 'diamond'),
    ('kandidat_mutasi', 'Kandidat mutasi', 'finding', 'persen_beban < 20', '#2d72ba', 'circle'),
]
OLD_EXCEL = 'kva * 1000 / 380 * 1.732 / 3'
