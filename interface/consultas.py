from banco import conectar

def buscar_alunos():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            nome,
            ativo
        FROM alunos
        ORDER BY nome
    """)

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_turmas():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            nome,
            curso
        FROM turmas
        ORDER BY nome
    """)

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_professores():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            nome,
            uid
        FROM professores
        ORDER BY nome
    """)

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_resumo():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM alunos
        WHERE ativo = TRUE
    """)

    alunos = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM aulas
        WHERE acao = 'abrir'
    """)

    aulas = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM presencas
        WHERE status = 'presente'
    """)

    presencas = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM presencas
        WHERE status = 'ausente'
    """)

    faltas = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT
            COALESCE(
                ROUND(AVG(percentual_presenca), 2),
                0
            ) AS media
        FROM presencas
    """)

    media = cursor.fetchone()["media"]

    cursor.close()
    conexao.close()

    return {
        "alunos": alunos,
        "aulas": aulas,
        "presencas": presencas,
        "faltas": faltas,
        "media": float(media)
    }


def buscar_frequencia(
    turma_id=None,
    aluno_id=None,
    professor_id=None
):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    sql = """
        SELECT
            alunos.id AS aluno_id,
            alunos.nome AS aluno,

            COUNT(DISTINCT presencas.aula_id)
                AS aulas,

            SUM(
                CASE
                    WHEN presencas.status = 'presente'
                    THEN 1
                    ELSE 0
                END
            ) AS presencas,

            SUM(
                CASE
                    WHEN presencas.status = 'ausente'
                    THEN 1
                    ELSE 0
                END
            ) AS faltas,

            ROUND(
                AVG(
                    presencas.percentual_presenca
                ),
                2
            ) AS percentual

        FROM presencas

        INNER JOIN alunos
            ON presencas.aluno_id = alunos.id

        INNER JOIN aulas
            ON presencas.aula_id = aulas.id

        INNER JOIN turmas
            ON aulas.turma_id = turmas.id

        INNER JOIN professores
            ON aulas.professor_id = professores.id

        WHERE 1 = 1
    """

    parametros = []

    if turma_id is not None:
        sql += """
            AND turmas.id = %s
        """
        parametros.append(turma_id)

    if aluno_id is not None:
        sql += """
            AND alunos.id = %s
        """
        parametros.append(aluno_id)

    if professor_id is not None:
        sql += """
            AND professores.id = %s
        """
        parametros.append(professor_id)

    sql += """
        GROUP BY
            alunos.id,
            alunos.nome

        ORDER BY
            percentual DESC
    """

    cursor.execute(
        sql,
        parametros
    )

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_historico(
    turma_id=None,
    aluno_id=None,
    professor_id=None
):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    sql = """
        SELECT
            presencas.id,
            alunos.nome AS aluno,
            professores.nome AS professor,
            turmas.nome AS turma,
            presencas.aula_id,
            aulas.data_hora AS aula,
            presencas.percentual_presenca,
            presencas.status

        FROM presencas

        INNER JOIN alunos
            ON presencas.aluno_id = alunos.id

        INNER JOIN aulas
            ON presencas.aula_id = aulas.id

        INNER JOIN professores
            ON aulas.professor_id = professores.id

        INNER JOIN turmas
            ON aulas.turma_id = turmas.id

        WHERE 1 = 1
    """

    parametros = []

    if turma_id is not None:
        sql += """
            AND turmas.id = %s
        """
        parametros.append(turma_id)

    if aluno_id is not None:
        sql += """
            AND alunos.id = %s
        """
        parametros.append(aluno_id)

    if professor_id is not None:
        sql += """
            AND professores.id = %s
        """
        parametros.append(professor_id)

    sql += """
        ORDER BY
            aulas.data_hora DESC,
            alunos.nome
    """

    cursor.execute(
        sql,
        parametros
    )

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_relatorio_aulas(
    turma_id=None,
    professor_id=None
):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    sql = """
        SELECT
            aulas.id AS aula_id,
            turmas.nome AS turma,
            professores.nome AS professor,
            aulas.data_hora,

            COUNT(presencas.id) AS total_alunos,

            SUM(
                CASE
                    WHEN presencas.status = 'presente'
                    THEN 1
                    ELSE 0
                END
            ) AS presentes,

            SUM(
                CASE
                    WHEN presencas.status = 'ausente'
                    THEN 1
                    ELSE 0
                END
            ) AS ausentes,

            ROUND(
                AVG(presencas.percentual_presenca),
                2
            ) AS frequencia_media

        FROM aulas

        INNER JOIN turmas
            ON aulas.turma_id = turmas.id

        INNER JOIN professores
            ON aulas.professor_id = professores.id

        LEFT JOIN presencas
            ON aulas.id = presencas.aula_id

        WHERE aulas.acao = 'abrir'
    """

    parametros = []

    if turma_id is not None:

        sql += """
            AND aulas.turma_id = %s
        """

        parametros.append(turma_id)

    if professor_id is not None:

        sql += """
            AND aulas.professor_id = %s
        """

        parametros.append(professor_id)

    sql += """
        GROUP BY
            aulas.id,
            turmas.nome,
            professores.nome,
            aulas.data_hora

        ORDER BY
            aulas.data_hora DESC
    """

    cursor.execute(
        sql,
        parametros
    )

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado