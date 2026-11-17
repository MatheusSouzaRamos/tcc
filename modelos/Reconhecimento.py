import cv2
import numpy as np


# ==========================================
# RECONHECER PESSOAS
# ==========================================

def reconhecer_pessoas(
    frame,
    dados,
    detector,
    recognizer,
    limiar
):

    pessoas_reconhecidas = []


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
        faces is None
        or len(faces) == 0
    ):

        return pessoas_reconhecidas


    # ======================================
    # PROCESSAR CADA ROSTO
    # ======================================

    for face in faces:

        try:

            # ==================================
            # ALINHAR ROSTO
            # ==================================

            aligned_face = (
                recognizer.alignCrop(
                    frame,
                    face
                )
            )


            # ==================================
            # GERAR EMBEDDING
            # ==================================

            embedding = recognizer.feature(
                aligned_face
            )

            embedding = (
                embedding.flatten()
            )


            # ==================================
            # NORMALIZAR
            # ==================================

            norma = np.linalg.norm(
                embedding
            )


            if norma == 0:
                continue


            embedding = (
                embedding / norma
            )


            # ==================================
            # PROCURAR MELHOR PESSOA
            # ==================================

            melhor_aluno_id = None

            melhor_nome = (
                "Desconhecido"
            )

            melhor_similaridade = -1


            for _, cadastro in dados.items():

                aluno_id = cadastro.get(
                    "aluno_id"
                )

                nome = cadastro.get(
                    "nome"
                )

                embeddings_cadastrados = (
                    cadastro.get(
                        "embeddings",
                        []
                    )
                )


                # Cadastro antigo/inválido
                if (
                    aluno_id is None
                    or nome is None
                ):
                    continue


                melhor_da_pessoa = -1


                # ==================================
                # COMPARAR EMBEDDINGS
                # ==================================

                for embedding_cadastrado in (
                    embeddings_cadastrados
                ):

                    embedding_cadastrado = (
                        np.array(
                            embedding_cadastrado,
                            dtype=np.float32
                        )
                    )

                    embedding_cadastrado = (
                        embedding_cadastrado.reshape(
                            1,
                            -1
                        )
                    )


                    similaridade = (
                        recognizer.match(
                            embedding.reshape(
                                1,
                                -1
                            ),
                            embedding_cadastrado,
                            cv2.FaceRecognizerSF_FR_COSINE
                        )
                    )


                    if (
                        similaridade
                        > melhor_da_pessoa
                    ):

                        melhor_da_pessoa = (
                            similaridade
                        )


                # ==================================
                # MELHOR CADASTRO
                # ==================================

                if (
                    melhor_da_pessoa
                    > melhor_similaridade
                ):

                    melhor_similaridade = (
                        melhor_da_pessoa
                    )

                    melhor_aluno_id = (
                        aluno_id
                    )

                    melhor_nome = nome


            # ==================================
            # RESULTADO
            # ==================================

            if (
                melhor_similaridade
                >= limiar
                and melhor_aluno_id
                is not None
            ):

                pessoa = {
                    "aluno_id":
                        melhor_aluno_id,

                    "nome":
                        melhor_nome,

                    "similaridade":
                        float(
                            melhor_similaridade
                        ),

                    "face":
                        face
                }


            else:

                pessoa = {
                    "aluno_id": None,

                    "nome":
                        "Desconhecido",

                    "similaridade":
                        float(
                            melhor_similaridade
                        ),

                    "face":
                        face
                }


            pessoas_reconhecidas.append(
                pessoa
            )


        except Exception as erro:

            print(
                "Erro no reconhecimento:",
                erro
            )


    # ======================================
    # RETORNAR RESULTADOS
    # ======================================

    return pessoas_reconhecidas