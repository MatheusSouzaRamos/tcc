#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>


#define SS_PIN 26
#define RST_PIN 27



const char* ssid = "mattt";
const char* password = "matheus123";

//const char* ssid = "Ap202";
//const char* password = "05032022";



const char* servidor =
    "http://10.124.64.77:5000/api/rfid";


// ==============================
// OBJETO RFID
// ==============================

MFRC522 rfid(SS_PIN, RST_PIN);


// ==============================
// CONEXÃO WI-FI
// ==============================

void conectarWiFi() {

  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println();
  Serial.println("Conectando ao Wi-Fi...");

  WiFi.begin(ssid, password);

  int tentativas = 0;

  while (
    WiFi.status() != WL_CONNECTED &&
    tentativas < 30
  ) {

    delay(500);

    Serial.print(".");

    tentativas++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println("Wi-Fi conectado!");

    Serial.print("IP da ESP32: ");
    Serial.println(WiFi.localIP());

  } else {

    Serial.println(
        "Não foi possível conectar ao Wi-Fi."
    );
  }
}


// ==============================
// ENVIA UID PARA O FLASK
// ==============================

void enviarUID(String uid) {

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println();
    Serial.println(
        "Wi-Fi desconectado."
    );

    conectarWiFi();
  }

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println(
        "Não foi possível enviar o UID."
    );

    return;
  }


  HTTPClient http;

  Serial.println();
  Serial.println(
      "Conectando ao servidor..."
  );

  http.begin(servidor);

  http.addHeader(
      "Content-Type",
      "application/json"
  );


  // ==============================
  // MONTA JSON
  // ==============================

  String json =
      "{\"uid\":\"" + uid + "\"}";


  Serial.println();
  Serial.println("Enviando UID:");
  Serial.println(json);


  // ==============================
  // ENVIA POST
  // ==============================

  int codigoHTTP =
      http.POST(json);


  Serial.print(
      "Código HTTP: "
  );

  Serial.println(codigoHTTP);


  // ==============================
  // PROCESSA RESPOSTA
  // ==============================

  if (codigoHTTP > 0) {

    String resposta =
        http.getString();


    Serial.println();
    Serial.println(
        "Resposta do servidor:"
    );

    Serial.println(resposta);


    JsonDocument documento;

    DeserializationError erro =
        deserializeJson(
            documento,
            resposta
        );


    if (erro) {

      Serial.println();
      Serial.println(
          "Erro ao interpretar JSON."
      );

      http.end();

      return;
    }


    // ==============================
    // DADOS DA RESPOSTA
    // ==============================

    const char* status =
        documento["status"];

    const char* mensagem =
        documento["mensagem"];

    const char* professor =
        documento["professor"];

    const char* turma =
        documento["turma"];

    const char* acao =
        documento["acao"];


    // ==============================
    // ERRO DA API
    // ==============================

    if (
        status != nullptr &&
        strcmp(status, "erro") == 0
    ) {

      Serial.println();
      Serial.println(
          "===== ERRO ====="
      );

      if (mensagem != nullptr) {

        Serial.print(
            "Mensagem: "
        );

        Serial.println(
            mensagem
        );
      }

      Serial.println(
          "================"
      );

      http.end();

      return;
    }


    // ==============================
    // AULA INICIADA
    // ==============================

    if (
        acao != nullptr &&
        strcmp(acao, "abrir") == 0
    ) {

      Serial.println();
      Serial.println(
          "=============================="
      );

      Serial.println(
          "       AULA INICIADA"
      );

      Serial.println(
          "=============================="
      );

      if (professor != nullptr) {

        Serial.print(
            "Professor: "
        );

        Serial.println(
            professor
        );
      }

      if (turma != nullptr) {

        Serial.print(
            "Turma: "
        );

        Serial.println(
            turma
        );
      }

      Serial.println(
          "Reconhecimento facial iniciado."
      );

      Serial.println(
          "=============================="
      );
    }


    // ==============================
    // AULA ENCERRADA
    // ==============================

    else if (
        acao != nullptr &&
        strcmp(acao, "fechar") == 0
    ) {

      Serial.println();
      Serial.println(
          "=============================="
      );

      Serial.println(
          "       AULA ENCERRADA"
      );

      Serial.println(
          "=============================="
      );

      if (professor != nullptr) {

        Serial.print(
            "Professor: "
        );

        Serial.println(
            professor
        );
      }

      if (turma != nullptr) {

        Serial.print(
            "Turma: "
        );

        Serial.println(
            turma
        );
      }

      Serial.println(
          "=============================="
      );
    }
  }


  // ==============================
  // ERRO HTTP
  // ==============================

  else {

    Serial.println();
    Serial.println(
        "Erro na comunicação HTTP."
    );

    Serial.print(
        "Detalhes: "
    );

    Serial.println(
        http.errorToString(
            codigoHTTP
        )
    );
  }


  http.end();
}


// ==============================
// CONFIGURAÇÃO INICIAL
// ==============================

void setup() {

  Serial.begin(115200);

  delay(1000);


  Serial.println();
  Serial.println(
      "================================="
  );

  Serial.println(
      " Sistema de Controle de Presença "
  );

  Serial.println(
      "================================="
  );


  // ==============================
  // WI-FI
  // ==============================

  conectarWiFi();


  // ==============================
  // SERVIDOR
  // ==============================

  Serial.println();

  Serial.print(
      "Servidor: "
  );

  Serial.println(
      servidor
  );


  // ==============================
  // SPI
  // ==============================

  SPI.begin(
      14,  // SCK
      12,  // MISO
      13,  // MOSI
      26   // SS
  );


  // ==============================
  // RFID
  // ==============================

  rfid.PCD_Init();

  delay(100);


  Serial.println();

  Serial.println(
      "RFID inicializado."
  );

  Serial.println(
      "Aproxime o cartão..."
  );

  Serial.println(
      "================================="
  );
}


// ==============================
// LOOP PRINCIPAL
// ==============================

void loop() {

  // ==============================
  // VERIFICA WI-FI
  // ==============================

  if (
      WiFi.status() != WL_CONNECTED
  ) {

    conectarWiFi();
  }


  // ==============================
  // VERIFICA NOVO CARTÃO
  // ==============================

  if (
      !rfid.PICC_IsNewCardPresent()
  ) {

    return;
  }


  if (
      !rfid.PICC_ReadCardSerial()
  ) {

    return;
  }


  // ==============================
  // MONTA UID
  // ==============================

  String uid = "";


  Serial.println();

  Serial.println(
      "Cartão detectado!"
  );

  Serial.print(
      "UID: "
  );


  for (
      byte i = 0;
      i < rfid.uid.size;
      i++
  ) {

    if (
        rfid.uid.uidByte[i] < 0x10
    ) {

      uid += "0";
    }


    uid += String(
        rfid.uid.uidByte[i],
        HEX
    );


    if (
        i < rfid.uid.size - 1
    ) {

      Serial.print(" ");
    }
  }


  uid.toUpperCase();


  Serial.println();

  Serial.print(
      "UID enviado: "
  );

  Serial.println(
      uid
  );


  // ==============================
  // ENVIA PARA O SERVIDOR
  // ==============================

  enviarUID(uid);


  Serial.println();

  Serial.println(
      "--------------------------------"
  );


  // ==============================
  // FINALIZA LEITURA
  // ==============================

  rfid.PICC_HaltA();

  rfid.PCD_StopCrypto1();


  // ==============================
  // EVITA LEITURA DUPLICADA
  // ==============================

  delay(1500);
}