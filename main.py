from time import sleep
from random import randint

from core.estado import carregar_progresso, salvar_progresso, limpar_progresso
from core.preparar_ambiente import preparar
from core.whatsapp import iniciar_chrome, abrir_whatsapp_web
from core.excel import ler_contatos
from core.envio import (
    abrir_conversa,
    anexar_midia,
    enviar_midia,
    escrever_texto,
    enviar_texto,
    fechar_dialogo_nativo,
)
from core.mensagem import carregar_mensagem, personalizar_mensagem
from core.logger import iniciar_log, finalizar_log, log
from config import (
    ARQUIVO_IMAGEM,
    ARQUIVO_VIDEO,
    TEMPO_ENTRE_MENSAGENS_MIN,
    TEMPO_ENTRE_MENSAGENS_MAX,
)


def escolher_midia():
    print()
    print("=" * 60)
    print("O que você quer enviar nesta campanha?")
    print("[1] Imagem")
    print("[2] Vídeo")
    print("=" * 60)

    while True:
        escolha = input("Digite 1 ou 2 e pressione ENTER: ").strip()

        if escolha == "1":
            print(f"Selecionado: Imagem ({ARQUIVO_IMAGEM.name})")
            return ARQUIVO_IMAGEM

        if escolha == "2":
            print(f"Selecionado: Vídeo ({ARQUIVO_VIDEO.name})")
            return ARQUIVO_VIDEO

        print("Opção inválida. Digite 1 ou 2.")


def escolher_formato_telefone():
    print()
    print("=" * 60)
    print("Como os números estão preenchidos no Excel?")
    print("[1] DDD + número (adicionar automaticamente o código 55)")
    print("[2] Número completo com o código 55")
    print("=" * 60)

    while True:
        escolha = input("Digite 1 ou 2 e pressione ENTER: ").strip()

        if escolha == "1":
            print("Selecionado: adicionar automaticamente o código 55")
            return True

        if escolha == "2":
            print("Selecionado: usar o número completo do Excel")
            return False

        print("Opção inválida. Digite 1 ou 2.")


def formatar_telefone(telefone, adicionar_codigo_pais):
    telefone = "".join(caractere for caractere in str(telefone) if caractere.isdigit())

    if adicionar_codigo_pais and not telefone.startswith("55"):
        telefone = "55" + telefone

    return telefone


def main():
    arquivo_midia = escolher_midia()

    if not arquivo_midia.exists():
        print()
        print(f"ERRO: arquivo não encontrado: {arquivo_midia}")
        print("Coloque o arquivo na pasta 'dados' e rode de novo.")
        return

    adicionar_codigo_pais = escolher_formato_telefone()

    preparar()
    iniciar_log()
    driver = iniciar_chrome()
    abrir_whatsapp_web(driver)
    contatos = ler_contatos()

    estado = carregar_progresso()
    indice_inicial = 0
    enviados = 0
    erros = 0

    if estado:
        indice_inicial = estado["ultimo_indice"] + 1
        enviados = estado.get("enviados", 0)
        erros = estado.get("erros", 0)
        log("")
        log("=" * 60)
        log("PROGRESSO ENCONTRADO")
        log("=" * 60)
        log(f'Último contato : {estado["nome"]}')
        log(f'Telefone.......: {estado["telefone"]}')
        log(f'Índice.........: {estado["ultimo_indice"]}')
        log(f'Enviados.......: {enviados}')
        log(f'Erros..........: {erros}')
        log(f'Data...........: {estado["data_hora"]}')
        log("")
        log(f"Retomando do contato {indice_inicial + 1}...")

    mensagem_base = carregar_mensagem()
    total = len(contatos)

    print()
    print("=" * 60)
    print(f"Foram encontrados {total} contatos.")
    print("=" * 60)

    for indice in range(indice_inicial, len(contatos)):
        contato = contatos[indice]
        nome = str(contato["Nome"]).strip()
        telefone = formatar_telefone(
            contato["Whatsapp"], adicionar_codigo_pais
        )
        titulo = f"[{indice + 1}/{total}] {nome}"

        print("")
        print("=" * 60)
        print(titulo)
        print("=" * 60)
        log("")
        log("=" * 60)
        log(titulo)
        log("=" * 60)

        try:
            abrir_conversa(driver, telefone)

            texto = personalizar_mensagem(mensagem_base, contato)

            anexar_midia(driver, arquivo_midia)
            enviar_midia(driver)
            sleep(30)
            escrever_texto(driver, texto)
            sleep(4)
            enviar_texto(driver)
            sleep(4)

            enviados += 1
            salvar_progresso(indice, nome, telefone, enviados, erros)

            espera = randint(
                TEMPO_ENTRE_MENSAGENS_MIN,
                TEMPO_ENTRE_MENSAGENS_MAX,
            )

            log("Mensagem enviada com sucesso.")
            log(f"Aguardando {espera} segundos...")
            sleep(espera)

        except Exception as erro:
            erros += 1
            log("")
            log(f"ERRO com {nome}")
            log(str(erro))
            fechar_dialogo_nativo()
            continue

    limpar_progresso()
    finalizar_log(total, enviados, erros)

    input("Pressione ENTER para fechar.")
    driver.quit()


if __name__ == "__main__":
    main()
