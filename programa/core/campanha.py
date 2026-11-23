import time
import traceback
from collections import deque
from datetime import datetime
from random import randint

from config import (
    LIMITE_ERROS_CONSECUTIVOS,
    LIMITE_REINICIOS_SEM_SUCESSO,
    MENSAGENS_POR_LOTE,
    PAUSA_ENTRE_LOTES_SEGUNDOS,
    TEMPO_ENTRE_MENSAGENS_MAX,
    TEMPO_ENTRE_MENSAGENS_MIN,
)
from core.erros import ErroEstado, NumeroInvalido, SessaoPerdida
from core.estado import salvar_progresso
from core.horario import (
    ajustar_fim_da_espera,
    dormir_ate,
    em_pausa_noturna,
    fim_da_pausa,
)
from core.inexistentes import registrar_inexistente
from core.logger import log

PAUSA_APOS_ENVIAR_MIDIA = 4


class Campanha:
    """Percorre a fila de destinatarios e decide o que fazer a cada resultado."""

    def __init__(
        self,
        destinatarios,
        fila,
        progresso,
        canal,
        midia,
        total_contatos,
        intervalo=(TEMPO_ENTRE_MENSAGENS_MIN, TEMPO_ENTRE_MENSAGENS_MAX),
        tamanho_lote=MENSAGENS_POR_LOTE,
        pausa_lote=PAUSA_ENTRE_LOTES_SEGUNDOS,
        limite_erros=LIMITE_ERROS_CONSECUTIVOS,
        limite_reinicios=LIMITE_REINICIOS_SEM_SUCESSO,
        agora=datetime.now,
        dormir=time.sleep,
    ):
        self.destinatarios = destinatarios
        self.fila = deque(fila)
        self.progresso = progresso
        self.canal = canal
        self.midia = midia
        self.total_contatos = total_contatos
        self.intervalo = intervalo
        self.tamanho_lote = tamanho_lote
        self.pausa_lote = pausa_lote
        self.limite_erros = limite_erros
        self.limite_reinicios = limite_reinicios
        self.agora = agora
        self.dormir = dormir
        self.falhas_seguidas = []
        self.reinicios_sem_sucesso = 0
        self.varredura_final = False

    def executar(self):
        """Retorna True se a fila terminou e False se a campanha foi interrompida."""
        self._respeitar_pausa_de_lote_salva()

        while True:
            if not self.fila and not self._iniciar_varredura_final():
                return True

            destinatario = self.fila.popleft()
            if self._resolvido(destinatario):
                continue

            if not self._processar(destinatario):
                return False

    def _resolvido(self, destinatario):
        return (
            destinatario.telefone in self.progresso.enviados
            or destinatario.telefone in self.progresso.invalidos
        )

    def _falhas_pendentes(self):
        return [
            destinatario
            for destinatario in self.destinatarios
            if destinatario.telefone in self.progresso.falhos
        ]

    def _iniciar_varredura_final(self):
        if self.varredura_final:
            return False

        self.varredura_final = True
        pendentes = self._falhas_pendentes()
        if not pendentes:
            return False

        self.fila.extend(pendentes)
        self.falhas_seguidas.clear()
        log(
            "Iniciando varredura final dos contatos que obtiveram erro: "
            f"{len(pendentes)} contato(s)."
        )
        return True

    def _ha_trabalho_restante(self):
        if any(not self._resolvido(item) for item in self.fila):
            return True
        return not self.varredura_final and bool(self._falhas_pendentes())

    def _anotar_contato_atual(self, destinatario):
        self.progresso.ultimo_indice = destinatario.indice
        self.progresso.nome = destinatario.nome
        self.progresso.telefone = destinatario.telefone

    def _processar(self, destinatario):
        """Trata um contato; retorna False se a campanha precisa parar."""
        titulo = (
            f"[{destinatario.indice + 1}/{self.total_contatos}] "
            f"{destinatario.nome}"
        )
        log("")
        log("=" * 60)
        log(titulo)
        log("=" * 60)

        self._aguardar_fim_da_pausa_noturna()

        try:
            confirmado = self._enviar(destinatario)
        except ErroEstado:
            raise
        except NumeroInvalido as erro:
            self._registrar_numero_invalido(destinatario, erro)
            return True
        except SessaoPerdida as erro:
            self._registrar_falha(destinatario, erro)
            log("A sessão do navegador foi perdida.")
            return self._recuperar_sessao([destinatario])
        except Exception as erro:
            self._registrar_falha(destinatario, erro)
            self.falhas_seguidas.append(destinatario)
            if len(self.falhas_seguidas) >= self.limite_erros:
                log(f"{self.limite_erros} erros seguidos.")
                return self._recuperar_sessao(list(self.falhas_seguidas))
            return True

        self._registrar_sucesso(destinatario, confirmado)
        self._esperar_proximo_envio()
        return True

    def _enviar(self, destinatario):
        progresso = self.progresso
        self.canal.abrir_conversa(destinatario.telefone)

        # Numa nova tentativa, quem ja recebeu a midia recebe somente o texto.
        if (
            self.midia is not None
            and destinatario.telefone not in progresso.midia_enviada
        ):
            self.canal.anexar_midia(self.midia)
            self.canal.enviar_midia()
            progresso.midia_enviada.add(destinatario.telefone)
            self._anotar_contato_atual(destinatario)
            salvar_progresso(progresso)
            self.dormir(PAUSA_APOS_ENVIAR_MIDIA)

        return self.canal.enviar_texto(destinatario.texto)

    def _registrar_sucesso(self, destinatario, confirmado):
        progresso = self.progresso
        telefone = destinatario.telefone
        progresso.enviados.add(telefone)
        progresso.falhos.discard(telefone)
        progresso.midia_enviada.discard(telefone)
        if not confirmado:
            progresso.nao_confirmados.add(telefone)
        self._anotar_contato_atual(destinatario)
        salvar_progresso(progresso)

        self.falhas_seguidas.clear()
        self.reinicios_sem_sucesso = 0
        log("Mensagem enviada com sucesso.")

    def _registrar_numero_invalido(self, destinatario, erro):
        progresso = self.progresso
        progresso.invalidos.add(destinatario.telefone)
        progresso.falhos.discard(destinatario.telefone)
        self._anotar_contato_atual(destinatario)
        salvar_progresso(progresso)
        registrar_inexistente(destinatario.telefone, str(erro))

        # O WhatsApp respondeu, portanto a sessao esta saudavel.
        self.falhas_seguidas.clear()
        log(f"Número inexistente, não será tentado de novo: {erro}")

    def _registrar_falha(self, destinatario, erro):
        progresso = self.progresso
        progresso.erros += 1
        progresso.falhos.add(destinatario.telefone)
        self._anotar_contato_atual(destinatario)
        log("")
        log(f"ERRO com {destinatario.nome}")
        log(f"{type(erro).__name__}: {erro}")
        log("".join(traceback.format_exception(erro)))
        salvar_progresso(progresso)

    def _recuperar_sessao(self, bloco):
        """Reinicia o Chrome e recoloca o bloco na fila, dentro do limite."""
        while self.reinicios_sem_sucesso < self.limite_reinicios:
            self.reinicios_sem_sucesso += 1
            log(
                "Reiniciando o Chrome (tentativa "
                f"{self.reinicios_sem_sucesso}/{self.limite_reinicios})."
            )
            try:
                self.canal.reiniciar()
            except Exception as erro:
                log(f"O Chrome não reiniciou: {type(erro).__name__}: {erro}")
                continue

            self.fila.extendleft(reversed(bloco))
            self.falhas_seguidas.clear()
            return True

        log(
            "Campanha interrompida: o problema continuou depois de "
            f"{self.limite_reinicios} reinício(s) sem nenhum envio. "
            "O progresso foi mantido; corrija a causa e escolha continuar."
        )
        return False

    def _aguardar_fim_da_pausa_noturna(self):
        agora = self.agora()
        if em_pausa_noturna(agora):
            retomar = fim_da_pausa(agora)
            log(f"Pausa noturna ativa. Retomando às {retomar:%H:%M}.")
            dormir_ate(retomar, self.agora, self.dormir)

    def _respeitar_pausa_de_lote_salva(self):
        progresso = self.progresso
        if not progresso.retomar_apos:
            return

        retomar = datetime.fromisoformat(progresso.retomar_apos)
        if retomar > self.agora():
            log(f"Pausa entre lotes em andamento. Retomando em {retomar:%d/%m %H:%M}.")
            dormir_ate(retomar, self.agora, self.dormir)
        progresso.retomar_apos = None
        salvar_progresso(progresso)

    def _esperar_proximo_envio(self):
        if not self._ha_trabalho_restante():
            return

        espera = randint(*self.intervalo)
        retomar = ajustar_fim_da_espera(self.agora(), espera)
        log(f"Próximo envio às {retomar:%d/%m %H:%M:%S}.")
        dormir_ate(retomar, self.agora, self.dormir)

        if len(self.progresso.enviados) % self.tamanho_lote == 0:
            self._fazer_pausa_de_lote()

    def _fazer_pausa_de_lote(self):
        progresso = self.progresso
        retomar = ajustar_fim_da_espera(self.agora(), self.pausa_lote)

        # A pausa fica salva para que reiniciar o programa nao a encurte.
        progresso.retomar_apos = retomar.isoformat()
        salvar_progresso(progresso)
        log(
            f"{self.tamanho_lote} mensagens do lote enviadas. "
            f"Pausa até {retomar:%d/%m %H:%M}."
        )
        dormir_ate(retomar, self.agora, self.dormir)
        progresso.retomar_apos = None
        salvar_progresso(progresso)
