
import streamlit as st
import mysql.connector
import requests
import subprocess
import sys
import os
import json
import pandas as pd

from consultas import (
    buscar_resumo,
    buscar_alunos as consultar_alunos,
    buscar_turmas as consultar_turmas,
    buscar_professores as consultar_professores,
    buscar_frequencia,
    buscar_historico,
    buscar_relatorio_aulas
)


# ==========================================
# CONFIGURAÇÃO
# ==========================================

st.set_page_config(
    page_title="Sistema de Presença",
    page_icon="🎓",
    layout="wide"
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVIDOR_DIR = os.path.dirname(BASE_DIR)

CAMINHO_SALVAR_ROSTO = os.path.join(
    SERVIDOR_DIR,
    "modelos",
    "SalvarRosto.py"
)

CAMINHO_SERVIDOR = os.path.join(
    SERVIDOR_DIR,
    "app.py"
)

CAMINHO_CONFIG = os.path.join(
    BASE_DIR,
    "configuracao.json"
)


# ==========================================
# ESTADO DA INTERFACE
# ==========================================

if "pagina" not in st.session_state:
    st.session_state.pagina = "Início"


# ==========================================
# CONFIGURAÇÃO DO SERVIDOR
# ==========================================

def carregar_configuracao():

    if not os.path.exists(CAMINHO_CONFIG):

        return {
            "servidor": "10.124.64.77",
            "porta": 5000
        }

    try:

        with open(
            CAMINHO_CONFIG,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(arquivo)

    except Exception:

        return {
            "servidor": "10.124.64.77",
            "porta": 5000
        }


def salvar_configuracao(servidor, porta):

    configuracao = {
        "servidor": servidor,
        "porta": porta
    }

    with open(
        CAMINHO_CONFIG,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            configuracao,
            arquivo,
            indent=4
        )


configuracao = carregar_configuracao()

SERVIDOR = configuracao["servidor"]
PORTA = configuracao["porta"]

URL_SERVIDOR = f"http://{SERVIDOR}:{PORTA}"


# ==========================================
# BANCO DE DADOS
# ==========================================

def conectar():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="mysql",
        database="tcc_presenca"
    )


# ==========================================
# FUNÇÕES DE CADASTRO
# ==========================================

def cadastrar_turma(nome, curso):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO turmas (
            nome,
            curso
        )
        VALUES (%s, %s)
    """, (
        nome,
        curso
    ))

    conexao.commit()

    turma_id = cursor.lastrowid

    cursor.close()
    conexao.close()

    return turma_id


def buscar_turmas():

    return consultar_turmas()


def buscar_turmas_com_alunos():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            turmas.id,
            turmas.nome,
            turmas.curso,
            COUNT(aluno_turma.aluno_id) AS total_alunos
        FROM turmas
        LEFT JOIN aluno_turma
            ON turmas.id = aluno_turma.turma_id
        GROUP BY
            turmas.id,
            turmas.nome,
            turmas.curso
        ORDER BY turmas.nome
    """)

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def buscar_alunos():

    return consultar_alunos()


def cadastrar_aluno(nome, turma_id):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO alunos (nome)
        VALUES (%s)
    """, (nome,))

    aluno_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO aluno_turma (
            aluno_id,
            turma_id
        )
        VALUES (%s, %s)
    """, (
        aluno_id,
        turma_id
    ))

    conexao.commit()

    cursor.close()
    conexao.close()

    return aluno_id


def cadastrar_professor(nome, uid):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO professores (
            nome,
            uid
        )
        VALUES (%s, %s)
    """, (
        nome,
        uid
    ))

    conexao.commit()

    cursor.close()
    conexao.close()


def buscar_professores():

    return consultar_professores()


def associar_professor_turma(professor_id, turma_id):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO professor_turma (
            professor_id,
            turma_id
        )
        VALUES (%s, %s)
    """, (
        professor_id,
        turma_id
    ))

    conexao.commit()

    cursor.close()
    conexao.close()


def buscar_associacoes_professores():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            professor_turma.professor_id,
            professor_turma.turma_id,
            professores.nome AS professor,
            professores.uid,
            turmas.nome AS turma,
            turmas.curso
        FROM professor_turma
        INNER JOIN professores
            ON professor_turma.professor_id = professores.id
        INNER JOIN turmas
            ON professor_turma.turma_id = turmas.id
        ORDER BY professores.nome, turmas.nome
    """)

    resultado = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultado


def remover_associacao_professor_turma(
    professor_id,
    turma_id
):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        DELETE FROM professor_turma
        WHERE professor_id = %s
        AND turma_id = %s
    """, (
        professor_id,
        turma_id
    ))

    conexao.commit()

    cursor.close()
    conexao.close()


# ==========================================
# SERVIDOR FLASK
# ==========================================

def testar_servidor():

    try:

        resposta = requests.get(
            URL_SERVIDOR,
            timeout=3
        )

        return resposta.status_code == 200

    except Exception:

        return False


def iniciar_servidor():

    try:

        if testar_servidor():

            return True

        subprocess.Popen(
            [
                sys.executable,
                CAMINHO_SERVIDOR
            ],
            cwd=SERVIDOR_DIR
        )

        return True

    except Exception as erro:

        st.error(
            f"Erro ao iniciar servidor: {erro}"
        )

        return False


# ==========================================
# STATUS DO SISTEMA
# ==========================================

def verificar_status_sistema():

    mysql_ok = False
    flask_ok = False
    reconhecimento_ok = False

    try:

        conexao = conectar()

        if conexao.is_connected():
            mysql_ok = True

        conexao.close()

    except Exception:

        mysql_ok = False

    flask_ok = testar_servidor()

    reconhecimento_ok = os.path.exists(
        CAMINHO_SALVAR_ROSTO
    )

    sistema_ok = (
        mysql_ok
        and flask_ok
        and reconhecimento_ok
    )

    return (
        mysql_ok,
        flask_ok,
        reconhecimento_ok,
        sistema_ok
    )


# ==========================================
# ACOMPANHAMENTO DA AULA
# ==========================================

def buscar_aula_aberta():

    try:

        resposta = requests.get(
            f"{URL_SERVIDOR}/api/aula-aberta",
            timeout=3
        )

        if resposta.status_code != 200:

            return None

        dados = resposta.json()

        if not dados.get("aula_aberta"):

            return None

        return dados

    except Exception:

        return None


def buscar_presencas_aula(aula_id):

    try:

        resposta = requests.get(
            f"{URL_SERVIDOR}/api/presencas-aula/{aula_id}",
            timeout=3
        )

        if resposta.status_code != 200:

            return []

        dados = resposta.json()

        return dados.get(
            "presencas",
            []
        )

    except Exception:

        return []


# ==========================================
# NAVEGAÇÃO
# ==========================================

def voltar_inicio():

    st.session_state.pagina = "Início"
    st.rerun()


# ==========================================
# ESTILO
# ==========================================

st.markdown("""
<style>

.titulo-principal {
    text-align: center;
    font-size: 42px;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 5px;
}

.subtitulo {
    text-align: center;
    font-size: 18px;
    margin-bottom: 30px;
}

.card-titulo {
    font-size: 23px;
    font-weight: 600;
    margin-bottom: 8px;
}

.card-descricao {
    font-size: 15px;
    min-height: 45px;
}

.status {
    text-align: center;
    font-size: 17px;
    margin-top: 20px;
}

</style>
""", unsafe_allow_html=True)


pagina = st.session_state.pagina


# ==========================================
# INÍCIO
# ==========================================

if pagina == "Início":

    st.markdown(
        '<div class="titulo-principal">'
        'Sistema de Presença'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitulo">'
        'Controle de frequência acadêmica por RFID e reconhecimento facial'
        '</div>',
        unsafe_allow_html=True
    )

    # ======================================
    # STATUS DO SISTEMA
    # ======================================

    mysql_ok, flask_ok, reconhecimento_ok, sistema_ok = (
        verificar_status_sistema()
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "MySQL",
            "Conectado" if mysql_ok else "Offline"
        )

    with col2:

        st.metric(
            "Flask",
            "Online" if flask_ok else "Offline"
        )

    with col3:

        try:

            alunos = buscar_alunos()

            quantidade_alunos = len(alunos)

            st.metric(
                "Alunos cadastrados",
                quantidade_alunos
            )

        except Exception:

            st.metric(
                "Alunos cadastrados",
                "Erro"
            )

    with col4:

        st.metric(
            "Sistema",
            "Pronto" if sistema_ok else "Inválido"
        )

    st.divider()

    # ======================================
    # CARDS PRINCIPAIS
    # ======================================

    col1, col2 = st.columns(2)

    with col1:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Cadastrar Aluno'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Cadastre alunos e registre o rosto para o reconhecimento facial.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Cadastrar Aluno",
                use_container_width=True,
                type="primary"
            ):

                st.session_state.pagina = "Cadastrar Aluno"
                st.rerun()

    with col2:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Turmas'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Cadastre as turmas e consulte as turmas existentes no sistema.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Turmas",
                use_container_width=True,
                type="primary"
            ):

                st.session_state.pagina = "Turmas"
                st.rerun()

    st.write("")

    col3, col4 = st.columns(2)

    with col3:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Professor e RFID'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Cadastre professores, cartões RFID e associe as turmas.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Professor e RFID",
                use_container_width=True,
                type="primary"
            ):

                st.session_state.pagina = "Professor e RFID"
                st.rerun()

    with col4:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Acompanhamento da Aula'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Acompanhe a aula aberta, o professor, a turma e as presenças.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Acompanhamento da Aula",
                use_container_width=True,
                type="primary"
            ):

                st.session_state.pagina = "Acompanhamento da Aula"
                st.rerun()

    st.write("")

    col5, col6 = st.columns(2)

    with col5:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Configurar Rede'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Configure o servidor Flask e os dispositivos do sistema.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Configurar Rede",
                use_container_width=True
            ):

                st.session_state.pagina = "Configurar Rede"
                st.rerun()

    with col6:

        with st.container(border=True):

            st.markdown(
                '<div class="card-titulo">'
                'Iniciar Sistema'
                '</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<div class="card-descricao">'
                'Verifique e inicialize os componentes necessários do sistema.'
                '</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "Iniciar Sistema",
                use_container_width=True
            ):

                st.session_state.pagina = "Iniciar Sistema"
                st.rerun()

    st.write("")

    with st.container(border=True):

        st.markdown(
            '<div class="card-titulo">'
            'Dashboard e Relatórios'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="card-descricao">'
            'Consulte frequência, aulas, alunos e relatórios em uma única aplicação.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "Abrir Dashboard e Relatórios",
            use_container_width=True
        ):

            st.session_state.pagina = "Dashboard e Relatórios"
            st.rerun()


# ==========================================
# TURMAS
# ==========================================

elif pagina == "Turmas":

    st.title("Cadastrar Turma")

    st.write(
        "Cadastre as turmas que serão utilizadas para organizar "
        "professores e alunos."
    )

    st.divider()

    st.subheader("Nova turma")

    col1, col2 = st.columns(2)

    with col1:

        nome_turma = st.text_input(
            "Nome da turma",
            placeholder="Ex.: TCC2"
        )

    with col2:

        curso_turma = st.text_input(
            "Curso",
            placeholder="Ex.: Engenharia de Computação"
        )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Cadastrar turma",
            type="primary",
            use_container_width=True
        ):

            if not nome_turma.strip():

                st.error("Digite o nome da turma.")

            elif not curso_turma.strip():

                st.error("Digite o curso.")

            else:

                try:

                    turma_id = cadastrar_turma(
                        nome_turma.strip(),
                        curso_turma.strip()
                    )

                    st.success(
                        f"Turma cadastrada com ID {turma_id}."
                    )

                    st.rerun()

                except Exception as erro:

                    st.error(
                        f"Erro ao cadastrar turma: {erro}"
                    )

    with col2:

        if st.button(
            "Voltar ao início",
            use_container_width=True
        ):

            voltar_inicio()

    st.divider()

    st.subheader("Turmas cadastradas")

    try:

        turmas = buscar_turmas_com_alunos()

        if turmas:

            dados_tabela = []

            for turma in turmas:

                dados_tabela.append({
                    "ID": turma["id"],
                    "Turma": turma["nome"],
                    "Curso": turma["curso"],
                    "Alunos": turma["total_alunos"]
                })

            st.dataframe(
                dados_tabela,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Nenhuma turma cadastrada."
            )

    except Exception as erro:

        st.error(
            f"Erro ao consultar turmas: {erro}"
        )


# ==========================================
# CADASTRAR ALUNO
# ==========================================

elif pagina == "Cadastrar Aluno":

    st.title("Cadastrar Aluno")

    st.write(
        "Cadastre o aluno e registre o rosto para utilização "
        "no reconhecimento facial."
    )

    st.divider()

    turmas = buscar_turmas()

    if not turmas:

        st.warning(
            "Nenhuma turma cadastrada no banco de dados."
        )

        if st.button(
            "Cadastrar turma",
            type="primary"
        ):

            st.session_state.pagina = "Turmas"
            st.rerun()

    else:

        nomes_turmas = [
            f"{turma['nome']} - {turma['curso']}"
            for turma in turmas
        ]

        turma_selecionada = st.selectbox(
            "Turma",
            nomes_turmas
        )

        indice_turma = nomes_turmas.index(
            turma_selecionada
        )

        turma_id = turmas[indice_turma]["id"]

        nome = st.text_input(
            "Nome completo do aluno",
            placeholder="Digite o nome completo"
        )

        st.write("")

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Cadastrar aluno e registrar rosto",
                type="primary",
                use_container_width=True
            ):

                if not nome.strip():

                    st.error(
                        "Digite o nome do aluno."
                    )

                else:

                    try:

                        aluno_id = cadastrar_aluno(
                            nome.strip(),
                            turma_id
                        )

                        st.success(
                            f"Aluno cadastrado com ID {aluno_id}."
                        )

                        if not os.path.exists(
                            CAMINHO_SALVAR_ROSTO
                        ):

                            st.error(
                                "Arquivo SalvarRosto.py não encontrado."
                            )

                        else:

                            st.info(
                                "A câmera será aberta para o cadastro facial."
                            )

                            with st.spinner(
                                "Aguardando conclusão do cadastro facial..."
                            ):

                                processo = subprocess.Popen(
                                    [
                                        sys.executable,
                                        CAMINHO_SALVAR_ROSTO
                                    ],
                                    stdin=subprocess.PIPE,
                                    text=True,
                                    cwd=os.path.dirname(
                                        CAMINHO_SALVAR_ROSTO
                                    )
                                )

                                processo.communicate(
                                    input=f"{aluno_id}\n"
                                )

                            if processo.returncode == 0:

                                st.success(
                                    "Cadastro facial finalizado com sucesso."
                                )

                            else:

                                st.error(
                                    "O cadastro facial foi encerrado com erro."
                                )

                    except Exception as erro:

                        st.error(
                            f"Erro no cadastro: {erro}"
                        )

        with col2:

            if st.button(
                "Voltar ao início",
                use_container_width=True
            ):

                voltar_inicio()

    st.divider()

    st.subheader("Alunos cadastrados")

    try:

        alunos = buscar_alunos()

        if alunos:

            st.dataframe(
                alunos,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Nenhum aluno cadastrado."
            )

    except Exception as erro:

        st.error(
            f"Erro ao consultar alunos: {erro}"
        )


# ==========================================
# PROFESSOR E RFID
# ==========================================

elif pagina == "Professor e RFID":

    st.title("Cadastrar Professor e RFID")

    st.write(
        "Cadastre o professor, associe seu cartão RFID "
        "e defina a turma em que ele irá ministrar aula."
    )

    st.divider()

    st.subheader("Cadastro do professor")

    col1, col2 = st.columns(2)

    with col1:

        nome_professor = st.text_input(
            "Nome do professor",
            placeholder="Digite o nome do professor"
        )

    with col2:

        uid = st.text_input(
            "UID do cartão RFID",
            placeholder="Ex.: 351D8105"
        )

    st.info(
        "O UID identifica o cartão RFID utilizado pelo professor."
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Cadastrar professor",
            type="primary",
            use_container_width=True
        ):

            if not nome_professor.strip():

                st.error(
                    "Digite o nome do professor."
                )

            elif not uid.strip():

                st.error(
                    "Digite o UID do cartão."
                )

            else:

                try:

                    cadastrar_professor(
                        nome_professor.strip(),
                        uid.strip().upper()
                    )

                    st.success(
                        "Professor e cartão cadastrados com sucesso."
                    )

                    st.rerun()

                except mysql.connector.IntegrityError:

                    st.error(
                        "Esse UID já está cadastrado."
                    )

                except Exception as erro:

                    st.error(
                        f"Erro no cadastro: {erro}"
                    )

    with col2:

        if st.button(
            "Voltar ao início",
            use_container_width=True
        ):

            voltar_inicio()

    st.divider()

    st.subheader("Associar professor à turma")

    try:

        professores = buscar_professores()
        turmas = buscar_turmas()

        if not professores:

            st.warning(
                "Cadastre pelo menos um professor antes de fazer a associação."
            )

        elif not turmas:

            st.warning(
                "Cadastre pelo menos uma turma antes de fazer a associação."
            )

            if st.button(
                "Cadastrar turma",
                type="primary"
            ):

                st.session_state.pagina = "Turmas"
                st.rerun()

        else:

            nomes_professores = [
                f"{professor['nome']} - UID: {professor['uid']}"
                for professor in professores
            ]

            nomes_turmas = [
                f"{turma['nome']} - {turma['curso']}"
                for turma in turmas
            ]

            col1, col2 = st.columns(2)

            with col1:

                professor_selecionado = st.selectbox(
                    "Professor",
                    nomes_professores,
                    key="professor_associacao"
                )

            with col2:

                turma_selecionada = st.selectbox(
                    "Turma",
                    nomes_turmas,
                    key="turma_associacao"
                )

            indice_professor = nomes_professores.index(
                professor_selecionado
            )

            indice_turma = nomes_turmas.index(
                turma_selecionada
            )

            professor_id = professores[indice_professor]["id"]
            turma_id = turmas[indice_turma]["id"]

            if st.button(
                "Associar professor à turma",
                type="primary",
                use_container_width=True
            ):

                try:

                    associar_professor_turma(
                        professor_id,
                        turma_id
                    )

                    st.success(
                        "Professor associado à turma com sucesso."
                    )

                    st.rerun()

                except mysql.connector.IntegrityError:

                    st.warning(
                        "Esse professor já está associado a essa turma."
                    )

                except Exception as erro:

                    st.error(
                        f"Erro ao associar professor à turma: {erro}"
                    )

    except Exception as erro:

        st.error(
            f"Erro ao carregar professores e turmas: {erro}"
        )

    st.divider()

    st.subheader("Associações cadastradas")

    try:

        associacoes = buscar_associacoes_professores()

        if associacoes:

            dados_tabela = []

            for associacao in associacoes:

                dados_tabela.append({
                    "Professor": associacao["professor"],
                    "UID": associacao["uid"],
                    "Turma": associacao["turma"],
                    "Curso": associacao["curso"]
                })

            st.dataframe(
                dados_tabela,
                use_container_width=True,
                hide_index=True
            )

            st.write("")

            st.subheader("Remover associação")

            opcoes_remocao = [
                (
                    f"{associacao['professor']} → "
                    f"{associacao['turma']}"
                )
                for associacao in associacoes
            ]

            associacao_selecionada = st.selectbox(
                "Selecione a associação",
                opcoes_remocao,
                key="remover_associacao"
            )

            indice_associacao = opcoes_remocao.index(
                associacao_selecionada
            )

            associacao = associacoes[indice_associacao]

            if st.button(
                "Remover associação",
                use_container_width=True
            ):

                try:

                    remover_associacao_professor_turma(
                        associacao["professor_id"],
                        associacao["turma_id"]
                    )

                    st.success(
                        "Associação removida com sucesso."
                    )

                    st.rerun()

                except Exception as erro:

                    st.error(
                        f"Erro ao remover associação: {erro}"
                    )

        else:

            st.info(
                "Nenhuma associação entre professor e turma cadastrada."
            )

    except Exception as erro:

        st.error(
            f"Erro ao consultar associações: {erro}"
        )

    st.divider()

    st.subheader("Professores cadastrados")

    try:

        professores = buscar_professores()

        if professores:

            st.dataframe(
                professores,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Nenhum professor cadastrado."
            )

    except Exception as erro:

        st.error(
            f"Erro ao consultar professores: {erro}"
        )


# ==========================================
# ACOMPANHAMENTO DA AULA
# ==========================================

elif pagina == "Acompanhamento da Aula":

    st.title("Acompanhamento da Aula")

    if st.button(
        "← Voltar para a tela inicial",
        use_container_width=True
    ):

        voltar_inicio()

    st.caption(
        "Acompanhe a aula atualmente aberta pelo professor."
    )

    st.divider()

    aula = buscar_aula_aberta()

    if aula is None:

        st.info(
            "Nenhuma aula está aberta no momento."
        )

        st.write(
            "A aula será aberta quando o professor aproximar "
            "o cartão RFID do leitor."
        )

    else:

        aula_id = aula.get("aula_id")
        professor = aula.get(
            "professor",
            "Não informado"
        )
        turma = aula.get(
            "turma",
            "Não informada"
        )

        st.success(
            "Aula aberta"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Professor",
                professor
            )

        with col2:

            st.metric(
                "Turma",
                turma
            )

        with col3:

            st.metric(
                "Aula",
                aula_id
            )

        st.divider()

        st.subheader(
            "Presença dos alunos"
        )

        presencas = buscar_presencas_aula(
            aula_id
        )

        if not presencas:

            st.warning(
                "A aula está aberta, mas ainda não existem "
                "presenças registradas no banco para esta aula."
            )

            st.info(
                "As presenças finais são registradas quando "
                "o professor encerra a aula pelo cartão RFID."
            )

        else:

            total_alunos = len(presencas)

            presentes = sum(
                1
                for aluno in presencas
                if aluno["status"] == "presente"
            )

            ausentes = sum(
                1
                for aluno in presencas
                if aluno["status"] == "ausente"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Total de alunos",
                    total_alunos
                )

            with col2:

                st.metric(
                    "Presentes",
                    presentes
                )

            with col3:

                st.metric(
                    "Ausentes",
                    ausentes
                )

            st.write("")

            dados_tabela = []

            for aluno in presencas:

                dados_tabela.append({
                    "Aluno": aluno["aluno"],
                    "Frequência (%)": float(
                        aluno["percentual_presenca"]
                    ),
                    "Status": aluno["status"].upper()
                })

            df_presencas = pd.DataFrame(
                dados_tabela
            )

            st.dataframe(
                df_presencas,
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Atualizar acompanhamento",
                type="primary",
                use_container_width=True
            ):

                st.rerun()

        with col2:

            if st.button(
                "Voltar ao início",
                use_container_width=True
            ):

                voltar_inicio()


# ==========================================
# DASHBOARD E RELATÓRIOS
# ==========================================

elif pagina == "Dashboard e Relatórios":

    st.title("Dashboard e Relatórios")

    st.caption(
        "Acompanhamento da frequência acadêmica"
    )

    st.divider()

    try:

        turmas = buscar_turmas()
        alunos = buscar_alunos()
        professores = buscar_professores()

    except Exception as erro:

        st.error(
            f"Erro ao carregar filtros: {erro}"
        )

        st.stop()

    # ======================================
    # FILTROS
    # ======================================

    st.subheader("Filtros")

    col1, col2, col3 = st.columns(3)

    with col1:

        nomes_turmas = ["Todas"]

        nomes_turmas += [
            turma["nome"]
            for turma in turmas
        ]

        turma_selecionada = st.selectbox(
            "Turma",
            nomes_turmas,
            key="dashboard_turma"
        )

    with col2:

        nomes_alunos = ["Todos"]

        nomes_alunos += [
            aluno["nome"]
            for aluno in alunos
        ]

        aluno_selecionado = st.selectbox(
            "Aluno",
            nomes_alunos,
            key="dashboard_aluno"
        )

    with col3:

        nomes_professores = ["Todos"]

        nomes_professores += [
            professor["nome"]
            for professor in professores
        ]

        professor_selecionado = st.selectbox(
            "Professor",
            nomes_professores,
            key="dashboard_professor"
        )

    turma_id = None
    aluno_id = None
    professor_id = None

    if turma_selecionada != "Todas":

        for turma in turmas:

            if turma["nome"] == turma_selecionada:

                turma_id = turma["id"]
                break

    if aluno_selecionado != "Todos":

        for aluno in alunos:

            if aluno["nome"] == aluno_selecionado:

                aluno_id = aluno["id"]
                break

    if professor_selecionado != "Todos":

        for professor in professores:

            if professor["nome"] == professor_selecionado:

                professor_id = professor["id"]
                break

    st.divider()

    # ======================================
    # ABAS
    # ======================================

    aba_dashboard, aba_frequencia, aba_alunos, aba_aulas, aba_relatorio = st.tabs([
        "Dashboard",
        "Frequência",
        "Alunos",
        "Aulas",
        "Relatório"
    ])

    # ======================================
    # DASHBOARD
    # ======================================

    with aba_dashboard:

        try:

            resumo = buscar_resumo()

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                st.metric(
                    "Alunos",
                    resumo["alunos"]
                )

            with col2:

                st.metric(
                    "Aulas",
                    resumo["aulas"]
                )

            with col3:

                st.metric(
                    "Presenças",
                    resumo["presencas"]
                )

            with col4:

                st.metric(
                    "Faltas",
                    resumo["faltas"]
                )

            with col5:

                st.metric(
                    "Frequência média",
                    f"{resumo['media']:.2f}%"
                )

            st.divider()

            st.subheader(
                "Frequência dos alunos"
            )

            dados = buscar_frequencia(
                turma_id,
                aluno_id,
                professor_id
            )

            if dados:

                df = pd.DataFrame(dados)

                df.columns = [
                    "ID",
                    "Aluno",
                    "Aulas",
                    "Presenças",
                    "Faltas",
                    "Frequência (%)"
                ]

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Nenhum registro encontrado."
                )

        except Exception as erro:

            st.error(
                f"Erro ao carregar dashboard: {erro}"
            )

    # ======================================
    # FREQUÊNCIA
    # ======================================

    with aba_frequencia:

        st.header(
            "Relatório de Frequência"
        )

        try:

            dados = buscar_frequencia(
                turma_id,
                aluno_id,
                professor_id
            )

            if dados:

                df = pd.DataFrame(dados)

                df.columns = [
                    "ID",
                    "Aluno",
                    "Aulas",
                    "Presenças",
                    "Faltas",
                    "Frequência (%)"
                ]

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Nenhum registro encontrado."
                )

        except Exception as erro:

            st.error(
                f"Erro ao carregar frequência: {erro}"
            )

    # ======================================
    # ALUNOS
    # ======================================

    with aba_alunos:

        st.header(
            "Alunos cadastrados"
        )

        try:

            if alunos:

                df = pd.DataFrame(
                    alunos
                )

                df.columns = [
                    "ID",
                    "Nome",
                    "Ativo"
                ]

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Nenhum aluno cadastrado."
                )

        except Exception as erro:

            st.error(
                f"Erro ao carregar alunos: {erro}"
            )

    # ======================================
    # AULAS
    # ======================================

    with aba_aulas:

        st.header(
            "Relatório por Aula"
        )

        try:

            dados = buscar_relatorio_aulas(
                turma_id,
                professor_id
            )

            if dados:

                df = pd.DataFrame(dados)

                df.columns = [
                    "Aula",
                    "Turma",
                    "Professor",
                    "Data/Hora",
                    "Alunos",
                    "Presentes",
                    "Ausentes",
                    "Frequência Média (%)"
                ]

                df["Data/Hora"] = pd.to_datetime(
                    df["Data/Hora"]
                ).dt.strftime(
                    "%d/%m/%Y %H:%M"
                )

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                st.divider()

                st.subheader(
                    "Resumo das aulas"
                )

                col1, col2, col3, col4 = st.columns(4)

                with col1:

                    st.metric(
                        "Aulas realizadas",
                        len(df)
                    )

                with col2:

                    st.metric(
                        "Presentes",
                        int(
                            df["Presentes"].sum()
                        )
                    )

                with col3:

                    st.metric(
                        "Ausentes",
                        int(
                            df["Ausentes"].sum()
                        )
                    )

                with col4:

                    st.metric(
                        "Frequência média",
                        f"{df['Frequência Média (%)'].mean():.2f}%"
                    )

                st.divider()

                st.subheader(
                    "Frequência média por aula"
                )

                grafico = df[
                    [
                        "Aula",
                        "Frequência Média (%)"
                    ]
                ].set_index(
                    "Aula"
                )

                st.bar_chart(
                    grafico
                )

                csv = df.to_csv(
                    index=False
                ).encode(
                    "utf-8"
                )

                st.download_button(
                    label="Baixar relatório de aulas",
                    data=csv,
                    file_name="relatorio_aulas.csv",
                    mime="text/csv"
                )

            else:

                st.info(
                    "Nenhuma aula encontrada."
                )

        except Exception as erro:

            st.error(
                f"Erro ao carregar relatório de aulas: {erro}"
            )

    # ======================================
    # RELATÓRIO
    # ======================================

    with aba_relatorio:

        st.header(
            "Relatório detalhado"
        )

        try:

            dados = buscar_historico(
                turma_id,
                aluno_id,
                professor_id
            )

            if dados:

                df = pd.DataFrame(dados)

                df.columns = [
                    "ID",
                    "Aluno",
                    "Professor",
                    "Turma",
                    "Aula",
                    "Data/Hora",
                    "Percentual (%)",
                    "Status"
                ]

                df["Data/Hora"] = pd.to_datetime(
                    df["Data/Hora"]
                ).dt.strftime(
                    "%d/%m/%Y %H:%M"
                )

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                csv = df.to_csv(
                    index=False
                ).encode(
                    "utf-8"
                )

                st.download_button(
                    label="Baixar relatório CSV",
                    data=csv,
                    file_name="relatorio_presenca.csv",
                    mime="text/csv"
                )

            else:

                st.info(
                    "Nenhum registro encontrado."
                )

        except Exception as erro:

            st.error(
                f"Erro ao carregar relatório: {erro}"
            )

    st.divider()

    if st.button(
        "Voltar ao início",
        use_container_width=True
    ):

        voltar_inicio()


# ==========================================
# CONFIGURAR REDE
# ==========================================

elif pagina == "Configurar Rede":

    st.title("Configurar Rede")

    st.write(
        "Configure o endereço utilizado pela interface "
        "para acessar o servidor Flask."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        servidor = st.text_input(
            "Endereço IP do servidor",
            value=SERVIDOR
        )

    with col2:

        porta = st.number_input(
            "Porta",
            min_value=1,
            max_value=65535,
            value=int(PORTA)
        )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Salvar configuração",
            type="primary",
            use_container_width=True
        ):

            try:

                salvar_configuracao(
                    servidor.strip(),
                    int(porta)
                )

                st.success(
                    "Configuração salva com sucesso."
                )

                st.info(
                    "Atualize a página para utilizar a nova configuração."
                )

            except Exception as erro:

                st.error(
                    f"Erro ao salvar configuração: {erro}"
                )

    with col2:

        if st.button(
            "Voltar ao início",
            use_container_width=True
        ):

            voltar_inicio()

    st.divider()

    st.subheader("Teste de conexão")

    url_teste = f"http://{servidor}:{porta}"

    try:

        resposta = requests.get(
            url_teste,
            timeout=3
        )

        if resposta.status_code == 200:

            st.success(
                f"Servidor online: {url_teste}"
            )

        else:

            st.warning(
                f"Servidor respondeu com código {resposta.status_code}."
            )

    except Exception:

        st.error(
            f"Não foi possível conectar em {url_teste}"
        )


# ==========================================
# INICIAR SISTEMA
# ==========================================

elif pagina == "Iniciar Sistema":

    st.title("Iniciar Sistema")

    st.write(
        "Verifique os componentes necessários para o funcionamento."
    )

    st.divider()

    mysql_ok, flask_ok, reconhecimento_ok, sistema_ok = (
        verificar_status_sistema()
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        if mysql_ok:

            st.success(
                "MySQL conectado"
            )

        else:

            st.error(
                "MySQL offline"
            )

    with col2:

        if flask_ok:

            st.success(
                f"Flask online em {URL_SERVIDOR}"
            )

        else:

            st.warning(
                "Flask está offline."
            )

    with col3:

        if reconhecimento_ok:

            st.success(
                "Reconhecimento facial disponível"
            )

        else:

            st.error(
                "Reconhecimento facial não encontrado"
            )

    st.divider()

    st.subheader("Inicialização")

    if testar_servidor():

        st.success(
            "O servidor Flask já está funcionando."
        )

    else:

        if st.button(
            "Iniciar Flask",
            type="primary",
            use_container_width=True
        ):

            if iniciar_servidor():

                st.success(
                    "Servidor Flask iniciado."
                )

                st.info(
                    "Aguarde alguns segundos e atualize a página."
                )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Atualizar status",
            use_container_width=True
        ):

            st.rerun()

    with col2:

        if st.button(
            "Voltar ao início",
            use_container_width=True
        ):

            voltar_inicio()

    st.divider()

    st.subheader("Status geral")

    if sistema_ok:

        st.success(
            "Todos os componentes necessários estão funcionando."
        )

    else:

        st.warning(
            "Um ou mais componentes precisam de atenção."
        )
