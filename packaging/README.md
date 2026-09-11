# Packaging de codex-cockpit

Adaptado diretamente dos scripts e workflows de
[Wallace Martins / cc-cockpit](https://github.com/wallacemartinss/cc-cockpit).
Todos os pacotes usam `codex-cockpit` e o módulo `codex_cockpit`, sem substituir
arquivos do projeto original. A versão vem de `codex_cockpit/__init__.py`.

## Wheel e sdist

```bash
python3 -m venv .venv
.venv/bin/pip install build
.venv/bin/python -m build
./packaging/smoke-wheel.sh
```

O dashboard acompanha o módulo em `codex_cockpit/web/index.html`. O pacote Python
não exige GTK para usar CLI/dashboard. A bandeja precisa de PyGObject, Cairo e
AppIndicator instalados pelo gerenciador da distribuição; em um venv para usar a
bandeja, crie-o com `--system-site-packages`.

## Debian / Ubuntu

```bash
./packaging/build-deb.sh
sudo apt install ./dist/codex-cockpit_0.1.0_all.deb
```

O `.deb` declara as dependências da bandeja e instala uma entrada no menu de
aplicativos. Não habilita autostart globalmente. Para ativá-lo só para seu usuário:

```bash
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
cp /usr/share/applications/codex-cockpit.desktop "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/"
```

## Arch Linux

```bash
cd packaging
makepkg -si
```

A receita `codex-cockpit-git` acompanha `main`, porque não depende da existência
de um tag de release. `SKIP` é usado somente para essa fonte Git; `pkgver()`
registra versão, número de commits e revisão. Conflita apenas com outra instalação
Arch de `codex-cockpit`, nunca com `cc-cockpit`. A receita não foi publicada no AUR.
Atualize `.SRCINFO` com `makepkg --printsrcinfo > .SRCINFO` antes de publicá-la.

## CI e release

- CI: testes em Python 3.10 e 3.13, build wheel/sdist, instalação isolada sem GTK,
  verificação do HTML e de pt_BR, build e inspeção do `.deb`.
- Release: um tag `vX.Y.Z` deve corresponder à versão Python. Após os testes,
  publica wheel, sdist, `.deb` e `SHA256SUMS` em GitHub Releases.
- PyPI: opt-in pela variável de repositório `ENABLE_PYPI=true`, somente após
  configurar Trusted Publishing para `cpereiraweb/codex-cockpit`, workflow
  `release.yml`, environment `pypi`. Sem a variável, o job é ignorado.

Nenhum tag ou publicação no PyPI é criado pelos scripts de build local.
