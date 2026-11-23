from config import ARQUIVO_IMAGEM, ARQUIVO_VIDEO


def _perguntar(pergunta, respostas):
    """Repete a pergunta ate receber uma das respostas aceitas."""
    while True:
        resposta = input(pergunta).strip().upper()
        if resposta in respostas:
            return respostas[resposta]
        print("Opção inválida.")


def _perguntar_numero(pergunta, minimo, maximo):
    while True:
        try:
            numero = int(input(pergunta).strip())
        except ValueError:
            numero = 0
        if minimo <= numero <= maximo:
            return numero
        print(f"Opção inválida. Digite um número entre {minimo} e {maximo}.")


def _pedir_contato(total):
    """Aceita respostas como 32 ou 32/2050 e retorna o indice do contato."""
    while True:
        entrada = input("Informe o contato (ex.: 32 ou 32/2050): ").strip()
        try:
            numero = int(entrada.split("/", 1)[0].strip())
        except ValueError:
            print("Contato inválido. Informe um número da lista.")
            continue
        if 1 <= numero <= total:
            return numero - 1
        print(f"Informe um contato entre 1 e {total}.")


def escolher_midia():
    # A campanha pode usar um unico arquivo de midia ou somente texto.
    print()
    print("=" * 60)
    print("O que você quer enviar nesta campanha?")
    print("[1] Imagem")
    print("[2] Vídeo")
    print("[3] Nenhum (somente texto)")
    print("=" * 60)

    return _perguntar(
        "Digite 1, 2 ou 3 e pressione ENTER: ",
        {"1": ARQUIVO_IMAGEM, "2": ARQUIVO_VIDEO, "3": None},
    )


def escolher_coluna_contato(contatos):
    """Define qual coluna da planilha contem o telefone do WhatsApp."""
    quantidade_colunas = len(contatos[0])
    print()
    print(f"Em qual coluna está o contato do WhatsApp? (1 a {quantidade_colunas})")
    return _perguntar_numero(
        "Digite o número da coluna: ",
        1,
        quantidade_colunas,
    )


def escolher_prefixo_brasil():
    """Define se os telefones ja possuem o codigo do Brasil (55)."""
    print()
    print("Os contatos já começam com 55 (código do Brasil)?")
    print("Exemplo sem 55: 85999999999 -> será usado 5585999999999")
    return not _perguntar(
        "Digite S para sim ou N para não: ",
        {"S": True, "SIM": True, "N": False, "NAO": False, "NÃO": False},
    )


def escolher_quantidade_variaveis():
    """Define quantos placeholders {varN} serao usados na mensagem."""
    print()
    print("Quantas variáveis a mensagem deve usar? (1 a 5)")
    return _perguntar_numero("Digite uma quantidade: ", 1, 5)


def perguntar_campanha_nova():
    """Retorna True para campanha nova e False para manter o progresso."""
    print()
    print("Esta é uma nova chamada/campanha?")
    print("SIM: ignora o progresso anterior e envia para todos.")
    print("NÃO: mantém o progresso e mostra as opções de continuação.")
    return _perguntar(
        "Digite SIM ou NÃO: ",
        {"SIM": True, "S": True, "NAO": False, "NÃO": False, "N": False},
    )


def escolher_inicio_nova_campanha(total):
    """Retorna o indice do primeiro contato de uma campanha nova."""
    print()
    print("Como deseja continuar?")
    print("[1] Executar desde o início")
    print("[2] Escolher um contato")
    if _perguntar("Digite 1 ou 2 e pressione ENTER: ", {"1": 1, "2": 2}) == 1:
        return 0
    return _pedir_contato(total)


def escolher_inicio_retomada(total, progresso, indice_continuar):
    """Retorna o indice de onde a campanha salva deve continuar."""
    print()
    print("=" * 60)
    print("PROGRESSO ENCONTRADO")
    print("=" * 60)
    print(f"Último contato : {progresso.nome}")
    print(f"Telefone.......: {progresso.telefone}")
    print(f"Índice.........: {progresso.ultimo_indice + 1}/{total}")
    print(f"Enviados.......: {len(progresso.enviados)}")
    print(f"Falhas.........: {len(progresso.falhos)}")
    print(f"Data...........: {progresso.data_hora}")
    print()
    print("Como deseja continuar?")
    print("[1] Percorrer desde o primeiro contato (pula quem já recebeu)")
    print("[2] Continuar de onde parou")
    print("[3] Escolher um contato")

    escolha = _perguntar(
        "Digite 1, 2 ou 3 e pressione ENTER: ",
        {"1": 1, "2": 2, "3": 3},
    )
    if escolha == 1:
        return 0
    if escolha == 2:
        return indice_continuar
    return _pedir_contato(total)


def mostrar_triagem(selecao):
    """Informa quem ficou fora da campanha e por que."""
    print()
    print("=" * 60)
    print(f"Aptos a receber..............: {len(selecao.destinatarios)}")
    grupos = (
        ("Telefone inválido ou vazio...", selecao.invalidos),
        ("Não existem no WhatsApp......", selecao.inexistentes),
        ("Pediram para não receber.....", selecao.descadastrados),
        ("Telefone repetido............", selecao.duplicados),
        ("Variável em branco...........", selecao.incompletos),
    )
    for rotulo, posicoes in grupos:
        if posicoes:
            amostra = ", ".join(str(posicao) for posicao in posicoes[:15])
            sufixo = "..." if len(posicoes) > 15 else ""
            print(f"{rotulo}: {len(posicoes)} (contatos {amostra}{sufixo})")
    print("=" * 60)


def perguntar_remover_inexistentes(quantidade):
    """Pede confirmacao antes de alterar a planilha do usuario."""
    print()
    print(
        f"O WhatsApp informou que {quantidade} contato(s) da planilha "
        "não existem."
    )
    print("Eles já estão fora da campanha mesmo que continuem na planilha.")
    print("Antes de remover, uma cópia de segurança da planilha será criada.")
    return _perguntar(
        "Remover esses contatos da planilha? Digite S ou N: ",
        {"S": True, "SIM": True, "N": False, "NAO": False, "NÃO": False},
    )


def confirmar_envio(fila, midia, total_previsto):
    """Mostra a primeira mensagem real e exige uma confirmacao explicita."""
    print()
    print("=" * 60)
    print("PRÉVIA DA PRIMEIRA MENSAGEM")
    print(f"Para: {fila[0].nome} ({fila[0].telefone})")
    print(f"Mídia: {midia.name if midia else 'nenhuma'}")
    print("-" * 60)
    print(fila[0].texto)
    print("-" * 60)
    print(f"Serão enviadas mensagens para {total_previsto} contato(s).")
    print("=" * 60)
    return _perguntar(
        "Digite ENVIAR para começar ou N para cancelar: ",
        {"ENVIAR": True, "N": False, "NAO": False, "NÃO": False},
    )
