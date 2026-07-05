# 💰 Controle de Investimentos

App em Python (Streamlit) para controlar sua carteira de ações, FIIs e renda fixa —
gratuito e acessível de qualquer dispositivo (celular, tablet, computador).

## Telas

1. **Carteira Principal** — cadastro de ativos e renda fixa, com cálculo automático de
   valor investido, % da posição, valorização, margem até o preço teto, dividendo anual
   e yield on cost mensal.
2. **Exposição da Carteira** — gráficos de pizza e barras (Ações x FIIs x Renda Fixa,
   exposição por ativo, diversificação por setor).
3. **Crescimento e Aportes** — evolução patrimonial e proventos recebidos (dividendos,
   renda fixa, CDI, FGTS).

## Login e contas

Cada pessoa cria sua própria conta (e-mail + senha, mínimo 6 caracteres) na aba
"Criar conta" da tela inicial. As senhas ficam guardadas com hash (PBKDF2-SHA256 +
salt único por usuário) — nunca em texto puro. Os dados de cada conta ficam
isolados: ninguém enxerga a carteira de outra pessoa.

Não existe mais senha compartilhada — só é preciso avisar seus amigos a URL do app
e cada um cria a própria conta.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.
Os dados ficam salvos no arquivo `carteira.db` (SQLite), na mesma pasta do projeto.

## Como colocar online de graça (Streamlit Community Cloud)

1. Crie uma conta gratuita em https://share.streamlit.io (pode entrar com GitHub).
2. Suba os arquivos deste projeto para um repositório no GitHub.
3. No Streamlit Community Cloud, clique em "New app", escolha o repositório e o
   arquivo principal `app.py`.
4. Clique em "Deploy". Em poucos minutos você recebe uma URL pública
   (algo como `https://seu-app.streamlit.app`) que funciona em qualquer navegador,
   inclusive no celular. É essa URL que você compartilha com os amigos — cada um
   cria a própria conta na aba "Criar conta".


**Importante sobre o banco de dados na nuvem:** o Streamlit Community Cloud tem um
sistema de arquivos temporário — se o app "dormir" por inatividade e reiniciar, o
arquivo `carteira.db` pode ser resetado. Para uso pessoal com poucos acessos isso
raramente é um problema, mas se quiser persistência 100% garantida no free tier,
duas opções simples:

- Usar o **Turso** (banco SQLite na nuvem, plano gratuito generoso) — troca-se
  apenas a conexão em `db.py`.
- Ativar a opção de "Persistent storage" via um serviço como o **Supabase**
  (Postgres gratuito) — também é só trocar a camada de conexão em `db.py`,
  o resto do app não muda.

Se quiser, posso adaptar o `db.py` para um desses bancos na nuvem.

## Cotações de ações/FIIs

O app usa a API gratuita da [brapi.dev](https://brapi.dev) para buscar o preço atual
de ações e FIIs da B3. Não é obrigatório ter conta, mas o limite de requisições sem
token é baixo. Se quiser mais estabilidade:

1. Crie uma conta grátis em https://brapi.dev
2. Gere um token no dashboard
3. Crie o arquivo `.streamlit/secrets.toml` com:
   ```toml
   BRAPI_TOKEN = "seu_token_aqui"
   ```
   (no Streamlit Community Cloud, cole isso em "Settings > Secrets" do app)

## Estrutura de arquivos

```
carteira_app/
├── app.py                              # página inicial
├── db.py                               # camada de banco de dados (SQLite)
├── api.py                              # busca de cotações (brapi.dev)
├── requirements.txt
└── pages/
    ├── 1_📊_Carteira_Principal.py
    ├── 2_🥧_Exposicao_da_Carteira.py
    └── 3_📈_Crescimento_e_Aportes.py
```
