# Sistema de Jurimetria

Sistema web escalável de jurimetria (análise quantitativa de dados jurídicos) desenvolvido com Django e Django REST Framework.

## 🚀 Características

- **Dashboard Interativo**: Visualização de estatísticas e gráficos interativos
- **API REST**: Endpoints para acesso programático aos dados
- **Arquitetura Escalável**: Estrutura modular preparada para expansões futuras
- **Interface Moderna**: Design responsivo com Bootstrap 5 e Material Icons
- **Gráficos Dinâmicos**: Visualizações interativas com Plotly.js

## 📊 Funcionalidades Implementadas

### Tela Inicial (Dashboard)
- **Cards Informativos**: 6 indicadores principais
  - Total de processos
  - Processos distribuídos nos últimos 30 dias
  - Processos arquivados nos últimos 30 dias
  - Processos transitados em julgado nos últimos 30 dias
  - Valor total das causas
  - Valor médio das causas

- **Visualizações**:
  - Mapa de processos ativos por UF
  - Lista de processos por UF
  - Gráfico de duração média de processos
  - Processos ativos por fase
  - Processos ativos por comarca
  - Valor médio de causa por UF
  - Valor médio de condenação por UF

### API REST
- Endpoint `/api/processos/` - Listagem de processos com filtros
- Endpoint `/api/dashboard-data/` - Dados agregados para o dashboard
- Filtros disponíveis: UF, comarca, fase, situação
- Busca textual por número de processo

## 🛠️ Tecnologias Utilizadas

### Backend
- Python 3.11
- Django 5.0
- Django REST Framework 3.14.0
- django-filter 23.5
- django-cors-headers 4.3.1
- Gunicorn 21.2.0
- SQLite3

### Frontend
- HTML5 + CSS3
- Bootstrap 5.3.0
- Google Material Icons
- Plotly.js 2.27.0
- JavaScript (ES6+)

## 📦 Instalação e Configuração

### Requisitos
- Python 3.11 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo (Windows)

1. **Extrair o projeto**
   ```bash
   # Extrair o arquivo ZIP para uma pasta de sua escolha
   ```

2. **Criar ambiente virtual**
   ```bash
   python -m venv venv
   ```

3. **Ativar o ambiente virtual**
   ```bash
   # Windows
   venv\Scripts\activate
   ```

4. **Instalar dependências**
   ```bash
   pip install -r requirements.txt
   ```

5. **Executar o servidor**
   ```bash
   python manage.py runserver
   ```

6. **Acessar o sistema**
   - Abra o navegador e acesse: `http://localhost:8000`

## 📁 Estrutura do Projeto

```
jurimetria_project/
├── jurimetria/              # Configurações do projeto Django
│   ├── settings.py          # Configurações principais
│   ├── urls.py              # Rotas principais
│   └── wsgi.py              # Configuração WSGI
├── core/                    # App principal (interface web)
│   ├── templates/           # Templates HTML
│   ├── static/              # Arquivos estáticos
│   ├── models.py            # Modelos de dados
│   ├── views.py             # Views da interface
│   ├── charts.py            # Processamento de dados para gráficos
│   └── urls.py              # Rotas do core
├── api/                     # App da API REST
│   ├── serializers.py       # Serializers DRF
│   ├── views.py             # Views da API
│   └── urls.py              # Rotas da API
├── templates/               # Templates globais
│   └── base.html            # Template base
├── static/                  # Arquivos estáticos globais
├── Banco_de_Dados.db        # Banco de dados SQLite
├── manage.py                # Script de gerenciamento Django
├── requirements.txt         # Dependências Python
└── README.md                # Este arquivo
```

## 🔧 Configuração para Produção

Para deploy em produção, utilize o Gunicorn:

```bash
gunicorn jurimetria.wsgi:application --bind 0.0.0.0:8000
```

## 📚 Módulos Futuros (Estrutura Preparada)

O sistema foi desenvolvido com arquitetura escalável para suportar os seguintes módulos:

- Legal Assistant (BETA)
- Acordos
- Bloqueios
- Desfechos
- Distribuição
- Duração
- Revelias
- Preparos recursais
- Recursos
- Pedidos
- Valores
- Advogados
- Magistrados
- Mercado
- Lista

## 🎨 Paleta de Cores

- **Primary**: #3f51b5 (Azul/Roxo)
- **Secondary**: #5c6bc0 (Azul/Roxo claro)
- **Success**: #81c784 (Verde)
- **Info**: #64b5f6 (Azul claro)
- **Warning**: #ffb74d (Laranja)
- **Danger**: #e57373 (Vermelho)

## 📝 Notas Importantes

- O banco de dados `Banco_de_Dados.db` contém dados reais e não deve ser modificado
- O sistema usa `managed=False` nos modelos para não interferir com o banco existente
- Todas as datas estão no formato brasileiro (dd/mm/yyyy)
- Valores monetários estão no formato brasileiro (R$ 1.234,56)

## 🔒 Segurança

**IMPORTANTE**: Este projeto está configurado para desenvolvimento. Para produção:
- Altere a `SECRET_KEY` no `settings.py`
- Configure `DEBUG = False`
- Configure `ALLOWED_HOSTS` adequadamente
- Use variáveis de ambiente para informações sensíveis
- Configure HTTPS
- Implemente autenticação e autorização

## 📧 Suporte

Para dúvidas ou sugestões, entre em contato com a equipe de desenvolvimento.

---

**Versão**: 1.0.0  
**Data**: Novembro 2025  
**Desenvolvido com**: Django 5.0 + Django REST Framework
