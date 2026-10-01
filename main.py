import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# ================= KULLANICI BİLGİLERİ =================
TELEGRAM_TOKEN = "8841291692:AAFKHKf-0dj50J7ZL6XET2FqIxxu4JUcuPk"
CHAT_ID = "8905403085"

EXCEL_DOSYA_ADI = "trendyol_firsat_urunleri.xlsx"
KONTROL_ARALIGI_SANIYE = 7200  # Her 2 saatte bir Trendyol'u tarar
MINIMUM_NET_KAR_TL = 35        # Bildirim gelmesi için ürünün bırakması gereken minimum net kâr (TL)
# =======================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def telegram_mesaj_gonder(mesaj, dosya_yolu=None):
    """Telegram üzerinden bildirim ve Excel dosyası gönderir."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
        requests.post(url, data=payload)

        if dosya_yolu and os.path.exists(dosya_yolu):
            file_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            with open(dosya_yolu, "rb") as doc:
                requests.post(file_url, data={"chat_id": CHAT_ID}, files={"document": doc})
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")

def excel_kaydet(yeni_urunler):
    """Bulunan ürünleri Excel dosyasına ekler."""
    df_yeni = pd.DataFrame(yeni_urunler)
    if os.path.exists(EXCEL_DOSYA_ADI):
        df_mevcut = pd.read_excel(EXCEL_DOSYA_ADI)
        df_toplam = pd.concat([df_mevcut, df_yeni]).drop_duplicates(subset=["Ürün Linki"])
    else:
        df_toplam = df_yeni
    
    df_toplam.to_excel(EXCEL_DOSYA_ADI, index=False)

def trendyol_pazar_taramasi():
    """Trendyol Çok Satılanlar listesini inceler ve kârlı ürünleri süz araçıdır."""
    url = "https://www.trendyol.com/cok-satilanlar?sst=BEST_SELLER"
    
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Sayfaya ulaşılamadı. Durum kodu: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        urun_kartlari = soup.find_all("div", class_="p-card-chldrn-cntnr")
        
        bulunan_firsatlar = []

        for kart in urun_kartlari:
            try:
                title_elem = kart.find("span", class_="prdct-desc-cntnr-name")
                brand_elem = kart.find("span", class_="prdct-desc-cntnr-ttl")
                price_elem = kart.find("div", class_="prc-box-sllg")
                link_elem = kart.find("a")

                if not (title_elem and price_elem and link_elem):
                    continue

                urun_adi = f"{brand_elem.text if brand_elem else ''} {title_elem.text}".strip()
                urun_linki = "https://www.trendyol.com" + link_elem["href"]
                
                fiyat_text = price_elem.text.replace("TL", "").replace(".", "").replace(",", ".").strip()
                satis_fiyati = float(fiyat_text)

                # --- KÂR TAHMİNİ HESAPLAMA ---
                # Toptan ürün alış maliyeti perakende fiyatının yaklaşık %35'i kabul edilir.
                tahmini_alis_fiyati = satis_fiyati * 0.35 
                komisyon = satis_fiyati * 0.18 # Trendyol ortalama kategori komisyonu
                kargo = 38.0                   # Standart ortalama kargo maliyeti

                tahmini_net_kar = satis_fiyati - (tahmini_alis_fiyati + komisyon + kargo)

                if tahmini_net_kar >= MINIMUM_NET_KAR_TL: 
                    bulunan_firsatlar.append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Ürün Adı": urun_adi,
                        "Satış Fiyatı (TL)": satis_fiyati,
                        "Tahmini Alış (TL)": round(tahmini_alis_fiyati, 2),
                        "Tahmini Kâr (TL)": round(tahmini_net_kar, 2),
                        "Ürün Linki": urun_linki
                    })
            except Exception:
                continue

        return bulunan_firsatlar

    except Exception as e:
        print(f"Tarama hatası: {e}")
        return []

def ana_dongu():
    telegram_mesaj_gonder("🚀 *Trendyol 24 Saat Ürün Tarama Otomasyonu Başlatıldı!*")
    
    while True:
        firsatlar = trendyol_pazar_taramasi()
        
        if firsatlar:
            excel_kaydet(firsatlar)
            
            ozet_mesaj = f"🔥 *Yeni Kârlı Ürün Fırsatları Bulundu!*\nToplam {len(firsatlar)} potansiyel ürün tespit edildi.\n"
            for f in firsatlar[:3]: 
                ozet_mesaj += f"\n• *{f['Ürün Adı']}*\n  Satış: {f['Satış Fiyatı (TL)']} TL | Tahmini Kâr: *{f['Tahmini Kâr (TL)']} TL*\n  [Ürünü İncele]({f['Ürün Linki']})\n"
                
            telegram_mesaj_gonder(ozet_mesaj, dosya_yolu=EXCEL_DOSYA_ADI)
        
        time.sleep(KONTROL_ARALIGI_SANIYE)

if __name__ == "__main__":
    ana_dongu()