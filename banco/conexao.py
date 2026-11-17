import mysql.connector

def conectar():

    conexao = mysql.connector.connect(
        host="localhost",
        user="root",
        password="mysql", # SENHA ALTERADA AQUI
        database="tcc_presenca"
    )

    return conexao