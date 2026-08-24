# WhatsAppBot

Bot para envio automatizado de mensagens, imagens ou vídeos pelo WhatsApp Web usando Selenium e Google Chrome.

> Use este projeto somente com contatos que autorizaram o recebimento das mensagens e respeite os termos do WhatsApp e as leis aplicáveis.

## Funcionalidades

- Envio de imagem ou vídeo junto com uma mensagem personalizada.
- Variáveis `{var1}` a `{var5}` baseadas na posição das colunas da planilha.
- Escolha, no terminal, da coluna que contém o telefone do WhatsApp.
- A coluna do telefone não é usada como variável da mensagem.
- Registro de progresso para continuar uma campanha interrompida.
- Intervalo aleatório de 10 a 20 segundos entre mensagens.
- Pausa de X minutos a cada Y mensagens enviadas com sucesso (baseado no tempo que você definir em: 
  MENSAGENS_POR_LOTE = X
  PAUSA_ENTRE_LOTES_SEGUNDOS = Y * 60.
- Reinício do Chrome após 10 erros consecutivos.

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
│   └── core/
└── runtime/                 # criado durante a execução
```

## Requisitos

- Windows.
- Python 3.10 ou superior.
- Google Chrome instalado.
- Uma sessão do WhatsApp Web no perfil de automação.

As bibliotecas Python são verificadas automaticamente na primeira execução. Também podem ser instaladas manualmente:

```powershell
python -m pip install pandas openpyxl selenium pyautogui pyperclip
```

## Configuração da planilha

O arquivo deve ser salvo como `dados/contatos.xlsx`.

A primeira linha é tratada como título e ignorada. Os dados começam sempre na segunda linha. Os nomes dos títulos não importam: as colunas são identificadas somente pela posição escolhida no terminal.

Exemplo:

| Nome | Nome indicado | contato | titulo |
|---|---|---|---|
| Ana | Bruno | 5581999999999 | Curso de Python |

Ao escolher a coluna `3` como contato:

- a coluna `1` será `{var1}`;
- a coluna `2` será `{var2}`;
- a coluna `3` será usada somente para abrir o WhatsApp;
- a coluna `4` será `{var3}`.

O programa pergunta se os telefones já começam com o código do Brasil (`55`). Se você responder `N`, ele acrescentará `55` automaticamente quando necessário. Se responder `S`, os números serão usados com o prefixo já informado.

Símbolos são aceitos e removidos automaticamente. Por exemplo, `(85)99999-9999` será convertido para `85999999999`; respondendo `N` à pergunta do código do Brasil, o número usado no WhatsApp será `5585999999999`.

## Configuração da mensagem

Edite `dados/mensagem.txt` usando as variáveis na ordem das colunas, desconsiderando a coluna escolhida como telefone:

```text
Olá {var1}, tudo bem?
Você foi indicado por {var2}.
Temos uma oportunidade sobre {var3}.
```

Durante a execução, o programa pergunta:

1. Se será enviada uma imagem ou um vídeo.
2. Em qual coluna está o contato do WhatsApp.
3. Se os contatos já começam com `55` ou se o código deve ser acrescentado.
4. Quantas variáveis de texto serão usadas, de 1 a 5.

O telefone é sempre usado somente para abrir a conversa no WhatsApp. A coluna escolhida não entra na sequência das variáveis da mensagem.

Uma variável que não existir entre as colunas disponíveis permanece escrita no texto como `{varN}`. Revise a mensagem antes de iniciar a campanha.

## Executar pelo Python

No PowerShell:

```powershell
cd P:\DEV\Python\WhatsAppBot\programa
python main.py
```

Na primeira execução, o Chrome abrirá o WhatsApp Web. Escaneie o QR Code e aguarde o login ser concluído. O perfil usado pela automação fica em `runtime/chrome_automacao`, separado do seu perfil normal do Chrome.

## Criar o executável

Dentro da pasta `programa`, execute:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --name WhatsappBot main.py
```

O executável será criado em `programa/dist/WhatsappBot.exe`. Mantenha a pasta `dados` ao lado do executável e coloque nela a planilha, a mensagem e o arquivo de mídia.

## Progresso e logs

Os arquivos gerados ficam em `programa/runtime/`:

- `estado.json`: permite continuar a campanha sem reenviar contatos já concluídos.
- `logs/`: registra os envios, erros e pausas.
- `chrome_automacao/`: perfil separado usado pelo Chrome automatizado.

Para começar uma campanha completamente nova, remova o `estado.json` somente quando tiver certeza de que não precisa continuar a campanha anterior.

## Publicação no GitHub

Dados pessoais, mídias, logs, perfil do Chrome, executáveis e arquivos temporários são ignorados pelo `.gitignore`. Antes de publicar alterações, confira o que será enviado:

```powershell
git status
git add .
git commit -m "descreve a alteração"
git push
```
