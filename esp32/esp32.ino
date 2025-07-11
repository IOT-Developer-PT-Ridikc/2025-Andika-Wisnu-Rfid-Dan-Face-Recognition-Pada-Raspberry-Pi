#include <Arduino.h>

#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
#include <ESP32_Servo.h>

int relay = 26;
Servo servoESP32;
int port_servoESP32 = 27;
int port_sensor_pir = 14;

String data = "";




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

void relay_on() {
  //Aktif low, dibalik jadi High jika terbalik
  digitalWrite(relay, LOW);
  lcd.init();  //jika error pakai lcd.init();
  lcd.backlight();
}
void relay_off() {
  digitalWrite(relay, HIGH);
  lcd.init();  //jika error pakai lcd.init();
  lcd.backlight();
}
void posisi_servoESP32(int posisi) {
  servoESP32.write(posisi);
}
int baca_sensor_pir() {
  return digitalRead(port_sensor_pir);
}

void buka_pintu(String nama) {
  relay_on();
  debug(nama);
  debug("Terdeteksi ", 1, 0);
  Serial.println("relay ON");
  delay(1000);
  posisi_servoESP32(90);
}

void tutup_pintu() {
  debug("Mengunci ..  ", 1, 0);
  posisi_servoESP32(0);
  delay(1000);
  relay_off();
  Serial.println("relay Off");
}

void setup() {
  Serial.begin(9600);
  lcd_i2c();
  pinMode(relay, OUTPUT);
  relay_off();
  servoESP32.attach(port_servoESP32);
  
  pinMode(port_sensor_pir, INPUT);
  relay_on();
  delay(1000);
  relay_off();
  posisi_servoESP32(90);
  delay(1000);
  posisi_servoESP32(0);
}



void loop() {


  int sensor_pir = baca_sensor_pir();
  debug("Aktif .. ");


  if (Serial.available()) {
    data = Serial.readStringUntil('\n');
    debug("Terhubung");
  }

  if (data == "get_sensor") {
    delay(100);
    Serial.println((String)sensor_pir);
    data = "";
  }

  if (data.indexOf('@') != -1) {
    Serial.println("Karakter ditemukan.");
    data.remove(0, 1);
    buka_pintu(data);
    delay(3000);
    tutup_pintu();
  }

  delay(100);
}
