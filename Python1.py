import tkinter as tk
from tkinter import ttk
from pymongo import MongoClient
from datetime import datetime
import paho.mqtt.client as mqtt
import tkinter.messagebox as messagebox
from bson import ObjectId
import bson

class InventarApp:
    def __init__(self, root): #Definise konstruktor klase sa jednim parametrom koji ce biti koriscen za inicijalizaciju odredjenih clanova klase

        # Inicijalizacija prozora
        self.root = root
        self.root.title("Sistem za upravljanje zalihama")

        # Promjenljiva za cuvanje broja kartice
        self.broj_kartice_var = None

        # Povezivanje na MongoDB bazu podataka
        atlas_uri = "mongodb+srv://sinisastojic98:jBz65C7XRNg3eYZQ@cluster0.okw9vqn.mongodb.net/"
        self.client = MongoClient(atlas_uri)
        self.db = self.client["inventar"]
        self.knjige_collection = self.db["knjige"]

        # Kreiranje Treeview-a za prikazivanje tabele knjiga
        columns = ("Broj Kartice", "Naziv", "Autor", "Cijena", "Stanje", "Min.Kolicina", "Datum izmjene", "Lokacija")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")

        # Postavljanje sirine za svaku kolonu
        column_widths = (100, 150, 100, 80, 80, 100, 150, 100)
        for col, width in zip(columns, column_widths):
            self.tree.column(col, width=width, anchor=tk.CENTER)
            self.tree.heading(col, text=col)

        self.tree.pack(pady=10)

        # Dugmad za dodavanje i brisanje knjiga
        remove_button = tk.Button(root, text="Obrisi Knjigu", command=self.ukloni_knjigu)
        remove_button.pack(side=tk.LEFT, padx=10)

        # Polje za pretragu
        self.search_entry = tk.Entry(root, width=20)
        self.search_entry.pack(side=tk.RIGHT, padx=10)
        search_button = tk.Button(root, text="Pretraga", command=self.pretraga_knjiga)
        search_button.pack(side=tk.RIGHT, padx=10)

        # Dodavanje boje redovima
        self.tree.tag_configure("oddrow", background="#f0f0f0")
        self.tree.tag_configure("evenrow", background="#ffffff")

        # Popunjavanje tabele sa podacima iz baze podataka
        self.popuni_tabelu()
        
        # Dodavanje funkcionalnosti pretrage pritiskom na Enter
        self.search_entry.bind("<Return>", self.pretraga_knjiga_enter)

        # MQTT konfiguracija
        self.mqtt_broker = "192.168.1.103"  # Postavljanje IP adrese MQTT brokera
        self.mqtt_port = 1883
        self.mqtt_topic = "knjige"  # Postavljanje teme

        # Postavljanje promjenljive za pracenje prvog citanja
        self.prvo_citanje = True

        # MQTT klijent
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message

        # Povezivanje na MQTT broker
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)

        # Pretlati se na odredjenu temu
        self.mqtt_client.subscribe(self.mqtt_topic)

        # Pokretanje petlje za osluskivanje poruka
        self.mqtt_client.loop_start()

    def popuni_tabelu(self):
        # Uzimanje podataka iz baze i njihovo prikazivanje u tabeli
        self.tree.delete(*self.tree.get_children())  # Ocisti trenutne podatke u tabeli
        knjige = self.knjige_collection.find()
        for i, knjiga in enumerate(knjige):
            data = (
                knjiga.get("Broj_Kartice", ""),
                knjiga.get("naziv", ""),
                knjiga.get("autor", ""),
                knjiga.get("cijena", ""),
                knjiga.get("stanje", ""),
                knjiga.get("minKolicina", ""),
                knjiga.get("datumIzmjene", ""),
                knjiga.get("lokacija", "")
            )
            tags = ("evenrow", "oddrow")[i % 2 == 1]  # Odredjivanje boje reda
            self.tree.insert("", tk.END, values=data, tags=tags)

    def ukloni_knjigu(self):
        # Implementacija funkcionalnosti za uklanjanje selektovane knjige iz baze
        selected_item = self.tree.selection()
        if selected_item:
            card_number = self.tree.item(selected_item, "values")[0]
            self.knjige_collection.delete_one({"Broj_Kartice": card_number})
            
            # Osvjezi prikaz tabele
            self.popuni_tabelu()

    # Funkcija za pretragu knjiga po nazivu ili autoru
    def pretraga_knjiga(self):
        # Dobijanje unosa korisnika iz Entry polja za pretragu
        query = self.search_entry.get()
        # Brisanje svih trenutnih edova u Treeview komponenti kako bi se osvjezili rezultati pretrage
        self.tree.delete(*self.tree.get_children())
        knjige = self.knjige_collection.find({
            "$or": [  # Operator za pretragu po vise polja (naziv i autor)
                {"naziv": {"$regex": query, "$options": "i"}},  # $regex se koristi za fleksibilnu pretragu sa opcijom "i" koja znaci da se ne razlikuje izmedju velikih i malih slova
                {"autor": {"$regex": query, "$options": "i"}}
            ]
        })
        # Iteracija kroz rezultate pretrage i dodavanje novih redova u Treeview
        for i, knjiga in enumerate(knjige):
            data = (
                knjiga.get("Broj_Kartice", ""),
                knjiga.get("naziv", ""),
                knjiga.get("autor", ""),
                knjiga.get("cijena", ""),
                knjiga.get("stanje", ""),
                knjiga.get("minKolicina", ""),
                knjiga.get("datumIzmjene", ""),
                knjiga.get("lokacija", "")
            )

            # Postavljanje tagova za redove kako bi se postigao efekat razlicitih boja pozadine
            tags = ("evenrow", "oddrow")[i % 2 == 1]
            # Dodavanje novog reda sa podacima u Treeview
            self.tree.insert("", tk.END, values=data, tags=tags)

    # Funkcija za pretragu knjiga po nazivu ili autoru kada korisnik pritisne Enter
    def pretraga_knjiga_enter(self, event):
        self.pretraga_knjiga()

    # Funkcija koja se poziva prilikom primanja poruke preko MQTT-a
    def on_message(self, client, userdata, msg):
        # Dekodiranje payload-a poruke i formatiranje broja kartice
        card_number = msg.payload.decode('utf-8').rstrip('\n')
        formatted_card_number = card_number.replace(" ", "").upper().strip()  # Razdijeli string

        # Pretraga knjige po broju kartice u kolekciji
        knjiga_po_kartici = self.knjige_collection.find_one({"Broj_Kartice": formatted_card_number})

        # Ako je knjiga pronadjena po broju kartice, prikazi prozor za azuriranje
        if knjiga_po_kartici:
            self.prikazi_prozor_za_azuriranje(formatted_card_number)
        else:
            # Ako knjiga nije pronadjena po broju kartice, pokusaj pronaci po ObjectID
            knjiga_po_objectid = self.pronadji_knjigu_po_objectid(formatted_card_number)

            # Ako je knjiga pronadjena po ObjectID, prikazi prozor za azuriranje
            if knjiga_po_objectid:
                self.prikazi_prozor_za_azuriranje(str(knjiga_po_objectid["_id"]))
            else:
                dodaj_knjigu = messagebox.askquestion("UPOZORENJE", "Kartica ne postoji! Da li zelite da je dodate?")

                # Ako korisnik zeli dodati knjigu, pozovi funkciju za dodavanje nove knjige 
                if dodaj_knjigu == 'yes':
                    self.prozor_dodaj_knjigu(formatted_card_number)
                else:
                    pass

    # Funkcija za pronalazenje knjige po ObjectID               
    def pronadji_knjigu_po_objectid(self, object_id):
        try:
            # Pokusaj konvertovati string u ObjectID
            objectId= ObjectId(object_id)
            # Pronadji knjigu u kolekciji po ObjectID
            knjiga = self.knjige_collection.find_one({"_id":objectId})
            return knjiga
        except bson.errors.InvalidId:
            return None

    # Funkcija za prikazivanje prozora za azuriranje stanja knjige 
    def prikazi_prozor_za_azuriranje(self, card_number):
        azuriraj_knjigu = tk.Toplevel(self.root)
        azuriraj_knjigu.title("Ažuriranje Knjige")

        tk.Label(azuriraj_knjigu, text=f"Ažuriranje knjige sa brojem kartice ili ObjectID: {card_number}").pack()

        tk.Button(azuriraj_knjigu, text="Dodaj Knjigu", command=lambda: self.azuriraj_stanje(card_number, "dodaj", azuriraj_knjigu)).pack()
        tk.Button(azuriraj_knjigu, text="Oduzmi Knjigu", command=lambda: self.azuriraj_stanje(card_number, "oduzmi", azuriraj_knjigu)).pack()

    # Funkcija za azuriranje stanja knjige (povecanje ili smanjenje stanja)
    def azuriraj_stanje(self, identifikator, operacija, dialog):
        knjiga = None

        try:
            # Provera da li je identifikator ObjectId
            objectId = ObjectId(identifikator)
            knjiga = self.knjige_collection.find_one({"_id": objectId})
        except:
            # Ako nije ObjectId, pretpostavi da je broj kartice
            knjiga = self.knjige_collection.find_one({"Broj_Kartice": identifikator})

        if not knjiga:
            dodaj_knjigu = messagebox.askquestion("UPOZORENJE", "Kartica ne postoji! Da li zelite da je dodate?")

            if dodaj_knjigu =='yes':
                self.prozor_dodaj_knjigu(identifikator)
            else:
                pass
            return

        # Izracunaj novo stanje knjige 
        nova_kolicina = knjiga.get('stanje', 0) - 1 if operacija == "oduzmi" else knjiga.get('stanje', 0) + 1

        if operacija == "oduzmi" and nova_kolicina <= 0:
            messagebox.showerror("Upozorenje", "Nema više knjiga na stanju!")
            return

        if operacija == "oduzmi" and nova_kolicina <= knjiga.get('minKolicina', 0):
            messagebox.showwarning("Upozorenje", f"Stanje knjige je ispod minimalne količine, naruči još knjiga!")

        if nova_kolicina < 0:
            nova_kolicina = 0  # Obezbjedi da stanje ne može biti negativno

        # Azuriraj bazu podataka sa novim stanjem i datumom izmjene
        self.knjige_collection.update_one(
            {"_id": knjiga["_id"]},
            {
                "$set": {
                    "stanje": nova_kolicina,
                    "datumIzmjene": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            }
        )

        self.popuni_tabelu()

        dialog.destroy()  # Zatvori dijalog prozor

    # Funkcija za prikazivanje prozora za dodavanje nove knjige
    def prozor_dodaj_knjigu(self, broj_kartice):
        self.broj_kartice_var = tk.StringVar(value=broj_kartice)
        self.add_book_window = tk.Toplevel(self.root)
        self.add_book_window.title("Dodaj Knjigu")

        tk.Label(self.add_book_window, text="Broj Kartice:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
        tk.Entry(self.add_book_window, textvariable=self.broj_kartice_var, state='readonly').grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Naziv:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)
        self.naziv_entry = tk.Entry(self.add_book_window)
        self.naziv_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Autor:").grid(row=2, column=0, padx=10, pady=5, sticky=tk.E)
        self.autor_entry = tk.Entry(self.add_book_window)
        self.autor_entry.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Cijena:").grid(row=3, column=0, padx=10, pady=5, sticky=tk.E)
        self.cijena_entry = tk.Entry(self.add_book_window)
        self.cijena_entry.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Stanje:").grid(row=4, column=0, padx=10, pady=5, sticky=tk.E)
        self.stanje_entry = tk.Entry(self.add_book_window)
        self.stanje_entry.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Min. Kolicina:").grid(row=5, column=0, padx=10, pady=5, sticky=tk.E)
        self.min_kolicina_entry = tk.Entry(self.add_book_window)
        self.min_kolicina_entry.grid(row=5, column=1, padx=10, pady=5)

        datum_izmjene = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        tk.Label(self.add_book_window, text="Datum izmjene:").grid(row=6, column=0, padx=10, pady=5, sticky=tk.E)
        datum_izmjene_entry = tk.Entry(self.add_book_window, state='readonly', textvariable=tk.StringVar(value=datum_izmjene))
        datum_izmjene_entry.grid(row=6, column=1, padx=10, pady=5)

        tk.Label(self.add_book_window, text="Lokacija:").grid(row=7, column=0, padx=10, pady=5, sticky=tk.E)
        self.lokacija_entry = tk.Entry(self.add_book_window)
        self.lokacija_entry.grid(row=7, column=1, padx=10, pady=5)

        button_frame = tk.Frame(self.add_book_window)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)

        tk.Button(button_frame, text="Dodaj Knjigu", command=self.dodaj_knjigu).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Zatvori", command=self.add_book_window.destroy).grid(row=0, column=1, padx=5)

    # Funkcija za dodavanje nove knjige ili azuriranje postojece
    def dodaj_knjigu(self):
        broj_kartice = self.broj_kartice_var.get()
        naziv = self.naziv_entry.get()
        autor = self.autor_entry.get()
        cijena = float(self.cijena_entry.get()) if self.cijena_entry.get() else 0.0
        stanje = int(self.stanje_entry.get()) if self.stanje_entry.get() else 0
        min_kolicina = int(self.min_kolicina_entry.get()) if self.min_kolicina_entry.get() else 0
        datum_izmjene = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        lokacija = self.lokacija_entry.get()

        # Provjeri da li knjiga vec postoji u bazi podataka
        knjiga = self.knjige_collection.find_one({"Broj_Kartice": broj_kartice})

        # Ako knjiga vec postoji, azuriraj je
        if knjiga:
            self. knjige_collection.update_one(
                {"Broj_Kartice": broj_kartice},
                {
                    "$set":{
                        "naziv": naziv,
                        "autor": autor,
                        "cijena": cijena,
                        "stanje": stanje,
                        "minKolicina": min_kolicina,
                        "datumIzmjene": datum_izmjene,
                        "lokacija": lokacija
                    }
                }
            )
        else:
            # Ako knjiga ne postoji, dodaj je u bazu podataka
            self.knjige_collection.insert_one({
                "Broj_Kartice": broj_kartice,
                "naziv": naziv,
                "autor": autor,
                "cijena": cijena,
                "stanje": stanje,
                "minKolicina": min_kolicina,
                "datumIzmjene": datum_izmjene,
                "lokacija": lokacija
        })

        self.add_book_window.destroy()  # Zatvori prozor za dodavanje knjige
        self.popuni_tabelu()  # Osvjezi prikaz tabele

    # Funkcija za azuriranje reda u tabeli nakon izmjene podataka
    def azuriraj_red_tabele(self, broj_kartice, broj_kartice_value, naziv_value, autor_value, cijena_value, stanje_value, min_kolicina_value, datum_izmjene_value, lokacija_value):
        item_id = None

        # Pronadji ID reda u tabeli na osnovu broja kartice
        for item in self.tree.get_children():
            # Provjera da li prva vrijednost (broj_kartice) u trenutnom redu odgovara trazenom broju kartice
            if self.tree.item(item, "values")[0] == broj_kartice:
                item_id = item
                break

        # Ako je pronadjen ID, azuriraj vrijednosti u tom redu
        if item_id:
            # Pripremi podatke za azuriranje u redu
            data = (broj_kartice_value, naziv_value, autor_value, cijena_value, stanje_value, min_kolicina_value, datum_izmjene_value, lokacija_value)
            self.tree.item(item_id, values=data)  # Postavi nove vrijednosti u odgovarajuci red u tabeli

    # Funkcija za pokretanje glavne petlje
    def run(self):
        self.root.mainloop()

# Blok koda koji se izvrsava samo ako je ovaj fajl pokrenut kao glavni program
if __name__ == "__main__":
    root = tk.Tk()
    app = InventarApp(root)
    app.run()
