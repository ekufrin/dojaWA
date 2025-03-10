import datetime
import os
import re
import difflib
import jellyfish._jellyfish as pyjellyfish
import schedule
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
import time
import requests
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

browser = None
original_window = None


# Pokretanje Firefoxa i Whatsapp-a
def start():
    global browser, original_window
     # Ako preglednik već radi, zatvori ga prije ponovnog pokretanja
    if browser is not None:
        try:
            browser.quit()
        except:
            pass  # Ako je već zatvoren, ignoriraj grešku
    
    options = Options()
    options.profile = '/root/.mozilla/firefox/pcv2qwd8.default-release-1730744277558'
    browser = webdriver.Firefox(options=options)
    browser.get('https://web.whatsapp.com/')
    original_window = browser.current_window_handle

# Postavke za DojaWA i Telegram
WAP_DOJAVA_CHAT_ID = "test"
TELEGRAM_TOKEN = "YOUR TELEGRAM API TOKEN"
TELEGRAM_CHAT_ID = "YOUR TELEGRAM GROUP CHAT ID"
znakovi = ['_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

# Kljucne rijeci za tip događaja
policija = ['policija', 'stoje', 'zaustavljaju', 'sjede', 'policijski kombi', 'policijski auto', 'zrtva', 'stopaju',
            'presretac', 'motorista', 'suzuki', 'vitara']
radari = ['snima', 'radar', 'tronožac', 'kamera', 'brzinu', 'pistolj', 'snajper']
sudar = ['sudar', 'prometna', 'nesreća', 'kvar']
vaga = ['vaga', 'carina', 'tehnički', 'inspekcija', 'kontrola']

# Poruke koje treba preskociti
preskoci_poruke = ['+', '-', 'jos uvijek', 'jos uvjek', 'otisli', 'otisli upravo', 'nema ih', 'i dalje', 'jos su  tu', 'chat.whatsapp.com', 'http']

# Učitavanje grupa iz datoteke
with open('grupe.txt', 'r', encoding='utf8') as g:
    groups = [group.strip() for group in g.readlines()]

# Inicijalizacija datoteka za svaku grupu
for grupa in groups:
    with open(f'poruke/{grupa}.txt', 'w'):
        pass


def obrisi_stare_poruke():
    # Za svaku grupu iz datoteke 'grupe.txt'
    with open('grupe.txt', 'r', encoding='utf8') as g:
        groups = [group.strip() for group in g.readlines()]

        for group in groups:
            group_file_path = f'poruke/{group}.txt'
            if os.path.exists(group_file_path):
                # Čitanje svih linija iz datoteke za grupu
                with open(group_file_path, 'r') as file:
                    lines = file.readlines()

                # Brišemo sve redove osim zadnje
                if len(lines) > 1:
                    with open(group_file_path, 'w') as file:
                        file.write(lines[-1])
    
    # Obrisi errore
    with open('errors.txt', 'w') as file:
        file.write('')
def posalji_poruku(wap_poruka, tg_poruka):
    user = WebDriverWait(browser, 20).until(EC.presence_of_element_located(
                        (By.XPATH, f'//span[@title="{WAP_DOJAVA_CHAT_ID}"]')))
    user.click()

    msg_box = WebDriverWait(browser, 20).until(EC.element_to_be_clickable(
                        (By.XPATH,
                         '/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]')))
    [msg_box.send_keys(c) for c in wap_poruka]

    posalji_gumb = WebDriverWait(browser, 20).until(EC.element_to_be_clickable(
                        (By.XPATH, '//button[@data-tab="11" and @aria-label="Send"]')))
    posalji_gumb.click()

    # Dodaje \\ ispred znakova kako bi se mogla poslati telegram poruka
    for znak in znakovi:
        tg_poruka = tg_poruka.replace(znak, '\\' + znak)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={tg_poruka}&parse_mode=MarkdownV2"
    requests.get(url)

def provjeri_policijske_akcije():
    browser.switch_to.new_window('tab')
    browser.get(
        'https://zagrebacka-policija.gov.hr/vijesti/8?page=1&tag=-1&tip=&Datumod=&Datumdo=&pojam=Najava+akcije+%E2%80%9EAlkohol+i+droge%E2%80%9C+te+%E2%80%9EBrzina%22')

    # Prihvati kolačiće

    try:
        kolacic = browser.find_element(By.XPATH, '//*[@class="gdc-button"]').click()
    except NoSuchElementException:
        pass

    # Pronađi najnoviju vijest
    vijest_naziv = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="content"]/div/div[2]/div/div[1]'))
    ).find_element(By.XPATH, '//*[@id="content"]/div/div[2]/div/div[1]/a/span')

    vijest_datum = browser.find_element(By.XPATH, '//*[@id="content"]/div/div[2]/div/div[1]/span').text.split('|')

    danasnji_datum = datetime.date.today().strftime('%d.%m.%Y.')

    # Provjeri postoji li akcija na danasnji dan
    if difflib.SequenceMatcher(None, vijest_naziv.text,
                               'Najava akcije „Alkohol i droge“ te „Brzina"').ratio() * 100 >= 80 and danasnji_datum == \
            vijest_datum[0].strip():
        vijest_naziv.click()
        tekst_akcije = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="content"]/div[1]/div[2]'))
        ).find_element(By.XPATH, '//*[@id="content"]/div[1]/div[2]').text

        trajanje_akcije = re.search(r'Tijekom vikenda.*?(?=Predmetnom akcijom|$)', tekst_akcije,
                                    re.DOTALL).group().strip()
        opis_akcije = re.search(r'Predmetnom akcijom.*?(?=Stranica|$)', tekst_akcije, re.DOTALL).group().strip()

        wap_poruka = f"*Policijska akcija* \n\n {trajanje_akcije} \n\n {opis_akcije} "
        tg_poruka = f"🚓 *Policijska akcija* 🚓 \n\n ⏳ {trajanje_akcije} \n\n 📝 {opis_akcije}"
        
        
        with open(f'poruke/policijske_akcije.txt', 'a+') as pakcija:
            pakcija.write(f"Za datum {danasnji_datum} postoji akcija, poruka poslana!\n")
        time.sleep(1)
        browser.close()
        browser.switch_to.window(original_window)

        # Ako postoji akcija, pošalji poruku
        posalji_poruku(wap_poruka, tg_poruka)

    else:
        with open(f'poruke/policijske_akcije.txt', 'a+') as pakcija:
            pakcija.write(f"Za datum {danasnji_datum} nije pronađena akcija\n")
        time.sleep(1)
        browser.close()
        browser.switch_to.window(original_window)

def provjeri_prometnu_prognozu():
    # Otvori novu karticu i pređi na HAK stranicu
        browser.switch_to.new_window('tab')
        browser.get('https://m.hak.hr/stanje.asp?id=11')


    # Dohvati prometnu prognozu
        try:

            #Potvrdi kolačiće ako postoje
            try:
                kolacic = browser.find_element(By.XPATH, '/html/body/div[3]/div/div/a[2]').click()
            except NoSuchElementException:
                pass
           
            # Dohvati detaljan opis prognoze
            prognoza_text = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body'))).text

            prognoza_naslov = re.search(r'Prometna prognoza za Hrvatsku.*?godine', prognoza_text, re.DOTALL).group().strip()
            prognoza_opis = re.search(r'Na cestama.*?(?=Hrvatski autoklub|$)', prognoza_text, re.DOTALL).group().strip()

            # Pripremi poruke za slanje
            wap_poruka = f"*{prognoza_naslov}:*\n\n{prognoza_opis}"
            tg_poruka = f"🌤️ *{prognoza_naslov}* 🌤️\n\n📝 {prognoza_opis}"

            # Vrati se na Whatsapp tab
            time.sleep(1)
            browser.close()
            browser.switch_to.window(original_window)

            # Pošalji poruku
            posalji_poruku(wap_poruka, tg_poruka)
            with open('poruke/hak_obavijesti.txt', 'a+') as hak:
                hak.write(f"Za datum {datetime.date.today().strftime('%d.%m.%Y.')} postoji prognoza, poruka poslana!\n")

            

        except Exception as e:
            # Zabilježi pogrešku
            with open('errors.txt', 'a') as errors_file:
                errors_file.write(f"Greška za datum {datetime.date.today().strftime('%d.%m.%Y.')}: {e}\n")
            print(f"Došlo je do greške: {e}")
            browser.close()
            browser.switch_to.window(original_window)

def dohvati_i_posalji_poruke():
    # Iteriranje kroz sve grupe
    for group in groups:

        # Pretraživanje grupe
        try:
            search_box = WebDriverWait(browser, 30).until(EC.presence_of_element_located(
                (By.XPATH,
                 '//div[@class="x1hx0egp x6ikm8r x1odjw0f x6prxxf x1k6rcq7 x1whj5v" and @contenteditable="true" and @role="textbox"]')))
            search_box.clear()
        except TimeoutException:
            pass
        time.sleep(1)
        [search_box.send_keys(g) for g in group]
        group_title = WebDriverWait(browser, 20).until(EC.presence_of_element_located(
            (By.XPATH, f'//span[@title="{group}"]')))
        group_title.click()

        # Pronalaženje svih poruka u grupi
        poruke = WebDriverWait(browser, 30).until(EC.presence_of_all_elements_located(
            (By.XPATH, "//span[@dir='ltr'][@class='_ao3e selectable-text copyable-text']/span")))

        # Izdvajanje zadnje poruke ako postoji
        if poruke:
            zadnja_poruka = poruke[-1].text.strip()
        else:
            zadnja_poruka = None

        # Provjera je li poruka nova
        nova_poruka = True
        # Ucitaj dosadasnje poruke iz svih grupa
        for grup in groups:
            group_file_path = f'poruke/{grup}.txt'
            if os.path.exists(group_file_path):
                # Čitanje svih linija iz datoteke za grupu
                with open(group_file_path, 'r', encoding='utf8') as file:
                    lines = file.readlines()
                # Provjera jesu li poruke jednake zadnjoj poruci
                for line in lines:
                    slicnost_poruka = pyjellyfish.jaro_similarity(zadnja_poruka.lower(), line.strip().lower()) * 100
                    if line.strip().lower() == zadnja_poruka.lower():
                        nova_poruka = False
                        with open('errors.txt', 'a+') as error_file:
                            error_file.write(f"Vrijeme: {datetime.datetime.now()}\n")
                            error_file.write(f"Poruka: '{zadnja_poruka}' je ista kao: '{line.strip()}'\n")
                            error_file.write("-------------------------\n")
                        break
                    # Ako je slicnost stare i nove poruke veca od 60%, smatraj poruku starom
                    elif slicnost_poruka > 60:
                        nova_poruka = False
                        with open('errors.txt', 'a+') as error_file:
                            error_file.write(f"Vrijeme: {datetime.datetime.now()}\n")
                            error_file.write(f"Poruka: '{zadnja_poruka}' je slicna kao: '{line.strip()}' sa {slicnost_poruka}% slicnosti\n")
                            error_file.write("-------------------------\n")
                        break

        # Provjeri jel poruka sadrzi bezvezne informacije
        for preskoci_poruku in preskoci_poruke:
            slicnost_poruka = pyjellyfish.jaro_similarity(zadnja_poruka.lower(), preskoci_poruku.lower().strip()) * 100
            if slicnost_poruka > 80:
                nova_poruka = False
                with open('errors.txt', 'a+') as error_file:
                    error_file.write(f"Vrijeme: {datetime.datetime.now()}\n")
                    error_file.write(f"Poruka: '{zadnja_poruka}' sadrzi nepotrebnu poruku: '{preskoci_poruku}' sa {slicnost_poruka}% slicnosti\n")
                    error_file.write("-------------------------\n")
                break

        ocisti_search = WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[3]/div/div[1]/div/div[2]/span/button')))
        ocisti_search.click()

        # Ako je poruka nova, dodaj je u datoteku i pošalji
        if nova_poruka:
            with open(f'poruke/{group}.txt', 'a', encoding='utf8') as file:
                if zadnja_poruka is not None:
                    # Zapisivanje poruke u njezinu datoteku
                    file.write(zadnja_poruka + '\n')

                    # Zapisivanje poruke u logove
                    with open('logovi.txt', 'a+') as log_file:
                        log_file.write(f"Vrijeme: {datetime.datetime.now()}\n")
                        log_file.write(f"Poruka: {zadnja_poruka}\n")
                        log_file.write("-------------------------\n")

                    # Provjeri u koju kategoriju spada poruka
                    wap_poruka = None
                    tg_poruka = None
                    for rijec in zadnja_poruka.lower().split():
                        for test in policija:
                            omjer = difflib.SequenceMatcher(None, test, rijec).ratio() * 100
                            if omjer >= 80:
                                wap_poruka = f'*Policija*\n{zadnja_poruka}'
                                tg_poruka = f"👮 *Policija* 👮 \n{zadnja_poruka}"
                                break

                        for test in radari:
                            omjer = difflib.SequenceMatcher(None, test, rijec).ratio() * 100
                            if omjer >= 80:
                                wap_poruka = f"*Radar*\n{zadnja_poruka}"
                                tg_poruka = f"🎥 *Radar* 🎥 \n{zadnja_poruka}"
                                break

                        for test in sudar:
                            omjer = difflib.SequenceMatcher(None, test, rijec).ratio() * 100
                            if omjer >= 80 and rijec != 'prometa':
                                wap_poruka = f"*Prometna nesreća*\n{zadnja_poruka}"
                                tg_poruka = f"💥 *Prometna nesreća* 💥 \n{zadnja_poruka}"
                                break

                        for test in vaga:
                            omjer = difflib.SequenceMatcher(None, test, rijec).ratio() * 100
                            if omjer >= 80:
                                wap_poruka = f"*Vaga*\n {zadnja_poruka}"
                                tg_poruka = f"🚚 *Vaga* 🚚 \n{zadnja_poruka}"
                                break
                    if wap_poruka is None:
                        wap_poruka = zadnja_poruka
                    if tg_poruka is None:
                        tg_poruka = zadnja_poruka
                    time.sleep(2)

                    posalji_poruku(wap_poruka, tg_poruka)

start()                   
#Pokretanje glavne funkcije za inicijalizaciju web preglednika i Whatsapp-a
schedule.every(2).days.at("00:00").do(start)
#Pokretanje funkcije za dohvaćanje prometne prognoze svakih 24 sata
schedule.every().day.at("07:00").do(provjeri_prometnu_prognozu)
# Pokretanje funkcije za brisanje starih poruka svakih sat vremena
schedule.every().hour.do(obrisi_stare_poruke)
# Pokretanje funkcije za provjeru policijskih akcija svakih 24 sata
schedule.every().day.at("23:59").do(provjeri_policijske_akcije)
# Pokretanje funkcije za dohvacanje i slanje poruka
schedule.every().minute.do(dohvati_i_posalji_poruke)
# Glavna petlja
while True:
    # Provjera i izvršavanje zakazanih zadataka
    schedule.run_pending()
    time.sleep(1)

