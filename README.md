# Controle de Investimentos

App em Python (Streamlit) para controlar carteira de ações, FIIs, renda fixa e
contabilidade mensal — gratuito e acessível de qualquer dispositivo (celular,
tablet, computador). Suporta múltiplos usuários, cada um com login e dados
próprios.

## Telas

1. **Início** — painel geral: patrimônio total, evolução patrimonial, progresso
   da meta, dividendos recebidos (mês/ano/histórico) e pop-up automático de
   alertas configurados.
2. **Carteira Principal** — cadastro de ativos (ticker, setor, quantidade,
   preço médio, preço teto, preço chão, dividendo) e renda fixa, com cálculo
   automático de valor investido, % da posição, valorização, margem até o
   preço teto e yield on cost (anual e mensal). Exclusão individual com
   confirmação e exportação para Excel.
3. **Exposição da Carteira** — gráficos de pizza e barras (Ações x FIIs x
   Renda Fixa, exposição por ativo, diversificação por setor).
4. **Crescimento e Aportes** — evolução patrimonial, proventos recebidos
   (dividendos, renda fixa, CDI, FGTS), evolução de dividendos e YoC realizado
   mês a mês.
5. **Metas** — metas de patrimônio por ano, reserva de emergência, metas de
   longo prazo (desejada/master) com barra de progresso, resumo de
   rendimentos por ano.
6. **Contabilidade Mensal** — categorias de receita/despesa customizáveis,
   lançamentos mês a mês por ano, resumo com sobras ($ e %) e médias.
7. **Notícias e Fatos Relevantes** — últimas notícias de cada ativo da
   carteira, via Yahoo Finance, com imagem/thumbnail quando disponível.
8. **Alertas** — configuração de avisos (preço teto, preço chão, variação
   diária, YoC mínimo, concentração máxima, meta de patrimônio atingida), com
   edição em lote, ativar/desativar, exclusão e histórico de disparos. Dispara
   um pop-up ao fazer login quando alguma condição é atingida.
9. **Admin - Importar SQL** *(oculta para a maioria dos usuários)* — execução
   de scripts SQL direto no banco em produção, restrita por e-mail em
   `admin_config.py`.

## Login e contas

Cada pessoa cria sua própria conta na aba "Criar conta" da tela inicial,
informando nome completo, e-mail, telefone (opcional), perfil de investidor
(Conservador/Moderado/Arrojado), objetivo principal e uma senha (mínimo 6
caracteres, guardada com hash PBKDF2-SHA256 + salt único por usuário — nunca
em texto puro). O login acontece automaticamente após criar a conta. Os dados
de cada conta ficam isolados: ninguém enxerga a carteira de outra pessoa.

Não existe senha compartilhada — só é preciso avisar a URL do app aos amigos;
cada um cria a própria conta.

## Banco de dados

O app usa o **Turso** (SQLite hospedado na nuvem) quando as variáveis
`TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` estão configuradas nos Secrets. Isso
garante que os dados **não são perdidos** quando o Streamlit Community Cloud
reinicia o app por inatividade.

Se essas variáveis não estiverem configuradas (ex: rodando local sem
configurar nada), o app cai automaticamente para um arquivo SQLite local
(`carteira.db`, na mesma pasta do projeto) — útil para testar rapidamente sem
depender da nuvem.

## Cotações de ações/FIIs e notícias

O app usa o **Yahoo Finance** (biblioteca `yfinance`) para buscar cotações e
notícias — gratuito, sem necessidade de token ou conta. Tickers da B3 recebem
o sufixo `.SA` internamente (ex: `PETR4` → `PETR4.SA`). As cotações de todos
os ativos são buscadas em uma única requisição em lote, para evitar limites de
requisição por rajada.

## Área administrativa

A lista de e-mails com acesso à página "Admin - Importar SQL" fica centralizada
em `admin_config.py`:

```python
EMAILS_ADMIN = {"seu-email@gmail.com"}
```

Essa mesma lista controla tanto o bloqueio de acesso à página quanto a
visibilidade do link no menu lateral (montado manualmente em `nav.py`, já que
a navegação automática do Streamlit sempre mostra todas as páginas para todo
mundo).

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run "Início.py"
```

O navegador abrirá automaticamente em `http://localhost:8501`.

## Como colocar online de graça (Streamlit Community Cloud)

1. Crie uma conta gratuita em https://share.streamlit.io (pode entrar com GitHub).
2. Suba os arquivos deste projeto para um repositório no GitHub.
3. No Streamlit Community Cloud, clique em "New app", escolha o repositório e
   o arquivo principal `Início.py`.
4. Em Settings → Secrets, cole:
   ```toml
   TURSO_DATABASE_URL = "sua_url_aqui"
   TURSO_AUTH_TOKEN = "seu_token_aqui"
   ```
5. Clique em "Deploy". Em poucos minutos você recebe uma URL pública que
   funciona em qualquer navegador, inclusive no celular. É essa URL que você
   compartilha com os amigos — cada um cria a própria conta na aba "Criar
   conta".

**Atualizações futuras:** basta `git push` na branch `main` — o Streamlit Cloud
detecta o commit e atualiza o app publicado automaticamente em cerca de 1
minuto, sem precisar reconfigurar nada.

## Estrutura de arquivos

```
carteira_app/
├── Início.py                                  # painel geral / página inicial (entry point)
├── db.py                                      # camada de banco de dados (Turso / SQLite local)
├── api.py                                     # cotações e notícias (Yahoo Finance)
├── auth.py                                    # login, criação de conta, hash de senha
├── style.py                                   # tema visual e formatação de tabelas
├── export.py                                  # exportação de dados para Excel
├── alerts.py                                  # lógica de avaliação dos alertas
├── nav.py                                     # menu lateral manual (permite ocultar páginas)
├── admin_config.py                            # lista de e-mails com acesso administrativo
├── requirements.txt
├── .streamlit/
│   ├── config.toml                            # tema + navegação automática desativada
│   └── secrets.toml                           # TURSO_DATABASE_URL, TURSO_AUTH_TOKEN (não versionado)
└── pages/
    ├── 1_Carteira_Principal.py
    ├── 2_Exposição_da_Carteira.py
    ├── 3_Crescimento_e_Aportes.py
    ├── 4_Metas.py
    ├── 5_Contabilidade_Mensal.py
    ├── 6_Notícias_e_Fatos_Relevantes.py
    ├── 7_Admin_Importar_SQL.py
    └── 8_Alertas.py
```
