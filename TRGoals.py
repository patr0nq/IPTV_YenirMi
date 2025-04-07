# ! Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli import konsol
from httpx import Client, HTTPError, TimeoutException, Timeout
from parsel import Selector
import re
import traceback
import random
import time

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }
        self.httpx = Client(headers=self.headers, timeout=Timeout(30.0), follow_redirects=True)
        
        # Bilinen TRGoals domain'leri
        self.bilinen_domainler = [
            "https://trgoals1254.xyz",
            "https://trgoalsgiris.xyz"
        ]

    def referer_domainini_al(self):
        referer_deseni = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        try:
            with open(self.m3u_dosyasi, "r") as dosya:
                icerik = dosya.read()

            if eslesme := re.search(referer_deseni, icerik):
                return eslesme[1]
            else:
                konsol.log("[red][!] M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")
                # Örnek domain dönelim ki program çalışmaya devam edebilsin
                return "https://trgoals1254.xyz"
        except Exception as e:
            konsol.log(f"[red][!] Dosya okuma hatası: {str(e)}")
            return "https://trgoals1254.xyz"

    def domain_check(self, domain):
        """Verilen domain'e istek atarak çalışıp çalışmadığını kontrol eder"""
        try:
            response = self.httpx.get(domain, timeout=10.0)
            if response.status_code == 200:
                konsol.log(f"[green][+] Domain aktif: {domain}")
                return True
            else:
                konsol.log(f"[yellow][~] Domain yanıt verdi ama durum kodu {response.status_code}: {domain}")
                return False
        except Exception as e:
            konsol.log(f"[red][!] Domain kontrolü başarısız: {domain} - {str(e)}")
            return False

    def find_trgoals_url_from_twitter(self):
        """Twitter'dan (şimdi X) TRGoals linkini bulmaya çalışır"""
        try:
            twitter_urls = [
                "https://twitter.com/taraftarium24tv",
                "https://twitter.com/trgoals24",
                "https://twitter.com/search?q=trgoals&src=typed_query&f=live"
            ]
            
            for url in twitter_urls:
                try:
                    konsol.log(f"[yellow][~] Twitter'dan TRGoals linki aranıyor: {url}")
                    response = self.httpx.get(url, timeout=15.0)
                    
                    # TRGoals domain'i ara
                    trgoals_urls = re.findall(r'https?://(?:[^/]*trgoals[^/\s"\']*\.[^\s"\']+)', response.text)
                    if trgoals_urls:
                        for trgoals_url in trgoals_urls:
                            trgoals_url = trgoals_url.strip('"\'.,;:)( ')
                            if self.domain_check(trgoals_url):
                                return trgoals_url
                    
                    # t.co kısaltması ara
                    tco_urls = re.findall(r'https?://t\.co/[a-zA-Z0-9]+', response.text)
                    if tco_urls:
                        for tco_url in tco_urls:
                            try:
                                response = self.httpx.get(tco_url, follow_redirects=True, timeout=10.0)
                                final_url = str(response.url)
                                if "trgoals" in final_url and self.domain_check(final_url):
                                    return final_url
                            except Exception:
                                continue
                except Exception as e:
                    konsol.log(f"[red][!] Twitter URL kontrol hatası ({url}): {str(e)}")
                    continue
                    
            return None
        except Exception as e:
            konsol.log(f"[red][!] Twitter TRGoals arama hatası: {str(e)}")
            return None

    def find_active_domain(self):
        """Aktif TRGoals domain'ini bulmaya çalışır"""
        # 1. Bilinen domain'leri kontrol et
        for domain in self.bilinen_domainler:
            if self.domain_check(domain):
                return domain
                
        # 2. Twitter'dan bulmaya çalış
        if twitter_domain := self.find_trgoals_url_from_twitter():
            return twitter_domain
            
        # 3. Numara arttırarak tahmin et
        for i in range(1, 20):
            tahmin_domain = f"https://trgoals{i}.xyz"
            if tahmin_domain not in self.bilinen_domainler and self.domain_check(tahmin_domain):
                return tahmin_domain
                
        # 4. Hiçbiri çalışmazsa eldeki domain'i dön
        konsol.log("[yellow][~] Aktif domain bulunamadı, varsayılan domain kullanılacak")
        return "https://trgoals1254.xyz"

    def extract_yayin_url(self, domain):
        """Verilen domain'den yayın URL'sini ayıklar"""
        try:
            kontrol_url = f"{domain}/channel.html?id=yayin1"
            konsol.log(f"[yellow][~] Yayın URL kontrol ediliyor: {kontrol_url}")
            
            # CloudFlare veya benzeri koruma varsa header'ları genişlet
            self.httpx.headers.update({
                "Referer": domain,
                "Origin": domain
            })
            
            # Bazen bot koruması olabileceği için biraz bekleme ekleyin
            time.sleep(2)
            
            response = self.httpx.get(kontrol_url, timeout=15.0)
            
            # Base URL arama (standart yöntem)
            if yayin_ara := re.search(r'var\s+baseurl\s*=\s*["\']?(https?:\/\/[^"\']+)["\']?', response.text):
                yayin_url = yayin_ara[1]
                konsol.log(f"[green][+] Yayın URL bulundu: {yayin_url}")
                return yayin_url
                
            # İframe kaynak kontrolü (alternatif yöntem)
            secici = Selector(response.text)
            iframe_src = secici.xpath("//iframe/@src").get()
            if iframe_src and "http" in iframe_src:
                konsol.log(f"[green][+] Iframe kaynak URL bulundu: {iframe_src}")
                # İframe kaynağı doğrudan stream URL'si olabilir veya içinde stream URL'si bulunabilir
                if "m3u8" in iframe_src or "workers.dev" in iframe_src:
                    return iframe_src
                else:
                    # İframe içindeki içeriği kontrol et
                    iframe_response = self.httpx.get(iframe_src, timeout=10.0)
                    if m3u8_ara := re.search(r'(https?:\/\/[^"\']+\.m3u8[^"\']*)', iframe_response.text):
                        return m3u8_ara[1]
            
            # JavaScript içinde stream URL'si arama
            if stream_ara := re.search(r'(https?:\/\/[^/]+\.(workers\.dev|shop|cfd|net)[^"\']*)', response.text):
                yayin_url = stream_ara[1]
                konsol.log(f"[green][+] JavaScript içinde stream URL bulundu: {yayin_url}")
                return yayin_url
                
            konsol.log("[red][!] Yayın URL'si bulunamadı!")
            return None
            
        except Exception as e:
            konsol.log(f"[red][!] Yayın URL çıkarma hatası: {str(e)}")
            return None

    def yeni_domaini_al(self, eldeki_domain):
        """Aktif TRGoals domain'ini bulur"""
        try:
            # Önce eldeki domain'i kontrol et
            if self.domain_check(eldeki_domain):
                return eldeki_domain
                
            # Eldeki domain çalışmıyorsa yeni domain bul
            return self.find_active_domain()
        except Exception as e:
            konsol.log(f"[red][!] Domain alma hatası: {str(e)}")
            # Hata durumunda eldeki domain'i geri dön
            return eldeki_domain

    def m3u_guncelle(self):
        try:
            eldeki_domain = self.referer_domainini_al()
            konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

            yeni_domain = self.yeni_domaini_al(eldeki_domain)
            konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

            with open(self.m3u_dosyasi, "r") as dosya:
                m3u_icerik = dosya.read()

            # Eski yayın URL'sini bul
            eski_yayin_url_match = re.search(r'https?:\/\/[^\/]+\.(workers\.dev|shop|cfd|net)\/?[^\s]*', m3u_icerik)
            if not eski_yayin_url_match:
                konsol.log("[red][!] M3U dosyasında eski yayın URL'si bulunamadı!")
                eski_yayin_url = None
            else:
                eski_yayin_url = eski_yayin_url_match[0]
                konsol.log(f"[yellow][~] Eski Yayın URL : {eski_yayin_url}")

            # Yeni yayın URL'sini al
            yayin_url = self.extract_yayin_url(yeni_domain)
            
            if not yayin_url and not eski_yayin_url:
                konsol.log("[red][!] Yayın URL'si alınamadı ve eski URL de bulunamadı!")
                return False
            elif not yayin_url:
                konsol.log("[yellow][~] Yeni yayın URL'si alınamadı, eski URL kullanılacak")
                yayin_url = eski_yayin_url
            
            konsol.log(f"[green][+] Yeni Yayın URL : {yayin_url}")

            # M3U içeriğini güncelle
            yeni_m3u_icerik = m3u_icerik
            
            # Eski domain'i yeni domain ile değiştir
            yeni_m3u_icerik = yeni_m3u_icerik.replace(eldeki_domain, yeni_domain)
            
            # Eski yayın URL'si varsa değiştir
            if eski_yayin_url:
                yeni_m3u_icerik = yeni_m3u_icerik.replace(eski_yayin_url, yayin_url)
            else:
                # Eski yayın URL'si yoksa, her bir kanal için URL'yi ekle/güncelle
                # Bu kısım M3U formatınıza göre değişebilir
                konsol.log("[yellow][~] Eski yayın URL bulunamadı, manuel güncelleme yapılıyor")
                
                # M3U içeriğindeki her bir kanalı bulup URL'yi güncelle
                kanal_satirlari = re.findall(r'(#EXTINF:.*?\n)(.*?)(\n|$)', m3u_icerik)
                if kanal_satirlari:
                    for extinf, url, _ in kanal_satirlari:
                        if not url.startswith("http"):
                            konsol.log(f"[yellow][~] Kanal URL'si güncelleniyor: {extinf.strip()}")
                            yeni_m3u_icerik = yeni_m3u_icerik.replace(
                                f"{extinf}{url}", 
                                f"{extinf}{yayin_url}"
                            )

            # Dosyayı yeni içerikle güncelle
            with open(self.m3u_dosyasi, "w") as dosya:
                dosya.write(yeni_m3u_icerik)
                
            konsol.log(f"[green][+] M3U dosyası başarıyla güncellendi: {self.m3u_dosyasi}")
            return True
            
        except Exception as e:
            konsol.log(f"[red][!] M3U güncelleme işleminde hata: {str(e)}")
            konsol.log(f"[yellow][~] Hata detayı: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    try:
        konsol.log("[green][+] TRGoals M3U güncelleyici başlatılıyor...")
        guncelleyici = TRGoals("Kanallar/KekikAkademi.m3u")
        basarili = guncelleyici.m3u_guncelle()
        if basarili:
            konsol.log("[green][+] İşlem başarıyla tamamlandı!")
        else:
            konsol.log("[red][!] İşlem tamamlandı ancak bazı hatalar oluştu.")
    except Exception as e:
        konsol.log(f"[red][!] Program çalışırken beklenmeyen bir hata oluştu: {str(e)}")
        konsol.log(f"[yellow][~] Hata detayı: {traceback.format_exc()}")