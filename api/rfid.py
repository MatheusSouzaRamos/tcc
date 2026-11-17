import os
import sys
import subprocess

from flask import Blueprint, request, jsonify
from banco.conexao import conectar


rfid_bp = Blueprint("rfid", __name__)


def iniciar_reconhecimento_facial():

    pasta_projeto = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    arquivo_presenca = os.path.join(
        pasta_projeto,
        "TCC.-Hash-facial",
        "Presenca.py"
    )

    try:

        subprocess.Popen(
            [
                sys.executable,
                "-u",
                arquivo_presenca
            ],
            cwd=pasta_projeto,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        print()
        print(
            "Reconhecimento facial iniciado."
        )

    except Exception as erro:

        print(
            "Erro ao iniciar "
            "reconhecimento facial:"
        )

        print(erro)


def buscar_aula_aberta():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            aulas.id AS aula_id,
            aulas.professor_id,
            professores.nome AS professor,
            aulas.turma_id,
            turmas.nome AS turma,
            turmas.curso,
            aulas.acao
        FROM aulas
        INNER JOIN professores
            ON aulas.professor_id = professores.id
        INNER JOIN turmas
            ON aulas.turma_id = turmas.id
        ORDER BY aulas.id DESC
        LIMIT 1
    """)

    aula = cursor.fetchone()

    cursor.close()
    conexao.close()

    if aula is None:
        return None

    if aula["acao"] == "fechar":
        return None

    return aula


def buscar_turma_do_professor(professor_id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            turmas.id AS turma_id,
            turmas.nome AS turma,
            turmas.curso
        FROM professor_turma
        INNER JOIN turmas
            ON professor_turma.turma_id = turmas.id
        WHERE professor_turma.professor_id = %s
        ORDER BY turmas.nome
    """, (professor_id,))

    turmas = cursor.fetchall()

    cursor.close()
    conexao.close()

    return turmas


def buscar_alunos_da_turma(turma_id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            alunos.id,
            alunos.nome
        FROM aluno_turma
        INNER JOIN alunos
            ON aluno_turma.aluno_id = alunos.id
        WHERE aluno_turma.turma_id = %s
          AND alunos.ativo = TRUE
        ORDER BY alunos.nome
    """, (turma_id,))

    alunos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return alunos


def registrar_presenca(aluno_id, aula_id):

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute("""
            INSERT INTO presencas (
                aluno_id,
                aula_id,
                status
            )
            VALUES (
                %s,
                %s,
                'presente'
            )
        """, (
            aluno_id,
            aula_id
        ))

        conexao.commit()

        return True, "Presença registrada com sucesso"

    except Exception as erro:

        conexao.rollback()

        if "Duplicate entry" in str(erro):

            return (
                False,
                "Aluno já possui presença nesta aula"
            )

        return False, str(erro)

    finally:

        cursor.close()
        conexao.close()


@rfid_bp.route(
    "/aula-aberta",
    methods=["GET"]
)
def aula_aberta():

    aula = buscar_aula_aberta()

    if aula is None:

        return jsonify({
            "status": "ok",
            "aula_aberta": False,
            "mensagem": "Nenhuma aula aberta"
        })

    return jsonify({
        "status": "ok",
        "aula_aberta": True,
        "aula_id": aula["aula_id"],
        "professor": aula["professor"],
        "turma_id": aula["turma_id"],
        "turma": aula["turma"],
        "curso": aula["curso"]
    })


@rfid_bp.route(
    "/alunos-turma/<int:turma_id>",
    methods=["GET"]
)
def alunos_turma(turma_id):

    alunos = buscar_alunos_da_turma(
        turma_id
    )

    return jsonify({
        "status": "ok",
        "turma_id": turma_id,
        "quantidade": len(alunos),
        "alunos": alunos
    })


@rfid_bp.route(
    "/rfid",
    methods=["POST"]
)
def receber_cartao():

    dados = request.get_json()

    if not dados:

        return jsonify({
            "status": "erro",
            "mensagem": "JSON não informado"
        }), 400

    uid = dados.get("uid")

    if not uid:

        return jsonify({
            "status": "erro",
            "mensagem": "UID não informado"
        }), 400

    uid = uid.strip().upper()

    print()
    print("==========================")
    print("UID recebido:", uid)

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT *
            FROM professores
            WHERE uid = %s
            """,
            (uid,)
        )

        professor = cursor.fetchone()

        if professor is None:

            print("Cartão não cadastrado!")
            print("==========================")
            print()

            return jsonify({
                "status": "erro",
                "mensagem": "Cartão não cadastrado"
            }), 404

        print(
            "Professor:",
            professor["nome"]
        )

        turmas = buscar_turma_do_professor(
            professor["id"]
        )

        if not turmas:

            print(
                "Professor não possui turma associada."
            )

            print("==========================")
            print()

            return jsonify({
                "status": "erro",
                "mensagem":
                    "Professor não possui turma associada"
            }), 400

        if len(turmas) > 1:

            print(
                "Professor possui mais de uma turma associada."
            )

            print("==========================")
            print()

            return jsonify({
                "status": "erro",
                "mensagem":
                    "Professor possui mais de uma turma associada"
            }), 400

        turma = turmas[0]

        turma_id = turma["turma_id"]

        print(
            "Turma:",
            turma["turma"]
        )

        cursor.execute("""
            SELECT *
            FROM aulas
            ORDER BY id DESC
            LIMIT 1
        """)

        ultima_aula = cursor.fetchone()

        if (
            ultima_aula is None
            or ultima_aula["acao"] == "fechar"
        ):

            acao = "abrir"

            cursor.execute("""
                INSERT INTO aulas (
                    professor_id,
                    turma_id,
                    acao
                )
                VALUES (
                    %s,
                    %s,
                    %s
                )
            """, (
                professor["id"],
                turma_id,
                acao
            ))

            conexao.commit()

            aula_id = cursor.lastrowid

            iniciar_reconhecimento_facial()

            print()
            print(
                "===== AULA INICIADA ====="
            )

            print(
                "Professor:",
                professor["nome"]
            )

            print(
                "Turma:",
                turma["turma"]
            )

            print(
                "Aula ID:",
                aula_id
            )

        else:

            if (
                ultima_aula["professor_id"]
                != professor["id"]
            ):

                print(
                    "Aula já está aberta!"
                )

                print(
                    "Professor responsável:",
                    ultima_aula["professor_id"]
                )

                print(
                    "Professor que tentou acessar:",
                    professor["id"]
                )

                print(
                    "=========================="
                )

                print()

                return jsonify({
                    "status": "erro",
                    "mensagem":
                        "Já existe uma aula aberta por outro professor"
                }), 403

            acao = "fechar"

            cursor.execute("""
                INSERT INTO aulas (
                    professor_id,
                    turma_id,
                    acao
                )
                VALUES (
                    %s,
                    %s,
                    %s
                )
            """, (
                professor["id"],
                ultima_aula["turma_id"],
                acao
            ))

            conexao.commit()

            print()
            print(
                "===== AULA ENCERRADA ====="
            )

            print(
                "Professor:",
                professor["nome"]
            )

            print(
                "Turma:",
                turma["turma"]
            )

    except Exception as erro:

        conexao.rollback()

        print(
            "Erro ao processar RFID:",
            erro
        )

        return jsonify({
            "status": "erro",
            "mensagem":
                f"Erro ao processar RFID: {erro}"
        }), 500

    finally:

        cursor.close()
        conexao.close()

    print(
        "=========================="
    )

    print()

    return jsonify({
        "status": "ok",
        "professor": professor["nome"],
        "turma_id": turma_id,
        "turma": turma["turma"],
        "acao": acao
    })


@rfid_bp.route(
    "/registrar-presenca",
    methods=["POST"]
)
def registrar_presenca_rota():

    dados = request.get_json()

    if not dados:

        return jsonify({
            "status": "erro",
            "mensagem": "JSON não informado"
        }), 400

    aluno_id = dados.get("aluno_id")

    if aluno_id is None:

        return jsonify({
            "status": "erro",
            "mensagem": "aluno_id não informado"
        }), 400

    aula = buscar_aula_aberta()

    if aula is None:

        return jsonify({
            "status": "erro",
            "mensagem": "Nenhuma aula está aberta"
        }), 400

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                alunos.id,
                alunos.nome
            FROM aluno_turma
            INNER JOIN alunos
                ON aluno_turma.aluno_id = alunos.id
            WHERE aluno_turma.aluno_id = %s
              AND aluno_turma.turma_id = %s
              AND alunos.ativo = TRUE
        """, (
            aluno_id,
            aula["turma_id"]
        ))

        aluno = cursor.fetchone()

    finally:

        cursor.close()
        conexao.close()

    if aluno is None:

        return jsonify({
            "status": "erro",
            "mensagem":
                "Aluno não pertence à turma desta aula"
        }), 403

    sucesso, mensagem = registrar_presenca(
        aluno_id,
        aula["aula_id"]
    )

    if not sucesso:

        return jsonify({
            "status": "erro",
            "mensagem": mensagem
        }), 409

    return jsonify({
        "status": "ok",
        "mensagem": "Presença registrada",
        "aluno": aluno["nome"],
        "professor": aula["professor"],
        "turma": aula["turma"],
        "aula_id": aula["aula_id"]
    })


@rfid_bp.route(
    "/registrar-presencas-finais",
    methods=["POST"]
)
def registrar_presencas_finais():

    dados = request.get_json()

    if not dados:

        return jsonify({
            "status": "erro",
            "mensagem": "JSON não informado"
        }), 400

    aula_id = dados.get(
        "aula_id"
    )

    resultados = dados.get(
        "resultados"
    )

    if aula_id is None:

        return jsonify({
            "status": "erro",
            "mensagem": "aula_id não informado"
        }), 400

    if resultados is None:

        return jsonify({
            "status": "erro",
            "mensagem": "resultados não informados"
        }), 400

    conexao = conectar()

    cursor = conexao.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            aulas.id,
            aulas.professor_id,
            aulas.turma_id,
            professores.nome AS professor,
            turmas.nome AS turma
        FROM aulas
        INNER JOIN professores
            ON aulas.professor_id = professores.id
        INNER JOIN turmas
            ON aulas.turma_id = turmas.id
        WHERE aulas.id = %s
          AND aulas.acao = 'abrir'
        """,
        (aula_id,)
    )

    aula = cursor.fetchone()

    if aula is None:

        cursor.close()
        conexao.close()

        return jsonify({
            "status": "erro",
            "mensagem": "Aula não encontrada"
        }), 404

    registros = []

    try:

        for resultado in resultados:

            aluno_id = resultado.get(
                "aluno_id"
            )

            percentual = float(
                resultado.get(
                    "percentual",
                    0
                )
            )

            if aluno_id is None:
                continue

            if percentual >= 70:

                status = "presente"

            else:

                status = "ausente"

            cursor.execute(
                """
                SELECT
                    alunos.id,
                    alunos.nome
                FROM aluno_turma
                INNER JOIN alunos
                    ON aluno_turma.aluno_id = alunos.id
                WHERE alunos.id = %s
                  AND aluno_turma.turma_id = %s
                  AND alunos.ativo = TRUE
                """,
                (
                    aluno_id,
                    aula["turma_id"]
                )
            )

            aluno = cursor.fetchone()

            if aluno is None:
                continue

            cursor.execute(
                """
                INSERT INTO presencas (
                    aluno_id,
                    aula_id,
                    percentual_presenca,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    percentual_presenca =
                        VALUES(percentual_presenca),
                    status =
                        VALUES(status)
                """,
                (
                    aluno_id,
                    aula_id,
                    percentual,
                    status
                )
            )

            registros.append({
                "aluno_id": aluno_id,
                "aluno": aluno["nome"],
                "percentual": round(
                    percentual,
                    2
                ),
                "status": status
            })

        conexao.commit()

    except Exception as erro:

        conexao.rollback()

        cursor.close()
        conexao.close()

        return jsonify({
            "status": "erro",
            "mensagem": str(erro)
        }), 500

    cursor.close()
    conexao.close()

    return jsonify({
        "status": "ok",
        "mensagem":
            "Presenças finais registradas",
        "aula_id": aula_id,
        "professor": aula["professor"],
        "turma": aula["turma"],
        "resultados": registros
    })


@rfid_bp.route(
    "/presencas-aula/<int:aula_id>",
    methods=["GET"]
)
def presencas_aula(aula_id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                alunos.id AS aluno_id,
                alunos.nome AS aluno,
                presencas.percentual_presenca,
                presencas.status
            FROM presencas
            INNER JOIN alunos
                ON presencas.aluno_id = alunos.id
            WHERE presencas.aula_id = %s
            ORDER BY alunos.nome
        """, (aula_id,))

        presencas = cursor.fetchall()

        return jsonify({
            "status": "ok",
            "aula_id": aula_id,
            "quantidade": len(presencas),
            "presencas": presencas
        })

    except Exception as erro:

        return jsonify({
            "status": "erro",
            "mensagem": str(erro)
        }), 500

    finally:

        cursor.close()
        conexao.close()