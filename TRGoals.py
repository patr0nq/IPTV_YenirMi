# ! Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli import konsol
from httpx     import Client
from parsel    import Selector
import re

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx       = Client(timeout=10)

    def referer_domainini_al(self):
        referer_deseni = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()

        if eslesme := re.search(referer_deseni, icerik):
            return eslesme[1]
        else:
            raise ValueError("M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")

    def trgoals_domaini_al(self):
        redirect_url = "https://bit.ly/m/taraftarium24w"
        while "bit.ly" in redirect_url:
            redirect_url = self.redirect_gec(redirect_url)
        return redirect_url

    def redirect_gec(self, redirect_url: str):
        response = self.httpx.get(redirect_url, follow_redirects=True)
        domain = str(response.url).strip("/")
        if "error" in domain:
            raise ValueError("Redirect domain hatalı..")
        return domain

    def yeni_domaini_al(self, eldeki_domain: str) -> str:
        def check_domain(domain: str) -> str:
            if domain == "https://trgoalsgiris.xyz":
                raise ValueError("Yeni domain alınamadı")
            return domain

        try:
            # İlk kontrol: Redirect geçiş
            yeni_domain = check_domain(self.redirect_gec(eldeki_domain))
        except Exception:
            konsol.log("[red][!] `redirect_gec(eldeki_domain)` fonksiyonunda hata oluştu.")
            try:
                # İkinci kontrol: trgoals domainini al
                yeni_domain = check_domain(self.trgoals_domaini_al())
            except Exception:
                konsol.log("[red][!] `trgoals_domaini_al` fonksiyonunda hata oluştu.")
                try:
                    # Üçüncü kontrol: Alternatif bir URL üzerinden redirect geç
                    yeni_domain = check_domain(self.redirect_gec("https://t.co/MTLoNVkGQN"))
                except Exception:
                    konsol.log("[red][!] `redirect_gec('https://t.co/MTLoNVkGQN')` fonksiyonunda hata oluştu.")
                    # Son çare: Yeni bir domain üret
                    rakam = int(eldeki_domain.split("trgoals")[1].split(".")[0]) + 1
                    yeni_domain = f"https://trgoals{rakam}.xyz"

        return yeni_domain

    def m3u_guncelle(self):
        eldeki_domain = self.referer_domainini_al()
        konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

        yeni_domain = self.yeni_domaini_al(eldeki_domain)
        konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

        kontrol_url = f"{yeni_domain}/channel.html?id=yayin1"

        with open(self.m3u_dosyasi, "r") as dosya:
            m3u_icerik = dosya.read()

        if not (eski_yayin_url := re.search(r'https?:\/\/[^\/]+\.(workers\.dev|shop|click)\/?', m3u_icerik)):
            raise ValueError("M3U dosyasında eski yayın URL'si bulunamadı!")

        eski_yayin_url = eski_yayin_url[0]
        konsol.log(f"[yellow][~] Eski Yayın URL : {eski_yayin_url}")

        # API çağrısı kaldırıldı, doğrudan istek yapılıyor
        response = self.httpx.get(kontrol_url, follow_redirects=True)

        if not (yayin_ara := re.search(r'var baseurl = "(https?:\/\/[^"]+)"', response.text)):
            secici = Selector(response.text)
            baslik = secici.xpath("//title/text()").get()
            if baslik == "404 Not Found":
                yeni_domain = eldeki_domain
                yayin_ara   = [None, eski_yayin_url]
            else:
                konsol.print(response.text)
                raise ValueError("Base URL bulunamadı!")

        yayin_url = yayin_ara[1]
        konsol.log(f"[green][+] Yeni Yayın URL : {yayin_url}")

        yeni_m3u_icerik = m3u_icerik.replace(eski_yayin_url, yayin_url)
        yeni_m3u_icerik = yeni_m3u_icerik.replace(eldeki_domain, yeni_domain)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(yeni_m3u_icerik)

if __name__ == "__main__":
    guncelleyici = TRGoals("Kanallar/KekikAkademi.m3u")
    guncelleyici.m3u_guncelle()