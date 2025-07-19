#include <SPI.h>
#include <MFRC522.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
#include <Arduino.h>


#define SS_PIN 5
#define RST_PIN 15
#define BUZZER_PIN 2
#define RELAY_PIN 14

MFRC522 rfid(SS_PIN, RST_PIN);


String data = "";
String kode_rfid = "kosong";
String last_rfid = "";
int timer_display = 0;
int status_serial = 0;



void debug(String message, int row = 0, int clear = 1) {
  //Serial.println(message);
  //tampilkan jika menggunakan lcd
  if (clear == 1) {
    lcd.clear();
  }
  lcd.setCursor(0, row);
  lcd.print(message);
}



void lcd_i2c(String text = "", int kolom = 0, int baris = 0, int clear = 1) {
  byte bar[8] = {
    B11111,
    B11111,
    B11111,
    B11111,
    B11111,
    B11111,
    B11111,
  };
  if (text == "") {
    lcd.init();  //jika error pakai lcd.init();
    lcd.backlight();
    lcd.createChar(0, bar);
    lcd.setCursor(0, 0);
    lcd.print("Loading..");
    for (int i = 0; i < 16; i++) {
      lcd.setCursor(i, 1);
      lcd.write(byte(0));
      delay(100);
    }
    delay(50);
    lcd.clear();
  } else {
    if (clear == 1) {
      lcd.clear();
    }
    lcd.setCursor(kolom, baris);
    lcd.print(text + "                ");
  }
}



void setup() {
  Serial.begin(9600);
  lcd_i2c();
  SPI.begin();
  rfid.PCD_Init();

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  bunyikanBuzzer();
  buka_pintu();
  delay(1000);
  tutup_pintu();


  debug("AKTIF");
}




void cekSerialInput() {

  if (Serial.available()) {
    data = Serial.readStringUntil('\n');
    status_serial = 1;
  }

  if (millis() - timer_display > 5000) {
    if (status_serial == 1) {
      debug("Terhubung");
    }
  }

  if (data.indexOf('#') != -1) {
    // Serial.println("Karakter ! ditemukan.");
    data.remove(0, 1);
    debug(data);
    data = "";
    buka_pintu();
    delay(3000);
    tutup_pintu();
  }


  if (data.indexOf('!') != -1) {
    // Serial.println("Karakter ! ditemukan.");
    data = "";
    bunyikanBuzzer();
    buka_pintu();
    delay(3000);
    tutup_pintu();

  } else if (data.indexOf('@') != -1) {
    // Serial.println("Karakter @ ditemukan.");

    data.remove(0, 1);

    debug(data);
    if (data == "Tidak Terdaftar") {
      bunyikanBuzzerPanjang();
    }
    if (data == "Kamera Aktif") {
      bunyikanBuzzer();
      delay(100);
      bunyikanBuzzer();
      delay(100);
      bunyikanBuzzer();
    }
    timer_display = millis();
    data = "";
  }
}


void cekKartuRFID() {
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    // Ambil UID
    String uidStr = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      if (rfid.uid.uidByte[i] < 0x10) uidStr += "0";
      uidStr += String(rfid.uid.uidByte[i], HEX);
    }
    uidStr.toUpperCase();

    // Cek apakah kartu baru (berbeda dari sebelumnya)
    if (uidStr != last_rfid) {
      last_rfid = uidStr;
      kode_rfid = uidStr;
      Serial.println(kode_rfid);  // kirim hanya sekali
      debug("ID:" + kode_rfid);
      timer_display = millis();
    }


    // Matikan komunikasi dengan kartu
    // rfid.PICC_HaltA();
    // rfid.PCD_StopCrypto1();
  }
  // Reset UID jika kartu sudah diangkat
  else if (!rfid.PICC_IsNewCardPresent()) {
    last_rfid = "";
  }
}



void buka_pintu() {

  digitalWrite(RELAY_PIN, LOW);  // Relay ON (buka pintu)
  //Serial.println("Pintu terbuka 🚪🔓");
  delay(100);
  SPI.begin();
  rfid.PCD_Init();
}

void tutup_pintu() {

  digitalWrite(RELAY_PIN, HIGH);
  // Serial.println("Pintu tertutup 🚪🔓");
  delay(100);
  SPI.begin();
  rfid.PCD_Init();
}

void bunyikanBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(300);
  digitalWrite(BUZZER_PIN, LOW);
}

void bunyikanBuzzerPanjang() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(3000);
  digitalWrite(BUZZER_PIN, LOW);
}


void loop() {
  cekKartuRFID();
  cekSerialInput();  // Baca perintah dari Serial
}
