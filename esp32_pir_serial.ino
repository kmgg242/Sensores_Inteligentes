const int pirPin = 27;          // Pino conectado ao OUT do sensor PIR
const int ledPin = 2;           // LED onboard do ESP32

int estadoAnterior = LOW;       // Guarda o estado anterior do sensor
unsigned long lastTrigger = 0;
const unsigned long cooldown = 5000; // 5 segundos de intervalo mínimo entre fotos

void setup() {
  Serial.begin(115200);
  
  // INPUT_PULLDOWN força o pino a ficar em 0V (LOW) quando o sensor não manda sinal
  pinMode(pirPin, INPUT_PULLDOWN);
  pinMode(ledPin, OUTPUT);
  
  Serial.println("Calibrando sensor PIR (aguarde 10s sem se mexer)...");
  delay(10000);
  Serial.println("SISTEMA_PRONTO");
}

void loop() {
  int estadoAtual = digitalRead(pirPin);

  // Só dispara na BORDA DE SUBIDA (quando muda de LOW para HIGH)
  if (estadoAtual == HIGH && estadoAnterior == LOW) {
    unsigned long agora = millis();
    
    if (agora - lastTrigger > cooldown) {
      digitalWrite(ledPin, HIGH);
      Serial.println("TRIGGER_MOVIMENTO");
      lastTrigger = agora;
    }
  } 
  
  // Quando o sensor volta para LOW, apaga o LED do ESP32
  if (estadoAtual == LOW && estadoAnterior == HIGH) {
    digitalWrite(ledPin, LOW);
    Serial.println("STATUS: Sensor voltou para repouso (LOW)");
  }

  estadoAnterior = estadoAtual;
}
