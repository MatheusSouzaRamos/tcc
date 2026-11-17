import csv
import platform
import time
from datetime import datetime

import cv2
import psutil


ARQUIVO = "monitoramento_pc.csv"
INTERVALO = 2


def obter_informacoes_pc():

    memoria = psutil.virtual_memory()
    disco = psutil.disk_usage("/")

    print("\n========== INFORMAÇÕES DO COMPUTADOR ==========")

    print(f"Sistema operacional: {platform.platform()}")
    print(f"Arquitetura: {platform.architecture()[0]}")
    print(f"Processador: {platform.processor()}")

    print(f"Núcleos físicos: {psutil.cpu_count(logical=False)}")
    print(f"Threads: {psutil.cpu_count(logical=True)}")

    frequencia = psutil.cpu_freq()

    if frequencia:
        print(f"Frequência atual: {frequencia.current:.0f} MHz")
        print(f"Frequência máxima: {frequencia.max:.0f} MHz")

    print(f"RAM total: {memoria.total / (1024 ** 3):.2f} GB")
    print(f"RAM disponível: {memoria.available / (1024 ** 3):.2f} GB")

    print(f"Disco total: {disco.total / (1024 ** 3):.2f} GB")
    print(f"Disco livre: {disco.free / (1024 ** 3):.2f} GB")

    print(f"Python: {platform.python_version()}")
    print(f"OpenCV: {cv2.__version__}")


def criar_csv():

    with open(
        ARQUIVO,
        "w",
        newline="",
        encoding="utf-8"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "data_hora",

            "cpu_total_percentual",

            "cpu_nucleo_1",
            "cpu_nucleo_2",
            "cpu_nucleo_3",
            "cpu_nucleo_4",

            "frequencia_cpu_mhz",

            "ram_percentual",
            "ram_usada_gb",
            "ram_disponivel_gb",

            "swap_percentual",

            "disco_percentual",
            "disco_livre_gb",

            "leitura_disco_mb",
            "escrita_disco_mb",

            "rede_enviada_mb",
            "rede_recebida_mb"
        ])


def monitorar():

    criar_csv()

    leitura_anterior = psutil.disk_io_counters()
    rede_anterior = psutil.net_io_counters()

    print("\n========== MONITORAMENTO ==========")
    print("Monitoramento iniciado.")
    print("Pressione CTRL+C para encerrar.\n")

    while True:

        time.sleep(INTERVALO)

        data_hora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        # CPU

        cpu_total = psutil.cpu_percent()

        cpu_nucleos = psutil.cpu_percent(
            percpu=True
        )

        frequencia = psutil.cpu_freq()

        if frequencia:
            frequencia_atual = frequencia.current
        else:
            frequencia_atual = 0

        # RAM

        memoria = psutil.virtual_memory()

        ram_percentual = memoria.percent

        ram_usada = (
            memoria.used / (1024 ** 3)
        )

        ram_disponivel = (
            memoria.available / (1024 ** 3)
        )

        # SWAP

        swap = psutil.swap_memory()

        # DISCO

        disco = psutil.disk_usage("/")

        leitura_atual = psutil.disk_io_counters()

        leitura_mb = (
            leitura_atual.read_bytes
            - leitura_anterior.read_bytes
        ) / (1024 ** 2)

        escrita_mb = (
            leitura_atual.write_bytes
            - leitura_anterior.write_bytes
        ) / (1024 ** 2)

        leitura_anterior = leitura_atual

        # REDE

        rede_atual = psutil.net_io_counters()

        rede_enviada_mb = (
            rede_atual.bytes_sent
            - rede_anterior.bytes_sent
        ) / (1024 ** 2)

        rede_recebida_mb = (
            rede_atual.bytes_recv
            - rede_anterior.bytes_recv
        ) / (1024 ** 2)

        rede_anterior = rede_atual

        # CSV

        with open(
            ARQUIVO,
            "a",
            newline="",
            encoding="utf-8"
        ) as arquivo:

            escritor = csv.writer(arquivo)

            escritor.writerow([
                data_hora,

                cpu_total,

                cpu_nucleos[0] if len(cpu_nucleos) > 0 else 0,
                cpu_nucleos[1] if len(cpu_nucleos) > 1 else 0,
                cpu_nucleos[2] if len(cpu_nucleos) > 2 else 0,
                cpu_nucleos[3] if len(cpu_nucleos) > 3 else 0,

                frequencia_atual,

                ram_percentual,
                round(ram_usada, 2),
                round(ram_disponivel, 2),

                swap.percent,

                disco.percent,
                round(disco.free / (1024 ** 3), 2),

                round(leitura_mb, 2),
                round(escrita_mb, 2),

                round(rede_enviada_mb, 2),
                round(rede_recebida_mb, 2)
            ])

        print(
            f"[{data_hora}] "
            f"CPU: {cpu_total:.1f}% | "
            f"RAM: {ram_percentual:.1f}% | "
            f"Disco: {disco.percent:.1f}% | "
            f"Rede ↓ {rede_recebida_mb:.2f} MB"
        )


if __name__ == "__main__":

    try:

        obter_informacoes_pc()
        monitorar()

    except KeyboardInterrupt:

        print("\nMonitoramento encerrado.")