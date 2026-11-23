# WhatsAppBot

Bot para envio automatizado de mensagens, imagens ou vídeos pelo WhatsApp Web usando Selenium e Google Chrome.

> Use este projeto somente com contatos que autorizaram o recebimento das mensagens. A automação do WhatsApp Web viola os termos do WhatsApp e pode levar ao bloqueio do número; para campanhas de marketing, a alternativa oficial é a WhatsApp Business Platform. Respeite a LGPD e os pedidos de descadastro.

## Funcionalidades

- Envio de imagem, vídeo ou somente texto, com mensagem personalizada.
- Variáveis `{var1}` a `{var5}`, definidas pela posição das colunas da planilha.
- Triagem antes do envio: telefones inválidos, repetidos, descadastrados e variáveis em branco ficam de fora.
- Prévia da primeira mensagem e confirmação antes de abrir o navegador.
- Progresso identificado pelo telefone, à prova de mudanças na ordem da planilha.
- Quando a mídia já foi enviada e o texto falha, a nova tentativa envia somente o texto.
- Pausa noturna e pausa entre lotes, que continua valendo se o programa for reiniciado.
- Números sem WhatsApp são marcados e não voltam para a fila.
- Reinício automático do Chrome e parada segura quando o problema persiste.

## Estrutura

```text
WhatsAppBot/
├── dados/                   # não versionado: dados da campanha
│   ├── contatos.xlsx
│   ├── mensagem.txt
│   ├── descadastro.txt      # criado automaticamente
│   ├── numeros_inexistentes.txt # preenchido pelo bot
│   ├── imagem.png           # opcional
│   └── video.mp4            # opcional
├── programa/
│   ├── main.py              # fluxo principal
│   ├── config.py            # caminhos, tempos e limites
│   ├── main.spec            # receita do executável
│   ├── core/
│   │   ├── campanha.py      # fila, novas tentativas e pausas
│   │   ├── destinatarios.py # triagem da planilha e descadastro
│   │   ├── envio.py         # ações no WhatsApp Web
│   │   ├── seletores.py     # tudo que depende da página do WhatsApp
│   │   ├── estado.py        # progresso salvo
│   │   ├── menu.py          # perguntas no terminal
│   │   └── ...
│   ├── scripts/
│   └── tests/
├── runtime/                 # progresso, logs e capturas de tela
├── requirements.txt
└── README.md
```

## Requisitos

- Windows.
- Python 3.10 ou superior.
- Google Chrome instalado.
- Uma sessão do WhatsApp Web no perfil de automação.

Instalação das bibliotecas, nas versões testadas:

```powershell
python -m pip install -r requirements.txt
```

As versões ficam fixas em `requirements.txt` e o programa não se atualiza sozinho.

## Configuração da planilha

O arquivo deve ser salvo como `dados/contatos.xlsx`.

A primeira linha é tratada como título e ignorada. As colunas são identificadas somente pela posição escolhida no terminal.

| Nome | Nome indicado | contato | titulo |
|---|---|---|---|
| Ana | Bruno | 5581999999999 | Curso de Python |

Ao escolher a coluna `3` como telefone:

- a coluna `1` será `{var1}`;
- a coluna `2` será `{var2}`;
- a coluna `3` será usada somente para abrir o WhatsApp;
- a coluna `4` será `{var3}`.

O programa pergunta se os números já começam com `55`:

- Respondendo `N`, números de 10 ou 11 dígitos recebem o `55`. A decisão é feita pelo tamanho, então o DDD 55 funciona corretamente.
- Respondendo `S`, o número precisa já estar completo.

Exemplo: `(85) 99999-9999` respondendo `N` vira `5585999999999`. Números fora do padrão brasileiro são listados na triagem e não recebem mensagem.

## Configuração da mensagem

Edite `dados/mensagem.txt` usando `{var1}` a `{var5}` na ordem das colunas, desconsiderando a coluna do telefone:

```text
Olá {var1}, tudo bem?
Você foi indicado por {var2}.
```

A campanha não começa se a mensagem usar uma variável sem coluna correspondente. Contatos com uma variável usada em branco ficam de fora e aparecem na triagem.

## Descadastro

Quem responder pedindo para sair deve ser adicionado manualmente em `dados/descadastro.txt`, um telefone por linha, com ou sem `55`. O bot não lê as respostas das conversas. O arquivo é consultado antes de cada campanha, e quem estiver nele nunca recebe mensagens.

## Números que não existem

Quando o WhatsApp avisa que um número não existe, o bot não tenta de novo e registra o número e o texto do aviso em `dados/numeros_inexistentes.txt`. A partir daí, esse número fica fora de todas as campanhas e não conta nos envios nem nas pausas de lote.

No fim da campanha e ao iniciar a próxima, o programa pergunta se deve remover esses contatos da planilha. Respondendo `S`, ele cria `dados/contatos_backup_*.xlsx`, remove as linhas, confere o resultado e só então substitui a planilha. A planilha precisa estar fechada no Excel.

Tempo esgotado ao abrir a conversa não é tratado como número inexistente, porque também acontece com internet lenta ou instabilidade do WhatsApp. Nesses casos, o log registra `Avisos na tela: [...]`. Se aparecer ali uma frase do WhatsApp que o bot não reconheceu, acrescente-a em `AVISO_PROBLEMA` em `programa/core/seletores.py`.

## Execução

```powershell
cd P:\DEV\Python\WhatsAppBot\programa
python main.py
```

Na ordem, o programa pergunta a mídia, a coluna do telefone, o código `55`, a quantidade de variáveis e se a campanha é nova. Depois mostra a triagem e a prévia, e só abre o navegador se você digitar `ENVIAR`.

**Rode apenas uma cópia por vez, mesmo em computadores diferentes.** Duas execuções usando a mesma pasta `runtime/` sobrescrevem o progresso uma da outra e causam envios duplicados.

Na primeira execução, escaneie o QR Code na janela do Chrome. O perfil da automação fica em `%LOCALAPPDATA%\WhatsAppBot\chrome_automacao`, separado do seu Chrome pessoal, que nunca é fechado pelo bot.

## Intervalos e recuperação

Os valores ficam em `programa/config.py`:

| Configuração | Valor atual | Função |
|---|---|---|
| `TEMPO_ENTRE_MENSAGENS_MIN` / `MAX` | 600 s | Espera entre envios |
| `MENSAGENS_POR_LOTE` | 45 | Mensagens antes da pausa de lote |
| `PAUSA_ENTRE_LOTES_SEGUNDOS` | 8 h | Duração da pausa de lote |
| `HORA_INICIO_PAUSA_NOTURNA` / `FIM` | 0 e 6 | Pausa noturna; pode cruzar a meia-noite, como 20 e 8 |
| `LIMITE_ERROS_CONSECUTIVOS` | 10 | Erros seguidos antes de reiniciar o Chrome |
| `LIMITE_REINICIOS_SEM_SUCESSO` | 3 | Reinícios sem nenhum envio antes de parar a campanha |

Comportamento em caso de erro:

- **Número que não existe:** registrado e não tentado de novo (veja "Números que não existem").
- **Sessão perdida** (navegador fechou ou voltou para o QR Code): o Chrome reinicia e o contato é refeito.
- **Outros erros:** o contato vai para a varredura final; depois de muitos erros seguidos, o Chrome reinicia.
- **Problema persistente:** a campanha para e mantém o progresso. Corrija a causa e escolha continuar.

Se o bot não conseguir confirmar visualmente um envio depois que o texto saiu da caixa, o contato conta como enviado e entra em "Sem confirmação visual" no resumo. Isso evita mandar a mesma mensagem duas vezes.

Quando o WhatsApp Web mudar a interface, ajuste `programa/core/seletores.py`. Falhas geram capturas de tela em `runtime/screenshots/` (são mantidas as 30 mais recentes).

## Progresso e logs

Os arquivos gerados ficam em `runtime/`, ao lado de `dados/`:

- `estado.json`: contatos enviados, com falha e inválidos. Se o arquivo for danificado, o programa usa `estado.json.bak`; sem backup válido, ele para sem apagar nada.
- `estado_arquivado_*.json`: progresso de campanhas encerradas ou substituídas.
- `estado_formato_antigo_*.json`: cópia feita ao converter o progresso da versão anterior.
- `logs/`: um arquivo `envio_*.txt` por execução.
- `screenshots/`: capturas de diagnóstico.

Ao continuar uma campanha, a opção "Percorrer desde o primeiro contato" pula quem já recebeu. Para reenviar a todos, responda `SIM` em "nova campanha": o progresso anterior é arquivado somente depois da confirmação.

## Testes

Dentro de `programa/`:

```powershell
python -m unittest discover -s tests -t .
```

Os testes usam pastas temporárias e não abrem o navegador.

## Criar o executável

Dentro da pasta `programa`:

```powershell
python -m pip install pyinstaller
pyinstaller main.spec
```

O executável será criado em `programa/dist/WhatsAppBot.exe`. Mantenha a pasta `dados` ao lado da pasta do executável ou dentro dela. O Chrome precisa estar instalado no computador.

## Publicação no GitHub

O `.gitignore` exclui toda a pasta `dados/`, `runtime/` e os executáveis. A exceção é `dados/mensagem.txt`, que já estava versionado e continua sendo rastreado até ser removido com `git rm --cached dados/mensagem.txt`. Revise sempre o stage antes do commit:

```powershell
git status
git diff --cached --stat
```
