# Monitor de eventos

Verifica a [página do Super Chill Bar](https://www.pensanoevento.com.br/locais/1253/super-chill-bar) a cada 15 minutos e avisa no WhatsApp, no Telegram ou nos dois quando aparece um evento novo. Roda no GitHub Actions, sem depender do seu PC.

## 1. Configurar os avisos

Configure pelo menos um canal. Usar os dois dá uma redundância útil, porque o WhatsApp aqui depende de um serviço de terceiros.

### Telegram

1. Fale com o `@BotFather`, envie `/newbot` e guarde o token.
2. Mande qualquer mensagem para o seu bot.
3. Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` e copie o valor de `message.chat.id`.

### WhatsApp (CallMeBot)

1. Pegue o número atual de ativação em [callmebot.com](https://www.callmebot.com/blog/free-api-whatsapp-messages/). Ele muda de tempos em tempos. As vagas são limitadas: se o número aparecer mascarado, o bot está lotado e é preciso voltar alguns dias depois. Enquanto isso, use o Telegram.
2. Salve esse número nos contatos e envie pelo WhatsApp: `I allow callmebot to send me messages`
3. Guarde a API key que chegar na resposta. Se não vier em 2 minutos, tente de novo depois de 24 horas.

Ele só envia mensagens para o seu próprio número e é voltado a uso pessoal.

## 2. Testar no seu PC

```bash
pip install -r requirements.txt
PAGE_URL="https://www.pensanoevento.com.br/locais/1253/super-chill-bar" PAGE_MARKER="Super Chill Bar" python monitor.py
```

Fora de temporada, o esperado é `Primeira execução: 0 evento(s) salvos, sem notificar.` Apague o `seen.json` depois do teste.

## 3. Publicar no GitHub

Crie um repositório **público** e envie estes arquivos. Depois, em Settings > Secrets and variables > Actions, na aba Secrets, cadastre os valores dos canais que você configurou:

| Nome | Valor |
| --- | --- |
| `TELEGRAM_TOKEN` | token do BotFather |
| `TELEGRAM_CHAT_ID` | seu chat id |
| `WHATSAPP_PHONE` | seu número com DDI, ex.: `+5548999999999` |
| `WHATSAPP_APIKEY` | API key do CallMeBot |

Em Actions, abra "Monitor de eventos" e clique em "Run workflow". Confira no log se a execução passou. Essa primeira execução salva o estado atual: como a casa está sem eventos, o próximo evento publicado já gera aviso.

## Bom saber

- A execução manual falhando com 403 ou "Possível bloqueio" significa que o site recusou o GitHub. Nesse caso, o bot precisa rodar em outro lugar.
- O agendamento do GitHub pode atrasar, então não serve para disputar ingresso no segundo em que abre.
- Em repositório público os minutos do Actions são gratuitos. Em privado, rodar a cada 15 minutos estoura a cota grátis; use `0 * * * *` para rodar de hora em hora.
- O GitHub pausa agendamentos em repositórios públicos sem atividade por 60 dias. O bot faz um commit mensal (`heartbeat.txt`) para tentar evitar isso, mas a documentação não define o que conta como atividade. Por isso, confira a aba Actions antes do verão e reative o workflow se ele estiver pausado.
- Para monitorar outra casa do Pensanoevento, troque `PAGE_URL` e `PAGE_MARKER` em `.github/workflows/monitor.yml`.
