# ✈️ Quiz Propulsão EASA

> Aplicação de quiz interativo para estudo de propulsão aeronáutica, baseada em IA generativa e recuperação de documentos oficiais da EASA.

---

## 📋 Índice

1. [O que é este projeto?](#-o-que-é-este-projeto)
2. [Para quem é este projeto?](#-para-quem-é-este-projeto)
3. [Tecnologias utilizadas — e por quê?](#-tecnologias-utilizadas--e-por-quê)
4. [Arquitetura do sistema](#-arquitetura-do-sistema)
5. [Como os componentes se comunicam](#-como-os-componentes-se-comunicam)
6. [Conceitos-chave de IA explicados](#-conceitos-chave-de-ia-explicados)
7. [Estrutura de pastas](#-estrutura-de-pastas)
8. [Como instalar e executar](#-como-instalar-e-executar)
9. [Fluxo de uso da aplicação](#-fluxo-de-uso-da-aplicação)
10. [Perguntas frequentes](#-perguntas-frequentes)

---

## 🎯 O que é este projeto?

O **Quiz Propulsão EASA** é uma aplicação de estudo inteligente que gera automaticamente questões de múltipla escolha sobre motores a jato, turbofans, ciclos termodinâmicos e outros tópicos de propulsão aeronáutica.

**Diferencial:** as questões não são pré-fabricadas. Elas são geradas em tempo real por um agente de IA que *primeiro pesquisa* no material oficial da EASA antes de formular cada pergunta — garantindo que o conteúdo é tecnicamente correto e alinhado ao exame real.

### Funcionalidades principais

- 10 questões de múltipla escolha por sessão, geradas dinamicamente
- Pontuação em tempo real (X de 10 corretas)
- Feedback imediato com explicação técnica após cada resposta
- Botão **"Gerar Novas Questões"** para reiniciar com um novo conjunto
- Revisão completa de todas as questões ao final

---

## 👩‍🎓 Para quem é este projeto?

- Estudantes de Engenharia Aeronáutica e Mecânica em preparação para exames EASA Part-66
- Quem quer entender na prática como construir um sistema de **RAG Agêntico** com ferramentas modernas de IA
- Quem está aprendendo a integrar **LLMs** (Large Language Models) em aplicações reais

---

## 🛠️ Tecnologias utilizadas — e por quê?

Cada tecnologia foi escolhida por um motivo específico. Entender o **porquê** de cada escolha é tão importante quanto saber usá-la.

---

### 🤖 Google Agent Development Kit (ADK)

**O que é:**
O [Google ADK](https://google.github.io/adk-docs/) é um framework para construir **agentes de IA** — sistemas que tomam decisões, chamam ferramentas e executam tarefas complexas de forma autônoma.

**Por que foi escolhido:**
Em vez de simplesmente chamar uma API de LLM diretamente, o ADK fornece:
- Um **loop de execução gerenciado**: o agente decide quando usar ferramentas, quais resultados aceitar e quando parar
- **System prompts estruturados** (instruções permanentes do sistema)
- **Lifecycle management**: criação de sessões, gerenciamento de estado, rastreamento de eventos
- Facilidade para adicionar novas ferramentas no futuro (ex: busca na web, calculadora de desempenho)

**Analogia:** Pense no ADK como o *piloto automático* — ele segue regras, usa instrumentos (ferramentas) e toma decisões, mas dentro de parâmetros que você define.

```python
# Exemplo simplificado de como o ADK é usado aqui
agent = Agent(
    name="easa_quiz_agent",
    model="gemini-2.5-flash",
    instruction="Você é um especialista EASA. Gere questões baseadas APENAS no contexto fornecido...",
)
```

---

### 🧠 Google Gemini 2.5 Flash (LLM)

**O que é:**
Um **Large Language Model (LLM)** — um modelo de linguagem treinado em bilhões de textos, capaz de entender e gerar texto com alto nível de qualidade.

**Por que foi escolhido:**
- **Gemini 2.5 Flash** é o modelo mais recente e capaz disponível no Google AI Studio
- Excelente raciocínio técnico para conteúdo de engenharia
- Suporte nativo ao Google ADK (mesma família de ferramentas)
- Disponível gratuitamente via Google AI Studio API Key

**Modelo de embedding:** `gemini-embedding-001`
- Transforma textos em vetores numéricos de 3072 dimensões
- Usado para indexar o PDF e para as buscas semânticas

---

### 📦 ChromaDB (Banco de Dados Vetorial)

**O que é:**
Um banco de dados especializado em armazenar e buscar **vetores** (listas de números que representam o significado de textos).

**Por que foi escolhido em vez de um banco SQL ou NoSQL convencional:**

| Banco Convencional | ChromaDB (Vetorial) |
|---|---|
| Busca por palavras exatas (`LIKE '%turbina%'`) | Busca por **significado** semântico |
| "compressor axial" ≠ "compressor de fluxo axial" | "compressor axial" ≈ "compressor de fluxo axial" |
| Rápido para dados estruturados | Rápido para similaridade entre textos |

**Por que ChromaDB e não FAISS, Qdrant ou Weaviate?**
- **FAISS**: muito rápido, mas não tem persistência nativa — precisa salvar/carregar manualmente
- **Qdrant**: excelente para produção, mas requer servidor Docker separado
- **Weaviate**: feature-rich mas complexo de configurar
- **ChromaDB**: simples, persistente em disco, API Python nativa, sem servidor externo — ideal para protótipo e aprendizado

```python
# ChromaDB persiste os dados em disco automaticamente
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection("easa_propulsao")
collection.add(ids=["chunk_001"], documents=["O ciclo de Brayton..."])
```

---

### 🌊 Streamlit (Frontend)

**O que é:**
Um framework Python que converte código Python em aplicações web interativas — sem escrever HTML, CSS ou JavaScript.

**Por que foi escolhido:**
- **Zero fricção**: uma variável `st.session_state` substitui todo o gerenciamento de estado de um frontend complexo
- **Prototipagem rápida**: ir de ideia a UI funcional em horas
- **Comunidade de ciência de dados**: padrão da indústria para demos de ML/AI
- **Evolutivo**: pode ser substituído por FastAPI + React no futuro sem alterar o backend

**Limitação conhecida:** não é adequado para produção com alta concorrência. Para escalar, o próximo passo seria separar o backend (FastAPI) do frontend.

---

### 📄 PyPDF

**O que é:**
Biblioteca Python para extrair texto de arquivos PDF.

**Por que foi escolhido em vez de outras opções:**
- `pypdf` (sucessor de `PyPDF2`) é a biblioteca mais mantida atualmente
- `pdfplumber`: mais preciso com tabelas, mas mais pesado
- `pdfminer`: muito baixo nível, requer mais código boilerplate

Para este caso (texto corrido de questões), `pypdf` é mais que suficiente.

---

### 🔑 python-dotenv

**O que é:**
Carrega variáveis de ambiente de um arquivo `.env` para que chaves de API não fiquem hardcoded no código.

**Boa prática de segurança:**
```
# ❌ NUNCA faça isso:
api_key = "AIzaSyBcVUPEu1zGKcrLn-mcpwd6gmVQ3FCyFhI"

# ✅ Sempre faça assim:
api_key = os.getenv("GOOGLE_API_KEY")  # lido do arquivo .env
```

---

## 🏗️ Arquitetura do sistema

O sistema segue uma arquitetura em **3 camadas** com responsabilidades bem separadas:

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUÁRIO                                 │
│                    (navegador web)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / Streamlit
┌──────────────────────────▼──────────────────────────────────────┐
│                    FRONTEND — Streamlit                         │
│  frontend/app.py                                                │
│                                                                 │
│  • Máquina de estados: não_iniciado → gerando → quiz → resultado│
│  • st.session_state: perguntas, índice atual, respostas, pontos │
│  • UI: barra de progresso, rádio buttons, feedback por questão  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ chamada Python (in-process)
┌──────────────────────────▼──────────────────────────────────────┐
│                 BACKEND — Agente ADK                            │
│  backend/agent/quiz_agent.py                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. PRÉ-BUSCA (sem LLM)                                  │   │
│  │     Busca contexto dos 10 tópicos direto no ChromaDB    │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │  2. GERAÇÃO (1 chamada ao LLM)                           │   │
│  │     ADK Agent + Gemini 2.5 Flash                        │   │
│  │     Recebe contexto pré-buscado → gera 10 MCQs JSON     │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ queries vetoriais
┌──────────────────────────▼──────────────────────────────────────┐
│                 RAG — ChromaDB + Embeddings                     │
│  backend/rag/retriever.py                                       │
│                                                                 │
│  chroma_db/  (89 chunks do PDF indexados)                       │
│  Embedding model: gemini-embedding-001 (3072 dimensões)         │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline de Ingestão (roda uma única vez)

```
easa_propulsao.pdf
       │
       ▼
 [pypdf] Extração de texto
       │  25 páginas
       ▼
 [Chunking] Divisão em pedaços
       │  89 chunks (~1000 chars cada, com 200 de overlap)
       ▼
 [gemini-embedding-001] Cada chunk → vetor de 3072 números
       │  task_type = RETRIEVAL_DOCUMENT
       ▼
 [ChromaDB] Armazenamento persistente em disco
       │
      ✅ chroma_db/ pronta para consultas
```

### Pipeline de Geração de Quiz (roda a cada "Gerar Quiz")

```
Usuário clica "Gerar Quiz"
       │
       ▼
 [retriever.py] 10 buscas semânticas no ChromaDB
       │  Uma busca por tópico: "ciclo Brayton", "stall do compressor", etc.
       │  task_type = RETRIEVAL_QUERY (diferente da indexação!)
       │  Retorna os 5 chunks mais relevantes por tópico
       ▼
 [quiz_agent.py] Monta prompt com todo o contexto recuperado
       │
       ▼
 [ADK Runner] Executa o agente Gemini 2.5 Flash
       │  System prompt: guardrails, formato JSON, regras acadêmicas
       │  User prompt: 10 blocos de contexto EASA
       │  1 chamada ao LLM → 10 questões JSON
       ▼
 [parse_response] Valida e extrai o JSON
       │
       ▼
 [Streamlit] Exibe as questões uma a uma
```

---

## 🔗 Como os componentes se comunicam

```
frontend/app.py
    │
    ├── importa ──► backend/agent/quiz_agent.py
    │                    │
    │                    ├── importa ──► backend/rag/retriever.py
    │                    │                    │
    │                    │                    └── usa ──► chroma_db/ (ChromaDB)
    │                    │                               google.genai (embeddings)
    │                    │
    │                    └── usa ──► google.adk (ADK Runner)
    │                               google.genai (Gemini LLM)
    │
    └── importa ──► backend/rag/retriever.py (para verificar se KB está pronta)

scripts/ingest.py
    │
    └── importa ──► backend/ingestion/pdf_processor.py
                         │
                         ├── usa ──► pypdf (extração PDF)
                         ├── usa ──► google.genai (embeddings)
                         └── usa ──► ChromaDB (persistência)
```

**Todos os componentes se comunicam via chamadas Python diretas** (sem REST API, sem filas). Isso simplifica o desenvolvimento e é adequado para a fase inicial. Quando o projeto escalar, o `quiz_agent.py` pode virar um serviço FastAPI.

---

## 💡 Conceitos-chave de IA explicados

### O que é RAG (Retrieval-Augmented Generation)?

RAG é uma técnica que **combina busca de documentos com geração de texto**.

**Sem RAG:**
```
Usuário: "Qual é o bypass ratio de um turbofan de alto BPR?"
LLM: [responde do seu treinamento — pode alucinar ou dar info desatualizada]
```

**Com RAG:**
```
Usuário: "Qual é o bypass ratio de um turbofan de alto BPR?"
Sistema:  1. Busca no PDF da EASA os trechos mais relevantes
          2. Envia: "Com base NESTE texto: '...', responda a pergunta"
LLM:     [responde usando o texto real como âncora — muito mais confiável]
```

**Por que RAG é melhor do que simplesmente perguntar ao LLM?**
- LLMs têm data de corte de conhecimento e podem "alucinar" detalhes técnicos
- RAG garante que a resposta está ancorada em uma fonte verificável
- Você controla *qual* fonte é usada

### O que são Embeddings?

Um **embedding** é a representação numérica do *significado* de um texto.

```
"turbina"           → [0.12, -0.45, 0.89, ...]  (vetor de 3072 números)
"rotor de turbina"  → [0.11, -0.43, 0.91, ...]  (vetor parecido = significados parecidos)
"compressor"        → [0.78,  0.23, -0.12, ...]  (vetor diferente = significado diferente)
```

O modelo `gemini-embedding-001` transforma qualquer texto em um vetor de **3072 dimensões**. Textos com significados parecidos ficam "próximos" nesse espaço multidimensional.

**Por que dois task_types diferentes?**
```
Indexação (chunks do PDF): task_type = RETRIEVAL_DOCUMENT
   → "Estou guardando um documento para ser encontrado"

Busca (query do usuário): task_type = RETRIEVAL_QUERY  
   → "Estou procurando documentos relevantes para esta pergunta"
```
Usar task_types diferentes melhora a qualidade da busca (retrieval assimétrico).

### O que é um Agente de IA?

Um **agente** é um LLM que pode usar **ferramentas** e tomar decisões sequenciais.

```
Agente simples (sem ferramentas):
  Pergunta → LLM → Resposta

Agente com ferramentas (ADK):
  Pergunta → LLM → "Preciso buscar X" → Ferramenta → Resultado
                → LLM → "Agora preciso buscar Y" → Ferramenta → Resultado
                → LLM → Resposta Final
```

Neste projeto, o agente recebe o contexto já montado (sem necessidade de chamadas de ferramenta em loop), o que economiza chamadas à API e mantena a arquitetura dentro dos limites do plano gratuito.

### Por que o padrão "pré-busca + geração única"?

O limite do plano gratuito do Gemini 2.5 Flash é **5 requisições por minuto (RPM)**. Um loop agêntico com 10 chamadas de ferramenta gera ~20 chamadas ao LLM — o que estouraria esse limite.

A solução foi separar as responsabilidades:

```
Antes (loop agêntico — 20 chamadas):           Depois (pré-busca — 1 chamada):
  LLM → "vou buscar tópico 1"                    ChromaDB × 10  (sem LLM)
  ChromaDB → resultado                              │
  LLM → "vou buscar tópico 2"                      ▼
  ChromaDB → resultado                           LLM × 1  (com todo o contexto)
  ... (10× vezes)
  LLM → gera questões
```

---

## 📁 Estrutura de pastas

```
quiz_propulsao/
│
├── 📄 README.md               # Este arquivo
├── 📄 requirements.txt        # Dependências Python
├── 📄 .env                    # Chaves de API (NÃO commitar no git!)
│
├── 📂 data_source/
│   └── easa_propulsao.pdf     # Fonte de dados oficial EASA
│
├── 📂 chroma_db/              # Criado automaticamente após ingestão
│   └── ...                    # Índice vetorial persistido em disco
│
├── 📂 backend/
│   ├── config.py              # Configuração centralizada (caminhos, variáveis)
│   │
│   ├── 📂 ingestion/
│   │   └── pdf_processor.py   # PDF → chunks → embeddings → ChromaDB
│   │
│   ├── 📂 rag/
│   │   └── retriever.py       # Busca semântica no ChromaDB
│   │
│   └── 📂 agent/
│       └── quiz_agent.py      # ADK Agent: monta contexto + chama Gemini
│
├── 📂 frontend/
│   └── app.py                 # Interface Streamlit (toda a UI)
│
└── 📂 scripts/
    └── ingest.py              # Script de ingestão (rodar uma vez)
```

**Princípio de separação de responsabilidades:**
- `ingestion/` — só sabe transformar PDF em dados indexados
- `rag/` — só sabe buscar no ChromaDB
- `agent/` — só sabe orquestrar o ADK e gerar questões
- `frontend/` — só sabe exibir a UI e gerenciar estado

---

## ⚙️ Como instalar e executar

### Pré-requisitos

- Python 3.10 ou superior
- Conta no [Google AI Studio](https://aistudio.google.com) para obter sua API Key
- O arquivo `data_source/easa_propulsao.pdf`

### Passo 1 — Clone e configure o ambiente

```bash
# Entre na pasta do projeto
cd quiz_propulsao

# Crie um ambiente virtual (boa prática!)
python -m venv .venv

# Ative o ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### Passo 2 — Instale as dependências

```bash
pip install -r requirements.txt
```

**O que será instalado e por quê:**

| Pacote | Versão mín. | Para que serve |
|---|---|---|
| `google-adk` | 1.0.0 | Framework de agentes de IA (Google) |
| `google-generativeai` | 0.8.0 | SDK legado (necessário por dependências) |
| `chromadb` | 0.6.0 | Banco de dados vetorial local |
| `streamlit` | 1.40.0 | Interface web em Python |
| `pypdf` | 4.3.0 | Extração de texto de PDFs |
| `python-dotenv` | 1.0.0 | Leitura do arquivo `.env` |
| `pydantic` | 2.0.0 | Validação de dados (usado pelo ADK) |

### Passo 3 — Configure as variáveis de ambiente

Crie (ou edite) o arquivo `.env` na raiz do projeto:

```bash
# .env
GOOGLE_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-2.5-flash
```

> 💡 **Como obter sua API Key:** Acesse [aistudio.google.com](https://aistudio.google.com), faça login com sua conta Google e clique em "Get API Key". O plano gratuito é suficiente para estudar.

### Passo 4 — Execute o pipeline de ingestão

Este passo precisa ser feito **apenas uma vez** (ou sempre que o PDF mudar):

```bash
python scripts/ingest.py
```

Você verá algo como:
```
=== Ingestion pipeline started ===
Source: .../data_source/easa_propulsao.pdf

[1/3] Extracting text from PDF…
      25 pages extracted

[2/3] Chunking text…
      89 chunks created

[3/3] Embedding & storing in ChromaDB…
  [50/89] chunks indexed…
  [89/89] chunks indexed…

=== Ingestion complete: 89 documents stored ===
```

O que acontece por baixo:
1. `pypdf` lê todas as 25 páginas do PDF
2. O texto é dividido em 89 pedaços (chunks) de ~1000 caracteres
3. Cada chunk é convertido em um vetor de 3072 números pelo Gemini
4. Os vetores são salvos no ChromaDB (pasta `chroma_db/`)

### Passo 5 — Inicie a aplicação

```bash
streamlit run frontend/app.py
```

Acesse no navegador: **http://localhost:8501**

---

## 🖥️ Fluxo de uso da aplicação

```
┌─────────────────────┐
│  TELA INICIAL       │
│                     │
│  [🚀 Gerar Quiz]    │
└────────┬────────────┘
         │ clique
         ▼
┌─────────────────────┐
│  GERANDO...         │
│  (spinner ~30s)     │
│                     │
│  Gemini 2.5 Flash   │
│  analisa o EASA e   │
│  cria 10 questões   │
└────────┬────────────┘
         │ pronto
         ▼
┌─────────────────────────────────────────────┐
│  QUESTÃO 1 DE 10            Acertos: 0/10   │
│  ██████░░░░░░░░░░░░░░  10%                  │
│                                             │
│  Em um motor turbofan de alto BPR, qual     │
│  componente gera a maior parcela de         │
│  empuxo?                                    │
│                                             │
│  ○ A — Câmara de combustão                  │
│  ○ B — Fan de baixa pressão                 │
│  ○ C — Turbina de alta pressão              │
│  ○ D — Compressor axial                     │
│                                             │
│            [✅ Confirmar resposta]           │
└────────┬────────────────────────────────────┘
         │ após confirmar
         ▼
┌─────────────────────────────────────────────┐
│  ✓ Correto! / ✗ Incorreto.                  │
│                                             │
│  [Explicação técnica detalhada baseada      │
│   no texto da EASA...]                      │
│                                             │
│            [➡️ Próxima questão]             │
└────────┬────────────────────────────────────┘
         │ após 10 questões
         ▼
┌─────────────────────┐
│  RESULTADO FINAL    │
│                     │
│  Sua pontuação:     │
│      8/10           │
│     80%             │
│                     │
│  🎯 Ótimo! Você     │
│  está muito bem     │
│  preparado.         │
│                     │
│  [Revisão detalhada │
│   de cada questão]  │
│                     │
│  [🔄 Novas Questões]│
└─────────────────────┘
```

---

## ❓ Perguntas frequentes

**P: Por que o quiz demora ~30 segundos para gerar?**
> O sistema precisa: (1) buscar contexto em 10 tópicos no ChromaDB, (2) montar um prompt grande com todo o contexto, (3) enviar para o Gemini e aguardar a geração de 10 questões completas com explicações. A maior parte do tempo é a latência da API do Google.

**P: As questões são sempre as mesmas?**
> Não. O LLM tem temperatura não-zero, então cada geração produz questões ligeiramente diferentes — mesmo usando os mesmos trechos do PDF como base. Cada sessão é única.

**P: E se eu quiser adicionar mais material (outros PDFs)?**
> Basta colocar o novo PDF em `data_source/` e modificar `scripts/ingest.py` para incluí-lo. O pipeline de ingestão pode ser adaptado para múltiplas fontes.

**P: Por que o embedding usa `RETRIEVAL_QUERY` na busca mas `RETRIEVAL_DOCUMENT` na indexação?**
> Isso é chamado de **retrieval assimétrico**. Ao indexar, você está dizendo "este é um documento a ser encontrado". Ao buscar, você está dizendo "este é uma pergunta, encontre documentos relevantes". Usar task_types diferentes melhora a qualidade da busca em ~10-15%.

**P: O projeto pode ir para produção assim?**
> Para produção com múltiplos usuários simultâneos, seria necessário:
> - Separar o backend em uma API (FastAPI/Flask)
> - Usar um banco vetorial gerenciado (Vertex AI Matching Engine, Pinecone)
> - Adicionar autenticação e rate limiting
> - Substituir o Streamlit por um frontend React/Vue
> A arquitetura atual foi desenhada para facilitar essa evolução — os componentes são independentes.

---

## 📐 Decisões de engenharia documentadas

| Decisão | Alternativa considerada | Por que esta foi escolhida |
|---|---|---|
| ChromaDB local | Qdrant, Pinecone | Sem servidor externo, ideal para prototipagem e aprendizado |
| `gemini-embedding-001` | `text-embedding-004` | O `-004` não está disponível no plano gratuito |
| Pré-busca + geração única | Loop agêntico multi-turn | Plano gratuito tem limite de 5 RPM — loop geraria 20+ chamadas |
| Thread separada para ADK | `asyncio.run()` direto | Streamlit pode ter event loop ativo; thread separada é mais segura |
| Chunking com overlap de 200 chars | Chunks sem overlap | Questões que cruzam o limite de um chunk não se perdem |
| Boundary detection por regex | Chunks fixos sempre | Preserva questões EASA completas quando detecta numeração |

---

## 📚 Recursos para aprender mais

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [What is RAG? — IBM](https://www.ibm.com/topics/retrieval-augmented-generation)
- [Gemini API — Google AI Studio](https://aistudio.google.com/)

---

*Projeto desenvolvido para fins educacionais. Todo o conteúdo das questões é derivado exclusivamente da documentação oficial EASA Part-66 Module 15.*
