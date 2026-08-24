from time import sleep
from random import randint
import re
import traceback

# Esta verificacao roda antes dos imports que dependem de bibliotecas instaladas.
from core.preparar_ambiente import verificar_dependencias
from config import CHROME_BINARY

if not verificar_dependencias(CHROME_BINARY):
    raise SystemExit(1)

from core.estado import carregar_progresso, salvar_progresso, limpar_progresso
from core.preparar_ambiente import preparar, finalizar_chrome, remover_lock
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
    MENSAGENS_POR_LOTE,
    PAUSA_ENTRE_LOTES_SEGUNDOS,
    TEMPO_ENTRE_MENSAGENS_MIN,
    TEMPO_ENTRE_MENSAGENS_MAX,
)

# Depois dessa quantidade, a sessao do navegador e reiniciada para
# reprocessar somente os contatos que falharam.
LIMITE_ERROS_CONSECUTIVOS = 20


def escolher_midia():
    # A campanha usa um unico arquivo de midia por execucao.
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


def escolher_quantidade_variaveis():
    """Define quantos placeholders {varN} serao usados na mensagem."""
    print()
    print("Quantas variáveis a mensagem deve usar? (1 a 5)")

    while True:
        try:
            quantidade = int(input("Digite uma quantidade: ").strip())
        except ValueError:
            quantidade = 0

        if 1 <= quantidade <= 5:
            print(f"Serão usadas {quantidade} variável(is).")
            return quantidade

        print("Opção inválida. Digite um número entre 1 e 5.")


def escolher_coluna_contato(contatos):
    """Define qual coluna da planilha contem o telefone do WhatsApp."""
    print()
    print("Em qual coluna está o contato do WhatsApp?")
    quantidade_colunas = len(contatos[0])
    for indice in range(1, quantidade_colunas + 1):
        print(f"[{indice}] Coluna {indice}")

    while True:
        try:
            coluna = int(input("Digite o número da coluna: ").strip())
        except ValueError:
            coluna = 0

        if 1 <= coluna <= quantidade_colunas:
            print(
                f"O contato do WhatsApp será a coluna {coluna}: "
                f"Coluna {coluna}."
            )
            return coluna

        print(
            f"Opção inválida. Digite um número entre 1 e "
            f"{quantidade_colunas}."
        )


def escolher_prefixo_brasil():
    """Define se os telefones ja possuem o codigo do Brasil (55)."""
    print()
    print("Os contatos já começam com 55 (código do Brasil)?")
    print("Exemplo sem 55: 85999999999 -> será usado 5585999999999")

    while True:
        escolha = input("Digite S para sim ou N para não: ").strip().upper()
        if escolha in {"S", "SIM"}:
            print("Os contatos serão usados com o 55 já informado.")
            return False
        if escolha in {"N", "NAO", "NÃO"}:
            print("O código 55 será acrescentado aos contatos.")
            return True
        print("Opção inválida. Digite S ou N.")


def preparar_telefone(valor, acrescentar_codigo_brasil):
    """Remove caracteres extras e garante o codigo 55 quando necessario."""
    telefone_bruto = str(valor).strip()
    if telefone_bruto.endswith(".0"):
        telefone_bruto = telefone_bruto[:-2]
    telefone = re.sub(r"\D", "", telefone_bruto)
    if acrescentar_codigo_brasil and not telefone.startswith("55"):
        telefone = "55" + telefone
    return telefone


def escolher_inicio(contatos, estado):
    """Escolhe onde continuar e recupera os contadores salvos."""
    if not estado:
        return 0, 0, 0

    total = len(contatos)
    proximo_indice = estado["ultimo_indice"] + 1
    enviados = estado.get("enviados", 0)
    erros = estado.get("erros", 0)

    print()
    print("=" * 60)
    print("PROGRESSO ENCONTRADO")
    print("=" * 60)
    print(f'Último contato : {estado["nome"]}')
    print(f'Telefone.......: {estado["telefone"]}')
    print(f'Índice.........: {estado["ultimo_indice"] + 1}/{total}')
    print(f'Enviados.......: {enviados}')
    print(f'Erros..........: {erros}')
    print(f'Data...........: {estado["data_hora"]}')
    print()
    print("Como deseja continuar?")
    print("[1] Executar desde o início")
    print("[2] Continuar de onde parou")
    print("[3] Escolher um contato")

    while True:
        escolha = input("Digite 1, 2 ou 3 e pressione ENTER: ").strip()

        if escolha == "1":
            return 0, 0, 0

        if escolha == "2":
            # Falhas pendentes tem prioridade sobre o proximo indice normal.
            falhos_indices = estado.get("falhos_indices", [])
            if falhos_indices:
                return min(falhos_indices), enviados, erros
            return min(proximo_indice, total), enviados, erros

        if escolha == "3":
            while True:
                entrada = input(
                    "Informe o contato (ex.: 32 ou 32/2050): "
                ).strip()
                try:
                    numero = int(entrada.split("/", 1)[0].strip())
                except ValueError:
                    print("Contato inválido. Informe um número da lista.")
                    continue

                if 1 <= numero <= total:
                    return numero - 1, enviados, erros

                print(f"Informe um contato entre 1 e {total}.")

        print("Opção inválida. Digite 1, 2 ou 3.")


def main():
    # Valida a entrada antes de abrir o navegador ou iniciar a campanha.
    arquivo_midia = escolher_midia()

    if not arquivo_midia.exists():
        print()
        print(f"ERRO: arquivo não encontrado: {arquivo_midia}")
        print("Coloque o arquivo na pasta 'dados' e rode de novo.")
        input("Pressione ENTER para fechar este terminal.")
        return

    # Fecha instancias antigas, remove locks e prepara o Selenium.
    preparar()
    iniciar_log()
    driver = iniciar_chrome()
    abrir_whatsapp_web(driver)
    contatos = ler_contatos()
    coluna_contato = escolher_coluna_contato(contatos)
    acrescentar_codigo_brasil = escolher_prefixo_brasil()
    quantidade_variaveis = escolher_quantidade_variaveis()

    # O estado permite continuar uma campanha interrompida sem duplicar envios.
    estado = carregar_progresso()
    indice_inicial, enviados, erros = escolher_inicio(contatos, estado)

    if estado:
        log("")
        log(f"Execução iniciada no contato {indice_inicial + 1}...")

    mensagem_base = carregar_mensagem()
    total = len(contatos)
    enviados_indices = set(estado.get("enviados_indices", [])) if estado else set()
    falhos_indices = set(estado.get("falhos_indices", [])) if estado else set()
    erros_consecutivos = 0

    print()
    print("=" * 60)
    print(f"Foram encontrados {total} contatos.")
    print("=" * 60)

    # A fila pode ser a sequencia normal ou a lista de falhas apos uma recuperacao.
    indices_para_processar = list(range(indice_inicial, total))
    while indices_para_processar:
        indice = indices_para_processar.pop(0)

        # Um contato enviado anteriormente nao deve receber a mesma campanha de novo.
        if indice in enviados_indices:
            log(f"Pulando {indice + 1}/{total}: mensagem já enviada.")
            continue

        contato = contatos[indice]
        nome = str(list(contato.values())[0]).strip()
        telefone = preparar_telefone(
            list(contato.values())[coluna_contato - 1],
            acrescentar_codigo_brasil,
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
            # Cada contato segue a ordem: abrir conversa, anexar midia e enviar texto.
            abrir_conversa(driver, telefone)

            texto = personalizar_mensagem(
                mensagem_base,
                contato,
                quantidade_variaveis,
                coluna_contato,
            )

            anexar_midia(driver, arquivo_midia)
            enviar_midia(driver)
            escrever_texto(driver, texto)
            enviar_texto(driver)

            enviados += 1
            enviados_indices.add(indice)
            falhos_indices.discard(indice)
            salvar_progresso(
                indice,
                nome,
                telefone,
                enviados,
                erros,
                enviados_indices,
                falhos_indices,
            )
            erros_consecutivos = 0

            espera = randint(
                TEMPO_ENTRE_MENSAGENS_MIN,
                TEMPO_ENTRE_MENSAGENS_MAX,
            )

            log("Mensagem enviada com sucesso.")
            log(f"Aguardando {espera} segundos...")
            sleep(espera)

            ainda_ha_envios = any(
                restante not in enviados_indices
                for restante in indices_para_processar
            )
            if enviados % MENSAGENS_POR_LOTE == 0 and ainda_ha_envios:
                pausa_minutos = PAUSA_ENTRE_LOTES_SEGUNDOS // 60
                log(
                    f"{MENSAGENS_POR_LOTE} mensagens enviadas. "
                    f"Pausa de {pausa_minutos} minutos antes do próximo lote."
                )
                sleep(PAUSA_ENTRE_LOTES_SEGUNDOS)

        except Exception as erro:
            # Salva a falha imediatamente para que uma interrupcao nao perca a fila.
            erros += 1
            falhos_indices.add(indice)
            log("")
            log(f"ERRO com {nome}")
            log(str(erro))
            fechar_dialogo_nativo()
            salvar_progresso(
                indice,
                nome,
                telefone,
                enviados,
                erros,
                enviados_indices,
                falhos_indices,
            )

            erros_consecutivos += 1
            if erros_consecutivos >= LIMITE_ERROS_CONSECUTIVOS:
                # A nova sessao recebe a fila ordenada dos contatos que falharam.
                log(
                    f"{LIMITE_ERROS_CONSECUTIVOS} erros consecutivos. "
                    "Reiniciando o Chrome para tentar novamente os falhos."
                )
                driver.quit()
                finalizar_chrome()
                remover_lock()
                driver = iniciar_chrome()
                abrir_whatsapp_web(driver)
                indices_para_processar = sorted(falhos_indices)
                erros_consecutivos = 0
            continue

    # Mantem o estado para uma proxima execucao enquanto houver falhas pendentes.
    if falhos_indices:
        log(
            f"Ainda existem {len(falhos_indices)} contato(s) com erro. "
            "O progresso foi mantido em estado.json."
        )
    else:
        limpar_progresso()
    finalizar_log(total, enviados, erros)

    input("Pressione ENTER para fechar.")
    driver.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        # Mantem o terminal aberto para que uma falha no computador do usuario
        # possa ser lida, mesmo quando o exe e aberto por duplo clique.
        print("\nERRO FATAL: o WhatsAppBot nao conseguiu continuar.")
        print(f"Detalhe: {erro}")
        traceback.print_exc()

        try:
            log("ERRO FATAL no programa:")
            log(traceback.format_exc())
        except Exception:
            pass

        input("\nPressione ENTER para fechar este terminal.")
