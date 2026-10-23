# WhatsAppBot

Bot para envio automatizado de mensagens, imagens ou vídeos pelo WhatsApp Web usando Selenium e Google Chrome.

> Use este projeto somente com contatos que autorizaram o recebimento das mensagens e respeite os termos do WhatsApp e as leis aplicáveis.

## Funcionalidades

- Envio de imagem, vídeo ou somente texto, com mensagem personalizada.
- Variáveis `{var1}` a `{var5}`, definidas pela posição das colunas da planilha.
- Escolha, no terminal, da coluna que contém o telefone e da quantidade de variáveis.
- Normalização dos telefones e opção para acrescentar o código do Brasil (`55`).
- Digitação do texto pelo Selenium, preservando as quebras de linha.
- Retomada de campanhas, seleção do contato inicial e reprocessamento de contatos com falha.
- Pausa noturna entre 00:00 e 06:00, conforme o horário local do computador.
- Reinício da sessão do Chrome após 200 erros consecutivos.

## Estrutura

```text
WhatsAppBot/
├── dados/
│   ├── contatos.xlsx       # não versionado: dados pessoais
│   ├── mensagem.txt
│   ├── imagem.png           # opcional
│   └── video.mp4            # opcional
├── programa/
│   ├── main.py
│   ├── config.py
│   ├── core/
│   └── runtime/             # progresso, logs e outros dados de execução
└── README.md
```

## Requisitos

- Windows.
- Python 3.10 ou superior.
- Google Chrome instalado.
- Uma sessão do WhatsApp Web no perfil de automação.

As bibliotecas Python são verificadas na inicialização. Se necessário, o programa pode instalá-las automaticamente. A instalação manual é:

```powershell
python -m pip install pandas openpyxl selenium pyautogui
```

## Configuração da planilha

O arquivo deve ser salvo como `dados/contatos.xlsx`.

A primeira linha é tratada como título e ignorada. Os dados começam sempre na segunda linha. Os nomes dos títulos não importam: as colunas são identificadas somente pela posição escolhida no terminal.

Exemplo:

| Nome | Nome indicado | contato | titulo |
|---|---|---|---|
| Ana | Bruno | 5581999999999 | Curso de Python |

Os títulos da primeira linha são ignorados. Ao escolher a coluna `3` como telefone:

- a coluna `1` será `{var1}`;
- a coluna `2` será `{var2}`;
- a coluna `3` será usada somente para abrir o WhatsApp;
- a coluna `4` será `{var3}`.

O programa pede a coluna do telefone e pergunta se os números já começam com o código do Brasil (`55`). Respondendo `N`, ele acrescenta `55` quando necessário; respondendo `S`, mantém o código que já está no número. Pontuação e outros caracteres não numéricos são removidos.

Exemplo: `(85) 99999-9999` é normalizado para `85999999999`; respondendo `N`, o número usado no WhatsApp será `5585999999999`.

## Configuração da mensagem

Edite `dados/mensagem.txt` usando `{var1}` a `{var5}` na ordem das colunas, desconsiderando a coluna escolhida como telefone:

```text
Olá {var1}, tudo bem?
Você foi indicado por {var2}.
Temos uma oportunidade sobre {var3}.
```

Variáveis sem uma coluna correspondente permanecem no texto como `{varN}`. O programa não substitui automaticamente marcadores como `{Nome}`; use `{var1}`, `{var2}` etc.

Durante a execução, o programa pergunta:

1. Se será enviada uma imagem, um vídeo ou somente texto.
2. Em qual coluna está o telefone do WhatsApp.
3. Se os contatos já começam com `55` ou se o código deve ser acrescentado.
4. Quantas variáveis de texto serão usadas, de 1 a 5.
5. Se a campanha é nova ou se deve continuar o progresso salvo.

Em uma nova campanha, é possível começar do primeiro contato ou escolher um contato da lista. Ao continuar uma campanha, também é possível retomar o próximo contato, escolher um contato ou começar novamente. Contatos já enviados são pulados quando o progresso é mantido.

O telefone é usado somente para abrir a conversa e não entra na sequência das variáveis da mensagem. Revise a mensagem e a ordem das colunas antes de iniciar a campanha.

## Intervalos e recuperação

Os valores atuais estão em `programa/config.py`:

- `TEMPO_ENTRE_MENSAGENS_MIN` e `TEMPO_ENTRE_MENSAGENS_MAX`: ambos estão em 60 segundos, então a espera após cada envio bem-sucedido é fixa em 1 minuto. Para configurar outro intervalo fixo, defina os dois valores em segundos com o mesmo número.
- `MENSAGENS_POR_LOTE`: pausa após 500 mensagens enviadas com sucesso, desde que ainda haja contatos a processar.
- `PAUSA_ENTRE_LOTES_SEGUNDOS`: atualmente configurada para 8 horas.
- `HORA_INICIO_PAUSA_NOTURNA` e `HORA_FIM_PAUSA_NOTURNA`: pausa entre meia-noite e 06:00 no horário local.

Após 200 erros consecutivos, o programa reinicia a sessão do Chrome e tenta novamente o bloco de contatos que falhou. O limite de tentativas de reprocessamento está definido em `programa/main.py`.

## Executar pelo Python

No PowerShell:

```powershell
cd P:\DEV\Python\WhatsAppBot\programa
python main.py
```

Na primeira execução, o Chrome abrirá o WhatsApp Web. Escaneie o QR Code e aguarde o login ser concluído. O perfil usado pela automação fica em `%LOCALAPPDATA%\WhatsAppBot\chrome_automacao`, separado do seu perfil normal do Chrome. Se houver um perfil antigo em `programa/runtime/chrome_automacao`, ele será copiado para essa pasta local na primeira execução; a cópia original será mantida.

## Criar o executável

Dentro da pasta `programa`, execute:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --name WhatsappBot main.py
```

O executável será criado em `programa/dist/WhatsappBot.exe`. Mantenha a pasta `dados` ao lado do executável e coloque nela a planilha, a mensagem e os arquivos de mídia. O Chrome precisa estar instalado no computador.

## Progresso e logs

Os arquivos gerados ficam em `programa/runtime/`, exceto o perfil local do Chrome:

- `estado.json`: guarda o índice, contadores, contatos enviados e falhas pendentes para continuar a campanha.
- `logs/`: cria um arquivo `envio_*.txt` com os eventos e o resumo da execução. O cabeçalho atual é `WHATSAPP BOT`.
- `screenshots/`: pode receber capturas de tela de diagnóstico quando o WhatsApp Web não carrega.
- `%LOCALAPPDATA%\WhatsAppBot\chrome_automacao`: perfil separado usado pelo Chrome automatizado.

Ao iniciar uma campanha nova e responder `SIM`, o progresso anterior é limpo pelo programa. Para continuar, responda `NÃO` e escolha uma das opções disponíveis. Não apague `estado.json` se precisar recuperar uma campanha interrompida.

## Publicação no GitHub

O `.gitignore` exclui planilhas de contatos, mídias, arquivos temporários e artefatos gerados. O texto da campanha em `dados/*.txt` não é ignorado; não use `git add .` neste projeto, pois isso pode publicar conteúdo da campanha.

Adicione somente os arquivos de código e documentação que deseja publicar e revise o stage antes do commit:

```powershell
git status
git add README.md programa/main.py programa/config.py programa/core programa/scripts
git diff --cached --stat
git diff --cached
git commit -m "descreve a alteração"
git push
```
