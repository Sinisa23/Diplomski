#include <WiFi.h>
#include <PubSubClient.h>
#include <MFRC522Constants.h>
#include <MFRC522DriverPin.h>
#include <MFRC522DriverPinSimple.h>
#include <MFRC522DriverSPI.h>
#include <MFRC522Hack.h>
#include <MFRC522v2.h>
#include <deprecated.h>
#include <require_cpp11.h>

MFRC522DriverPinSimple ss_pin(5);
MFRC522DriverSPI driver{ss_pin}; // Kreiraj driver za rfid senzor preko SPI
MFRC522 mfrc522{driver};         // Instanca drajvera

// Wifi podaci
const char* ssid = "Bojana";
const char* password = "12345678";

// MQTT podaci
const char* mqtt_server = "192.168.1.103";
const int mqtt_port = 1883;

WiFiClient espClient; // Kreiranje instance WiFi klijenta pod nazivom espClient
PubSubClient client(espClient); // Inicijalizacija MQTT klijenta

void setup() {
  Serial.begin(115200); // Postavlja brzinu serijske komunikacije na 115200 bps
  while (!Serial); // Ceka dok se serijska veza ne uspostavi

  // Inicijalizacija RFID citaca kartica
  mfrc522.PCD_Init(); // PCD_Init je metoda koja se koristi za pocetnu konfiguraciju i inicijalizaciju citaca. Nakon toga, RFID citac je spreman za ocitavanje podataka s RFID kartica.

  // Povezivanje na WiFi mrežu
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }

  mqttSetup();  // Dodaj poziv funkcije za MQTT setup
  // Povezivanje na MQTT broker
  reconnect();
}
// Callback funkcija koja se poziva kada stigne poruka na MQTT temu
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Poruka na temi: ");
  Serial.print(topic);
  Serial.print(". Poruka: ");
  for (int i = 0; i < length; i++) {  // Petlja koja prolazi kroz sve bajtove primljene poruke. Svaki bajt koji se interpretira kao karakter i prikazuje se kao dio poruke.
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

// Funkcija za podesavanje MQTT klijenta
void mqttSetup() {
  // Povezivanje na MQTT broker
  client.setServer(mqtt_server, mqtt_port);
}

// Ponovno povezivanje na MQTT broker ako veza nije uspostavljena
void reconnect() {
  while (!client.connected()) {
    String clientId = "esp32-" + WiFi.macAddress();
    
    if (client.connect(clientId.c_str())) {
      Serial.println("Povezan na MQTT broker!");
      // Pretplata na temu knjige
    } else {
      Serial.println("Neuspjelo povezivanje. Pokušavam ponovno za 5 sekundi... ");
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(5000);
    }
  }
}

void loop() {
  String tagContent = "";

  // Provjera da li je prisutan novi RFID tag
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Citanje serijskog broja RFID taga
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Prolazi kroz svaki bajt serijskog broja RFID taga
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    tagContent.concat(String(mfrc522.uid.uidByte[i], HEX)); // Dodaje svaki bajt u string 
  }

  tagContent.toUpperCase(); // Pretvaranje stringa u velika slova

  // Slanje poruke na MQTT broker
  if (client.connected()) {
    client.publish("knjige", tagContent.c_str()); // Slanje poruke na temu knjige
    Serial.println("knjige," + tagContent);  // Ispis poruke na serijskom monitoru
  }

  delay(1000); // Pauza od 1 sekunde

  // Provjera da li je MQTT klijent i dalje povezan
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // Odrzavanje veze s MQTT brokerom
}