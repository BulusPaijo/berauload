from datetime import date
from io import BytesIO
from openpyxl import Workbook
from app.catalog import calculate
from app.importer import parse_load_excel

def make_book():
    book=Workbook();ws=book.active;ws.title='1';ws['B2']=date(2026,11,1)
    ws['B9']=2000;ws['C9']=3000;ws['D9']=4000;ws['E9']=5000;ws['F9']=1000
    ws['I9']=3000;ws['J9']=2000;ws['K9']=50.1;ws['R9']=90
    ws['G36']=7000;ws['J36']=35000
    # A formula cache may be unavailable when saved by openpyxl; parser should
    # still preserve the real manually entered data and avoid blank hours.
    out=BytesIO();book.save(out);return out.getvalue()

def test_parse_does_not_invent_future_days_or_hours():
    data=parse_load_excel(make_book(),2026,11)
    assert len(data['hours'])==1
    assert data['hours'][0]['hour']==0
    assert data['hours'][0]['values']['pltu_lati_cb33_kw']==2000
    assert data['hours'][0]['values']['beban_sistem_kw']==35000

def test_formula_source_example():
    raw={'pltu_lati_cb33_kw':2938,'pltu_lati_cb31_kw':4602,
         'sewa_tama_1_kw':5000,'sewa_tama_2_kw':5000,'pltd_kw':2400,
         'pltu_berau_og3_kw':4924,'pltu_berau_og4_kw':1366,
         'pltd_berau_kw':725,'beban_suaran_kw':1714.18,'incoming_gi_kw':7870}
    result=calculate(raw)
    assert result['jumlah_beban_kw']==26230
    assert result['pltu_lati_total_kw']==9254.18
    assert result['pltu_berau_total_kw']==5565
    assert result['daya_pasok_pembangkit_kw']==27944.18
    assert result['beban_sistem_kw']==35814.18
