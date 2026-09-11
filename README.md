# codex-cockpit

[Repositório oficial: cpereiraweb/codex-cockpit](https://github.com/cpereiraweb/codex-cockpit)

Monitor local de uso do **OpenAI Codex** para Linux: indicador na bandeja GNOME,
dashboard e relatório no terminal. Detecção automática de idioma, com mensagens
em inglês (`en`) e português do Brasil (`pt_BR`); espanhol também permanece disponível.
O ícone azul sem moldura mantém o anel de consumo e o menu identifica `codex-cockpit`.

Lê os rollouts em `$CODEX_HOME/sessions/**/*.jsonl` e
`$CODEX_HOME/archived_sessions/**/*.jsonl` (`CODEX_HOME` padrão: `~/.codex`).
Não lê credenciais, não chama APIs e não altera a configuração do Codex.
O servidor do dashboard escuta somente em `127.0.0.1`.

## Origem, créditos e coautoria

Este projeto se inspirou diretamente no excelente trabalho de **Wallace Martins**
([wallacemartinss](https://github.com/wallacemartinss)), autor do
[cc-cockpit](https://github.com/wallacemartinss/cc-cockpit), e foi desenvolvido a
partir de seu código. A arquitetura original de monitoramento local, dashboard,
bandeja e relatórios forneceu a base desta adaptação para o Codex.

- **Wallace Martins da Silva** — autor do projeto original `cc-cockpit`.
- **Claudio Pereira ([cpereiraweb](https://github.com/cpereiraweb))** — idealização,
  direção e manutenção da adaptação `codex-cockpit`.
- **Codex (OpenAI) com modelo GPT-6 Astra** — coautor de IA desta adaptação, responsável pela implementação colaborativa da integração com o Codex, migração de namespaces, testes e documentação.

O histórico Git e a licença MIT original foram preservados, incluindo o crédito
de copyright de Wallace Martins da Silva. A coautoria de IA reconhece a contribuição
na adaptação e não implica afiliação ou endosso da OpenAI.

## Instalação e uso

Requer Python 3.10+ e Linux. Para a bandeja, instale também as dependências GTK:

```bash
git clone https://github.com/cpereiraweb/codex-cockpit.git
cd codex-cockpit
sudo apt install python3-gi python3-cairo gir1.2-ayatanaappindicator3-0.1
./install.sh
codex-cockpit
```

O instalador cria `~/.local/bin/codex-cockpit` e
`~/.config/autostart/codex-cockpit.desktop`. Mantenha este repositório no mesmo
local: o executável aponta para ele. O dashboard e os relatórios não dependem de GTK.

```bash
codex-cockpit report
codex-cockpit serve --open          # http://127.0.0.1:8766
codex-cockpit json
codex-cockpit collect
codex-cockpit config
codex-cockpit --lang pt report
```

Sem instalar:

```bash
python3 -m codex_cockpit report
python3 -m codex_cockpit serve --open
```

## Idioma

O padrão `language: "auto"` considera `LANGUAGE` (lista de preferências),
`LC_ALL`, `LC_MESSAGES` e `LANG`, ignorando locales genéricos como `C.UTF-8` e
idiomas sem tradução. Assim, `LANG=pt_BR.UTF-8` funciona mesmo quando um lançador
injeta `LC_ALL=C.UTF-8`. Sem preferência compatível, usa inglês.

```bash
codex-cockpit --lang pt_BR tray
codex-cockpit --lang en serve --open
```

A opção também pode ser salva como `"language": "pt_BR"` ou `"language": "en"`
no arquivo de configuração. `pt` e `pt-BR` são aliases aceitos. Reinicie a
bandeja após mudar a configuração. Dashboard, bandeja e relatórios compartilham
as mesmas traduções.

## Pacotes e automação

O projeto inclui wheel/sdist, builder `.deb`, receita Arch `codex-cockpit-git`
e workflows GitHub Actions adaptados do cc-cockpit. A CI testa Python 3.10/3.13
e verifica o dashboard dentro do wheel instalado. Tags `vX.Y.Z` publicam os
artefatos no GitHub Releases; PyPI exige configuração explícita de Trusted
Publishing. Veja [packaging/README.md](packaging/README.md) para build e instalação.

## O que mostra

- Tokens de entrada, saída, escrita e leitura de cache, por projeto e modelo.
- Histórico por hora, dia, mês e blocos locais configuráveis.
- Esforço de raciocínio e consumo de subagentes identificados nos metadados.
- Percentuais e resets de limites de 5 horas e 7 dias, quando presentes nos
  eventos `token_count`. As janelas são identificadas pela duração, não pela
  posição `primary`/`secondary`.
- Processos nativos do Codex em execução, PID, memória, diretório e tempo aberto.
  A associação a uma sessão exige um rollout aberto pelo processo; sem essa
  evidência, o consumo por processo não é atribuído. A atividade aparece como
  indisponível, pois a existência do processo não comprova estado busy/idle.
- Contexto estimado a partir do último uso informado, disponível no JSON e na bandeja.

A coleta é incremental, mantém metadados entre execuções, ignora linhas ainda
incompletas e usa deltas dos contadores cumulativos. Tokens de raciocínio já
estão incluídos na saída e não são somados novamente. O cache é separado da
entrada para evitar dupla contagem. Arquivar ou reler um rollout não duplica os
eventos já coletados. Um lock serializa coletas simultâneas.

## Limites e estimativas

A prioridade é: observação oficial nos rollouts → sincronização manual →
estimativa local. Observações oficiais preservam seu horário original e expiram
no reset; a coleta de um arquivo antigo não o torna uma observação recente.
Limites de outras durações ou específicos de outros produtos não são atribuídos
às janelas de 5h/7d. Não há consulta em tempo real à conta.

Sem dados oficiais, os percentuais usam tetos configurados, calibração ou seu
próprio pico histórico: **não são o limite real da assinatura**. Para sincronizar
manualmente os percentuais **usados** (se o Codex mostrar restante, subtraia de 100):

```bash
codex-cockpit sync --block 23% --block-reset 1h55 --week 3% --week-reset 2d
codex-cockpit sync
codex-cockpit sync --reset
```

Não existe instalação de um hook de statusline nesta versão. O mecanismo de
comando externo usado pelo projeto original não corresponde ao
[`tui.status_line` do Codex](https://learn.chatgpt.com/docs/config-file/config-reference),
que configura uma lista de itens do rodapé.

Valores em USD são **estimativas equivalentes à API**, não a fatura nem a quota
contratual do plano. A tabela inclui preços padrão verificados em 10/09/2026 para
[GPT-5.3-Codex](https://developers.openai.com/api/docs/models/gpt-5.3-codex),
[GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4),
[GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5),
[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) e
[GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol).
Não inclui taxas de ferramentas, descontos ou multiplicadores de service tier.
Os ajustes de contexto longo são aplicados aos modelos conhecidos quando o delta
de uso representa uma requisição. Lacunas nos registros podem agrupar requisições;
por isso contagens e valores continuam sendo aproximações locais.

Modelos sem preço conhecido continuam contando tokens e aparecem em
`unpriced_models`; CLI e dashboard sinalizam que os totais monetários são parciais.
Adicione seus preços para que o histórico retido seja recalculado na próxima coleta.

## Configuração e isolamento

`~/.config/codex-cockpit/config.json` (respeita `XDG_CONFIG_HOME`):

```json
{
  "language": "auto",
  "block_hours": 5,
  "limits": {"block_usd": null, "week_usd": null},
  "tray_metric": "block",
  "menu_bar_style": "blocks",
  "tray_show_cost": true,
  "refresh_seconds": 20,
  "plan_monthly_usd": null,
  "plan_name": "",
  "local_currency": null,
  "dashboard_port": 8766,
  "warn_pct": 70,
  "critical_pct": 90,
  "model_prices": {
    "gpt-5.3-codex": {"input": 1.75, "output": 14, "cached_input": 0.175}
  }
}
```

Os preços são em USD por milhão de tokens. `local_currency` pode conter
`{"code":"BRL","symbol":"R$","rate":5.4}`; a cotação é manual.

| Recurso | Identificador |
|---|---|
| Executável / AppIndicator | `codex-cockpit` |
| Módulo Python | `codex_cockpit` |
| Configuração | `$XDG_CONFIG_HOME/codex-cockpit` |
| Histórico, estado, lock e ícones | `$XDG_DATA_HOME/codex-cockpit` |
| Autostart | `codex-cockpit.desktop` |
| Porta padrão | `8766` |

`XDG_DATA_HOME` usa `~/.local/share` por padrão. Nenhum arquivo do `cc-cockpit`
é importado, modificado ou removido; os dois podem coexistir, inclusive seus dashboards.
Os rollouts são um formato local sujeito a mudanças entre versões do Codex.
Sessões remotas sem registros locais não entram nos totais de tokens.

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q codex_cockpit
bash -n install.sh
```

MIT — veja [LICENSE](LICENSE). Projeto independente, sem afiliação à OpenAI.
