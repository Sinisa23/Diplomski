import cv2
from pyzbar import pyzbar
from bson import ObjectId
import pymongo
import time
import paho.mqtt.client as mqtt

# Povezivanje na MongoDB Atlas
atlas_connection_uri = "mongodb+srv://sinisastojic98:jBz65C7XRNg3eYZQ@cluster0.okw9vqn.mongodb.net/"
client = pymongo.MongoClient(atlas_connection_uri)
db = client["inventar"]
kolekcija_knjige = db["knjige"]

cap = cv2.VideoCapture(0)
cap.set(3, 440)  # Širina prozora
cap.set(4, 280)  # Visina prozora

# Postavljanje promjenljive za praćenje
poslednje_vrijeme_citanja = time.time()
VRIJEME_OBNOVE = 1.5  # Vrijeme u sekundama nakon kojeg će se ponovo omogućiti čitanje istog koda

# Podešavanje MQTT parametara
mqtt_broker = "192.168.1.103"  # Unesite IP adresu ili domenu svog MQTT brokera
mqtt_port = 1883
mqtt_topic_knjige = "knjige"

# Podešavanje Paho MQTT klijenta
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Povezan s MQTT brokerom. Kod povratka:", rc)

# Povezivanje na MQTT broker prilikom pokretanja
mqtt_client.on_connect = on_connect
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

def posalji_na_mqtt(knjiga):
    mqtt_client.publish(mqtt_topic_knjige, knjiga)

def process_code(decoded_data):
    global poslednje_vrijeme_citanja
    # Provjera da li je dekodirani podatak validan ObjectId
    if ObjectId.is_valid(decoded_data) and time.time() - poslednje_vrijeme_citanja > VRIJEME_OBNOVE:
        # Traženje knjige u MongoDB kolekciji
        knjiga = kolekcija_knjige.find_one({"_id": ObjectId(decoded_data)})

        if knjiga:
            print(decoded_data)
            
            # Slanje podataka na MQTT temu
            posalji_na_mqtt(f"{decoded_data}")
        else:
            print("Kod nije pronađen u bazi podataka.")

        # Ažuriranje vremena posljednjeg čitanja
        poslednje_vrijeme_citanja = time.time()

kamera = True
while kamera:
    success, frame = cap.read()

    try:
        # Dekodiranje QR koda
        qr_codes = pyzbar.decode(frame)

        for code in qr_codes:
            process_code(code.data.decode('utf-8')) # Funkcija koja pretvara bajtove u string, s obzirom da dekodirani podaci mogu biti u bajt formatu

    except Exception as e:
        # Ne ispisuj ništa prilikom greške
        pass

    cv2.imshow('Testiranje-kodova', frame)
    key = cv2.waitKey(1)

# Zatvaranje kamere nakon završetka
cap.release()
cv2.destroyAllWindows()
