import cv2
import numpy as np
import json
import os
import time
import sys


# ==========================================
# CAMINHOS DO PROJETO
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PASTA_SERVIDOR = os.path.dirname(BASE_DIR)

if PASTA_SERVIDOR not in sys.path:
    sys.path.append(PASTA_SERVIDOR)


# ==========================================
# BANCO DE DADOS
# ==========================================

from banco.conexao import conectar


# ==========================================
# CONFIGURAÇÕES
# ==========================================

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

TOTAL_AMOSTRAS = 50

INTERVALO_CAPTURA = 0.5


# ==========================================
# INFORMAR ALUNO
# ==========================================

try:
    ALUNO_ID = int(
        input(
            "ID do aluno no banco: "
        ).strip()
    )

except ValueError:

    print(
        "\nERRO: informe um ID numérico."
    )

    exit()


# ==========================================
# BUSCAR ALUNO NO BANCO
# ==========================================

conexao = conectar()

cursor = conexao.cursor(
    dictionary=True
)

cursor.execute(
    """
    SELECT
        id,
        nome,
        ativo
    FROM alunos
    WHERE id = %s
    """,
    (ALUNO_ID,)
)

aluno = cursor.fetchone()

cursor.close()

conexao.close()


if aluno is None:

    print(
        "\nERRO: aluno não encontrado."
    )

    exit()


if not aluno["ativo"]:

    print(
        "\nERRO: aluno está inativo."
    )

    exit()


NOME = aluno["nome"]


print()
print(
    f"Aluno encontrado: "
    f"{NOME}"
)


# ==========================================
# VERIFICAR MODELOS
# ==========================================

if not os.path.exists(
    MODELO_YUNET
):

    print(
        "\nERRO: modelo YuNet "
        "não encontrado:"
    )

    print(
        MODELO_YUNET
    )

    exit()


if not os.path.exists(
    MODELO_SFACE
):

    print(
        "\nERRO: modelo SFace "
        "não encontrado:"
    )

    print(
        MODELO_SFACE
    )

    exit()


# ==========================================
# CARREGAR YUNET
# ==========================================

detector = cv2.FaceDetectorYN.create(
    MODELO_YUNET,
    "",
    (640, 480),
    0.9,
    0.3,
    5000
)


# ==========================================
# CARREGAR SFACE
# ==========================================

recognizer = cv2.FaceRecognizerSF.create(
    MODELO_SFACE,
    ""
)


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
# VARIÁVEIS
# ==========================================

embeddings = []

ultimo_tempo = 0


# ==========================================
# INFORMAÇÕES
# ==========================================

print()
print(
    "======================================"
)

print(
    "          CADASTRO FACIAL"
)

print(
    "======================================"
)

print(
    f"ID: {ALUNO_ID}"
)

print(
    f"Aluno: {NOME}"
)

print(
    f"Amostras: "
    f"0/{TOTAL_AMOSTRAS}"
)

print()
print(
    "Durante o cadastro:"
)

print(
    "- Olhe para frente"
)

print(
    "- Vire levemente para a esquerda"
)

print(
    "- Vire levemente para a direita"
)

print(
    "- Incline levemente a cabeça para baixo"
)

print(
    "- Incline levemente a cabeça para cima"
)

print()
print(
    "Pressione Q para cancelar."
)

print()


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


    # ======================================
    # DETECTAR ROSTOS
    # ======================================

    detector.setInputSize(
        (640, 480)
    )

    _, faces = detector.detect(
        frame
    )


    if (
        faces is not None
        and len(faces) > 0
    ):

        # ==================================
        # PEGAR MAIOR ROSTO
        # ==================================

        faces = sorted(
            faces,
            key=lambda f: f[2] * f[3],
            reverse=True
        )

        face = faces[0]

        x = int(face[0])
        y = int(face[1])
        w = int(face[2])
        h = int(face[3])


        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )


        agora = time.time()


        if (
            agora - ultimo_tempo
            >= INTERVALO_CAPTURA
            and len(embeddings)
            < TOTAL_AMOSTRAS
        ):

            try:

                aligned_face = (
                    recognizer.alignCrop(
                        frame,
                        face
                    )
                )

                embedding = (
                    recognizer.feature(
                        aligned_face
                    )
                )

                embedding = (
                    embedding.flatten()
                )

                norma = np.linalg.norm(
                    embedding
                )


                if norma > 0:

                    embedding = (
                        embedding / norma
                    )

                    embeddings.append(
                        embedding.tolist()
                    )

                    ultimo_tempo = agora

                    print(
                        f"Amostra capturada: "
                        f"{len(embeddings)}/"
                        f"{TOTAL_AMOSTRAS}"
                    )


            except Exception as erro:

                print(
                    "Erro ao gerar embedding:",
                    erro
                )


    # ======================================
    # INFORMAÇÕES NA TELA
    # ======================================

    cv2.putText(
        frame,
        (
            f"Amostras: "
            f"{len(embeddings)}/"
            f"{TOTAL_AMOSTRAS}"
        ),
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )


    cv2.putText(
        frame,
        "Movimente levemente a cabeca",
        (10, 460),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "Cadastro Facial",
        frame
    )


    tecla = (
        cv2.waitKey(1)
        & 0xFF
    )


    if tecla == ord("q"):
        break


    if (
        len(embeddings)
        >= TOTAL_AMOSTRAS
    ):
        break


# ==========================================
# ENCERRAR CÂMERA
# ==========================================

cap.release()

cv2.destroyAllWindows()


# ==========================================
# VERIFICAR AMOSTRAS
# ==========================================

if len(embeddings) == 0:

    print(
        "\nNenhuma amostra "
        "foi capturada."
    )

    exit()


# ==========================================
# CARREGAR JSON
# ==========================================

dados = {}


if os.path.exists(
    ARQUIVO_JSON
):

    try:

        with open(
            ARQUIVO_JSON,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

    except json.JSONDecodeError:

        print(
            "\nJSON inválido."
        )

        dados = {}


# ==========================================
# SALVAR EMBEDDINGS
# ==========================================

chave = str(ALUNO_ID)


dados[chave] = {
    "aluno_id": ALUNO_ID,
    "nome": NOME,
    "embeddings": embeddings
}


# ==========================================
# GRAVAR JSON
# ==========================================

with open(
    ARQUIVO_JSON,
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        dados,
        arquivo,
        indent=4,
        ensure_ascii=False
    )


# ==========================================
# RESULTADO
# ==========================================

print()
print(
    "======================================"
)

print(
    "        CADASTRO CONCLUÍDO"
)

print(
    "======================================"
)

print(
    f"ID do aluno: {ALUNO_ID}"
)

print(
    f"Aluno: {NOME}"
)

print(
    f"Amostras armazenadas: "
    f"{len(embeddings)}"
)

print(
    f"Arquivo: {ARQUIVO_JSON}"
)

print()
print(
    "Nenhuma imagem foi salva."
)

print(
    "Somente os embeddings "
    "faciais foram armazenados."
)