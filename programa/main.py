import traceback
from datetime import datetime

# Esta verificacao roda antes dos imports que dependem de bibliotecas instaladas.
from core.preparar_ambiente import verificar_dependencias
from config import CHROME_BINARY

if not verificar_dependencias(CHROME_BINARY):
    raise SystemExit(1)

from core import menu
from core.campanha import Campanha
from core.destinatarios import (
    carregar_descadastro,
    montar_destinatarios,
    telefones_por_indice,
)
from core.envio import limpar_uploads, preparar_copia_local
from core.erros import EntradaInvalida
from core.estado import (
    Progresso,
    arquivar_progresso,
    carregar_estado,
    progresso_de_dados,
)
from core.excel import impressao_digital, ler_contatos
from core.horario import dormir_ate, em_pausa_noturna, fim_da_pausa
from core.inexistentes import carregar_inexistentes, oferecer_remocao
from core.logger import finalizar_log, iniciar_log, log
from core.mensagem import carregar_mensagem, validar_variaveis
from core.preparar_ambiente import preparar
from core.whatsapp import CanalWhatsApp


def falhas_pendentes(selecao, progresso):
    """Lista os destinatarios atuais que ainda precisam de nova tentativa."""
    return [
        destinatario
        for destinatario in selecao.destinatarios
        if destinatario.telefone in progresso.falhos
    ]


def indice_para_continuar(selecao, progresso):
    """Falhas pendentes tem prioridade sobre o proximo contato da lista."""
    indices_falhos = [
        destinatario.indice
        for destinatario in falhas_pendentes(selecao, progresso)
    ]
    return min(indices_falhos + [progresso.ultimo_indice + 1])


def carregar_progresso_salvo(contatos, coluna, acrescentar_55):
    """Le o progresso; o formato antigo so faz sentido com a planilha intacta."""
    dados = carregar_estado()
    if dados is None:
        return None
    return progresso_de_dados(
        dados,
        telefones_por_indice(contatos, coluna, acrescentar_55),
    )


def definir_progresso(total, selecao, progresso, assinatura):
    """Retorna (progresso, indice inicial, se a campanha e nova)."""
    campanha_nova = menu.perguntar_campanha_nova()

    if campanha_nova:
        return Progresso(), menu.escolher_inicio_nova_campanha(total), True

    if progresso is None:
        print("Nenhum progresso salvo. A campanha começará do início.")
        return Progresso(), 0, False

    if progresso.planilha_sha256 and progresso.planilha_sha256 != assinatura:
        print()
        print(
            "AVISO: a planilha mudou desde a última execução. Quem já recebeu "
            "continua sendo pulado pelo número de telefone."
        )

    inicio = menu.escolher_inicio_retomada(
        total,
        progresso,
        indice_para_continuar(selecao, progresso),
    )
    return progresso, inicio, False


def aguardar_fim_da_pausa_noturna():
    agora = datetime.now()
    if em_pausa_noturna(agora):
        retomar = fim_da_pausa(agora)
        log(f"Pausa noturna ativa. Retomando às {retomar:%H:%M}.")
        dormir_ate(retomar)


def executar_campanha(selecao, fila, progresso, midia, contatos, coluna, acrescentar_55):
    """Abre o navegador somente depois que a entrada foi validada e confirmada."""
    aguardar_fim_da_pausa_noturna()
    preparar()
    iniciar_log()

    canal = CanalWhatsApp()
    copia_midia = preparar_copia_local(midia) if midia else None
    try:
        canal.iniciar()
        concluida = Campanha(
            selecao.destinatarios,
            fila,
            progresso,
            canal,
            copia_midia,
            len(contatos),
        ).executar()

        finalizar_log(len(fila), progresso)
        oferecer_remocao(contatos, coluna, acrescentar_55, progresso)
        if concluida and not falhas_pendentes(selecao, progresso):
            arquivar_progresso()
        else:
            log("O progresso foi mantido em estado.json para continuar depois.")

        input("Pressione ENTER para fechar.")
    finally:
        canal.encerrar()
        limpar_uploads()


def main():
    # Tudo e validado antes de fechar ou abrir qualquer navegador.
    midia = menu.escolher_midia()
    if midia is not None and not midia.exists():
        raise EntradaInvalida(
            f"Arquivo não encontrado: {midia}. "
            "Coloque o arquivo na pasta 'dados' e rode de novo."
        )

    mensagem = carregar_mensagem()
    contatos = ler_contatos()
    coluna = menu.escolher_coluna_contato(contatos)
    acrescentar_55 = menu.escolher_prefixo_brasil()
    quantidade_variaveis = menu.escolher_quantidade_variaveis()
    validar_variaveis(mensagem, quantidade_variaveis, len(contatos[0]) - 1)

    progresso_salvo = carregar_progresso_salvo(contatos, coluna, acrescentar_55)
    contatos = oferecer_remocao(
        contatos,
        coluna,
        acrescentar_55,
        progresso_salvo,
    )

    selecao = montar_destinatarios(
        contatos,
        mensagem,
        coluna,
        acrescentar_55,
        quantidade_variaveis,
        carregar_descadastro(),
        carregar_inexistentes(),
    )
    menu.mostrar_triagem(selecao)

    assinatura = impressao_digital()
    progresso, inicio, campanha_nova = definir_progresso(
        len(contatos),
        selecao,
        progresso_salvo,
        assinatura,
    )

    fila = [
        destinatario
        for destinatario in selecao.destinatarios
        if destinatario.indice >= inicio
        and destinatario.telefone not in progresso.enviados
        and destinatario.telefone not in progresso.invalidos
    ]
    if not fila:
        print("Não há contatos pendentes para esta campanha.")
        input("Pressione ENTER para fechar.")
        return

    # A varredura final tambem alcanca falhas anteriores ao contato escolhido.
    telefones_na_fila = {destinatario.telefone for destinatario in fila}
    total_previsto = len(fila) + sum(
        destinatario.telefone not in telefones_na_fila
        for destinatario in falhas_pendentes(selecao, progresso)
    )

    if not menu.confirmar_envio(fila, midia, total_previsto):
        print("Envio cancelado. Nada foi alterado.")
        input("Pressione ENTER para fechar.")
        return

    # So descarta o historico anterior depois da confirmacao do usuario.
    if campanha_nova:
        arquivar_progresso()
    progresso.planilha_sha256 = assinatura

    executar_campanha(
        selecao,
        fila,
        progresso,
        midia,
        contatos,
        coluna,
        acrescentar_55,
    )


if __name__ == "__main__":
    # Mantem o terminal aberto para que uma falha possa ser lida, mesmo
    # quando o exe e aberto por duplo clique.
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário. O progresso já está salvo.")
        input("Pressione ENTER para fechar este terminal.")
    except EntradaInvalida as erro:
        print(f"\nERRO: {erro}")
        input("\nPressione ENTER para fechar este terminal.")
    except Exception as erro:
        print("\nERRO FATAL: o WhatsAppBot nao conseguiu continuar.")
        print(f"Detalhe: {erro}")
        traceback.print_exc()
        log("ERRO FATAL no programa:")
        log(traceback.format_exc())
        input("\nPressione ENTER para fechar este terminal.")
