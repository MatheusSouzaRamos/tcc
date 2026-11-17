import cv2
import json
import os
import time
import requests

from Reconhecimento import reconhecer_pessoas


# ==========================================
# CONFIGURAÇÕES
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ARQUIVO_JSON = os.path.join(
    BASE_DIR,
    "faces.json"
)

MODELO_YUNET = os.path.join(
    BASE_DIR,
    "face_detection_yunet_2023mar.onnx"
)

MODELO_SFACE = os.path.join(
    BASE_DIR,
    "face_recognition_sface_2021dec.onnx"
)


SERVIDOR = (
    "http://10.124.64.77:5000"
)


URL_AULA_ABERTA = (
    f"{SERVIDOR}/api/aula-aberta"
)


URL_PRESENCAS_FINAIS = (
    f"{SERVIDOR}"
    "/api/registrar-presencas-finais"
)

URL_ALUNOS_TURMA = (
    f"{SERVIDOR}"
    "/api/alunos-turma"
)

INTERVALO_CAPTURA = 3

INTERVALO_CONSULTA_AULA = 2

LIMIAR = 0.40

PERCENTUAL_MINIMO = 70


# ==========================================
# VERIFICAR ARQUIVOS
# ==========================================

for caminho in [
    ARQUIVO_JSON,
    MODELO_YUNET,
    MODELO_SFACE
]:

    if not os.path.exists(
        caminho
    ):

        print(
            "\nERRO: arquivo não encontrado:"
        )

        print(
            caminho
        )

        exit()


# ==========================================
# CARREGAR CADASTROS
# ==========================================

with open(
    ARQUIVO_JSON,
    "r",
    encoding="utf-8"
) as arquivo:

    dados = json.load(
        arquivo
    )


if len(dados) == 0:

    print(
        "Nenhum aluno "
        "cadastrado."
    )

    exit()


# ==========================================
# IDENTIFICAR CADASTROS FACIAIS
# ==========================================

alunos_com_face = set()

for _, cadastro in dados.items():
    aluno_id = cadastro.get(
        "aluno_id"
    )

    if aluno_id is None:
        continue

    embeddings = cadastro.get(
        "embeddings",
        []
    )

    if len(embeddings) > 0:
        alunos_com_face.add(
            int(aluno_id)
        )

# ==========================================
# MODELOS
# ==========================================

detector = cv2.FaceDetectorYN.create(
    MODELO_YUNET,
    "",
    (640, 480),
    0.9,
    0.3,
    5000
)


recognizer = cv2.FaceRecognizerSF.create(
    MODELO_SFACE,
    ""
)


# ==========================================
# CONSULTAR AULA
# ==========================================

def consultar_aula():

    try:

        resposta = requests.get(
            URL_AULA_ABERTA,
            timeout=3
        )

        if resposta.status_code != 200:

            return None


        return resposta.json()


    except requests.RequestException:

        return None

#==========================================
# BUSCAR_ALUNOS
#==========================================

def buscar_alunos_turma(turma_id):
    try:
        resposta = requests.get(
            f"{URL_ALUNOS_TURMA}/{turma_id}",
            timeout=5
        )

        if resposta.status_code != 200:
            print("Erro ao buscar alunos da turma.")
            print(resposta.text)
            return []

        dados = resposta.json()

        return dados.get("alunos", [])

    except Exception as erro:
        print(f"Erro ao consultar alunos da turma: {erro}")
        return []

# ==========================================
# AGUARDAR AULA
# ==========================================

print()
print(
    "======================================"
)

print(
    "       CONTROLE DE PRESENÇA"
)

print(
    "======================================"
)

print()
print(
    "Aguardando professor abrir "
    "a aula pelo RFID..."
)

print()


aula = None


while True:

    resposta = consultar_aula()


    if (
        resposta
        and resposta.get(
            "aula_aberta"
        )
    ):

        aula = resposta
        break


    time.sleep(
        INTERVALO_CONSULTA_AULA
    )


# ==========================================
# DADOS DA AULA
# ==========================================

aula_id = aula["aula_id"]

turma_id = aula["turma_id"]

professor = aula["professor"]

turma = aula["turma"]

#===========================================
#CONSULTAR FLASK/MYSQL
#===========================================

alunos_turma = buscar_alunos_turma(turma_id)

if not alunos_turma:
    print("Nenhum aluno encontrado para esta turma.")
    exit()

contadores = {}

for aluno in alunos_turma:
    aluno_id = int(aluno["id"])

    contadores[aluno_id] = {
        "nome": aluno["nome"],
        "capturas": 0,
        "cadastro_facial": aluno_id in alunos_com_face
    }



for aluno_id, dados_aluno in contadores.items():
    print(
        f"ID {aluno_id} - {dados_aluno['nome']}"
    )

#===========================================
print()
print(
    "======================================"
)

print(
    "           AULA INICIADA"
)

print(
    "======================================"
)

print(
    f"Aula ID: {aula_id}"
)

print(
    f"Professor: {professor}"
)

print(
    f"Turma: {turma}"
)

print(
    f"Critério: "
    f"{PERCENTUAL_MINIMO}%"
)

print()


# ==========================================
# CÂMERA
# ==========================================

cap = cv2.VideoCapture(
    0,
    cv2.CAP_DSHOW
)


if not cap.isOpened():

    print(
        "Erro ao abrir a câmera."
    )

    exit()


# ==========================================
# VARIÁVEIS DA AULA
# ==========================================

inicio_aula = time.time()

ultima_captura = inicio_aula

ultima_consulta = inicio_aula

total_capturas = 0

aula_encerrada = False


# ==========================================
# LOOP
# ==========================================

while True:

    ret, frame = cap.read()


    if not ret:

        print(
            "Erro ao capturar imagem."
        )

        break


    frame = cv2.flip(
        frame,
        1
    )

    frame = cv2.resize(
        frame,
        (640, 480)
    )


    agora = time.time()


    # ======================================
    # CONSULTAR SE A AULA CONTINUA ABERTA
    # ======================================

    if (
        agora - ultima_consulta
        >= INTERVALO_CONSULTA_AULA
    ):

        ultima_consulta = agora

        resposta_aula = (
            consultar_aula()
        )


        if (
            resposta_aula
            and not resposta_aula.get(
                "aula_aberta",
                False
            )
        ):

            print()
            print(
                "Aula encerrada pelo RFID."
            )

            aula_encerrada = True

            break


    # ======================================
    # CAPTURA A CADA 3 SEGUNDOS
    # ======================================

    if (
        agora - ultima_captura
        >= INTERVALO_CAPTURA
    ):

        ultima_captura = agora

        total_capturas += 1


        resultados = (
            reconhecer_pessoas(
                frame,
                dados,
                detector,
                recognizer,
                LIMIAR
            )
        )


        presentes_agora = set()


        # ==================================
        # PROCESSAR RESULTADOS
        # ==================================

        for resultado in resultados:

            aluno_id = resultado.get(
                "aluno_id"
            )

            nome = resultado["nome"]

            similaridade = (
                resultado["similaridade"]
            )

            face = resultado["face"]


            x = int(
                face[0]
            )

            y = int(
                face[1]
            )

            w = int(
                face[2]
            )

            h = int(
                face[3]
            )


            # ==================================
            # RECONHECIDO
            # ==================================

            if (
                aluno_id is not None
                and nome
                != "Desconhecido"
            ):

                aluno_id = int(
                    aluno_id
                )

                presentes_agora.add(
                    aluno_id
                )


                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    frame,
                    (
                        f"{nome} "
                        f"{similaridade:.2f}"
                    ),
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )


            # ==================================
            # DESCONHECIDO
            # ==================================

            else:

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 0, 255),
                    2
                )


                cv2.putText(
                    frame,
                    (
                        "Desconhecido "
                        f"{similaridade:.2f}"
                    ),
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2
                )


        # ==================================
        # CONTABILIZAR
        # ==================================

        for aluno_id in (
            presentes_agora
        ):

            if aluno_id in contadores:

                contadores[
                    aluno_id
                ]["capturas"] += 1


        # ==================================
        # TERMINAL
        # ==================================

        print(
            f"Captura "
            f"#{total_capturas}"
        )


        if presentes_agora:

            print(
                "Reconhecidos:"
            )


            for aluno_id in (
                presentes_agora
            ):

                if aluno_id in contadores:

                    print(
                        "  - "
                        + contadores[
                            aluno_id
                        ]["nome"]
                    )


        else:

            print(
                "Nenhum aluno "
                "reconhecido."
            )


        print()


    # ======================================
    # TEMPO
    # ======================================

    tempo_aula = (
        agora - inicio_aula
    )

    minutos = int(
        tempo_aula // 60
    )

    segundos = int(
        tempo_aula % 60
    )


    cv2.putText(
        frame,
        (
            f"Tempo: "
            f"{minutos:02d}:"
            f"{segundos:02d}"
        ),
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )


    cv2.putText(
        frame,
        (
            f"Capturas: "
            f"{total_capturas}"
        ),
        (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        "Aguardando encerramento RFID",
        (10, 450),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "Controle de Presenca",
        frame
    )


    # Q apenas para interrupção manual/emergência
    tecla = (
        cv2.waitKey(1)
        & 0xFF
    )


    if tecla == ord("q"):

        print(
            "\nExecução interrompida "
            "manualmente."
        )

        break


# ==========================================
# FINALIZAR CÂMERA
# ==========================================

fim_aula = time.time()

cap.release()

cv2.destroyAllWindows()


# ==========================================
# CALCULAR RESULTADOS
# ==========================================

resultados_finais = []


print()
print(
    "======================================"
)

print(
    "          RESULTADO FINAL"
)

print(
    "======================================"
)

print()


for aluno_id, dados_aluno in (
    contadores.items()
):

    capturas_aluno = dados_aluno[
        "capturas"
    ]

    if total_capturas > 0:
        percentual = (
            capturas_aluno
            / total_capturas
        ) * 100
    else:
        percentual = 0

    if percentual >= PERCENTUAL_MINIMO:
        status = "PRESENTE"
    else:
        status = "AUSENTE"

    # Verificar cadastro facial
    if dados_aluno[
        "cadastro_facial"
    ]:
        cadastro_facial = "SIM"
    else:
        cadastro_facial = "NÃO"

    print(
        dados_aluno["nome"]
    )

    print(
        "  Cadastro facial: "
        f"{cadastro_facial}"
    )

    print(
        "  Capturas: "
        f"{capturas_aluno}/"
        f"{total_capturas}"
    )

    print(
        "  Percentual: "
        f"{percentual:.2f}%"
    )

    print(
        f"  Status: {status}"
    )

    print()

    resultados_finais.append(
        {
            "aluno_id": aluno_id,
            "percentual": round(
                percentual,
                2
            )
        }
    )

# ==========================================
# ENVIAR AO FLASK
# ==========================================

# Só registra automaticamente quando
# o encerramento ocorreu pelo RFID.
if aula_encerrada:

    payload = {
        "aula_id":
            aula_id,

        "resultados":
            resultados_finais
    }


    try:

        resposta = requests.post(
            URL_PRESENCAS_FINAIS,
            json=payload,
            timeout=10
        )


        print(
            "Código HTTP:",
            resposta.status_code
        )

        print(
            "Resposta do servidor:"
        )

        print(
            resposta.text
        )


    except requests.RequestException as erro:

        print(
            "Erro ao enviar "
            "presenças:"
        )

        print(
            erro
        )


else:

    print(
        "Resultados não enviados "
        "porque a execução não foi "
        "finalizada pelo RFID."
    )


print()
print(
    "Controle de presença encerrado."
)