// recursos-charts.js

let dadosRecursos = null;
let filtrosGlobais = {};

// Estados dos controles
let criterioReversoes = 'processos';
let agruparAnoReversoes = true;

let criterioAlteracoes = 'processos';
let agruparAnoAlteracoes = true;

let poloRankingReversao = 'ativo';
let agrupamentoRankingReversao = 'comarca';

let tipoVariacaoRanking = 'aumento';
let agrupamentoRankingVariacao = 'comarca';

/**
 * Carrega dados da API de recursos
 */
window.__nexoReload = function(){ carregarDadosRecursos(window.globalFilters||{}); };
function carregarDadosRecursos(filtros = {}) {
    filtrosGlobais = filtros;
    
    // Carregar dados de cada gráfico
    carregarGraficoReversoesPolo();
    carregarGraficoAlteracoesCondenacao();
    carregarGraficoRankingReversao();
    carregarGraficoRankingVariacao();
}

/**
 * Carrega dados do gráfico de reversões por polo
 */
function carregarGraficoReversoesPolo() {
    const payload = {
        ...filtrosGlobais,
        chart_type: 'reversoes_polo',
        criterio: criterioReversoes,
        agrupar_ano: agruparAnoReversoes
    };
    
    fetch('/api/recursos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        criarGraficoReversoesPolo(data);
    })
    .catch(error => {
        console.error('Erro ao carregar dados de reversões:', error);
    });
}

/**
 * Cria o gráfico de reversões por polo
 */
function criarGraficoReversoesPolo(dados) {
    const traceAtivo = {
        x: dados.labels,
        y: dados.ativo,
        name: 'ATIVO',
        type: 'bar',
        marker: {
            color: '#5b9bd5', // Azul claro
            line: {
                width: 0
            }
        },
        text: dados.ativo.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>ATIVO</b><br>%{x}: %{y:,.0f}<extra></extra>'
    };
    
    const tracePassivo = {
        x: dados.labels,
        y: dados.passivo,
        name: 'PASSIVO',
        type: 'bar',
        marker: {
            color: '#7f7f7f', // Cinza escuro
            line: {
                width: 0
            }
        },
        text: dados.passivo.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>PASSIVO</b><br>%{x}: %{y:,.0f}<extra></extra>'
    };
    
    const layout = {
        barmode: 'group',
        xaxis: {
            title: '',
            fixedrange: true,
            tickangle: 0,
            tickfont: {
                size: 11
            }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            tickformat: ',',
            tickfont: {
                size: 11
            }
        },
        margin: {
            l: 60,
            r: 20,
            t: 20,
            b: 60
        },
        legend: {
            orientation: 'h',
            y: 1.15,
            yanchor: 'top',
            x: 0.5,
            xanchor: 'center'
        },
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('grafico-reversoes-polo', [traceAtivo, tracePassivo], layout, config);
}

/**
 * Carrega dados do gráfico de alterações de condenação
 */
function carregarGraficoAlteracoesCondenacao() {
    const payload = {
        ...filtrosGlobais,
        chart_type: 'alteracoes_condenacao',
        criterio: criterioAlteracoes,
        agrupar_ano: agruparAnoAlteracoes
    };
    
    fetch('/api/recursos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        criarGraficoAlteracoesCondenacao(data);
    })
    .catch(error => {
        console.error('Erro ao carregar dados de alterações:', error);
    });
}

/**
 * Cria o gráfico de alterações de condenação
 */
function criarGraficoAlteracoesCondenacao(dados) {
    const traceAumento = {
        x: dados.labels,
        y: dados.aumento,
        name: 'AUMENTO',
        type: 'bar',
        marker: {
            color: '#9bbb59', // Verde
            line: {
                width: 0
            }
        },
        text: dados.aumento.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>AUMENTO</b><br>%{x}: %{y:,.0f}<extra></extra>'
    };
    
    const traceReducao = {
        x: dados.labels,
        y: dados.reducao,
        name: 'REDUÇÃO',
        type: 'bar',
        marker: {
            color: '#7f7f7f', // Cinza escuro
            line: {
                width: 0
            }
        },
        text: dados.reducao.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>REDUÇÃO</b><br>%{x}: %{y:,.0f}<extra></extra>'
    };
    
    const layout = {
        barmode: 'group',
        xaxis: {
            title: '',
            fixedrange: true,
            tickangle: 0,
            tickfont: {
                size: 11
            }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            tickformat: ',',
            tickfont: {
                size: 11
            }
        },
        margin: {
            l: 60,
            r: 20,
            t: 20,
            b: 60
        },
        legend: {
            orientation: 'h',
            y: 1.15,
            yanchor: 'top',
            x: 0.5,
            xanchor: 'center'
        },
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('grafico-alteracoes-condenacao', [traceAumento, traceReducao], layout, config);
}

/**
 * Carrega dados do gráfico de ranking de reversão
 */
function carregarGraficoRankingReversao() {
    const payload = {
        ...filtrosGlobais,
        chart_type: 'ranking_reversao',
        polo: poloRankingReversao,
        agrupamento: agrupamentoRankingReversao
    };
    
    fetch('/api/recursos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        criarGraficoRankingReversao(data);
    })
    .catch(error => {
        console.error('Erro ao carregar ranking de reversão:', error);
    });
}

/**
 * Cria o gráfico de ranking de reversão
 */
function criarGraficoRankingReversao(dados) {
    const trace = {
        x: dados.values,
        y: dados.labels.map(label => label + '    '),  // Espaçamento entre label e barra
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#ed7d31', // Coral/Laranja
            line: {
                width: 0
            },
            cornerradius: 5  // Arredonda pontas das barras
        },
        text: dados.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>%{y}</b><br>Reversões: %{x:,.0f}<extra></extra>'
    };
    
    const layout = {
        xaxis: {
            title: '',
            fixedrange: true,
            tickformat: ',',
            tickfont: {
                size: 11
            }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            autorange: 'reversed',
            tickfont: {
                size: 11
            },
            ticklen: 10,
            tickcolor: 'transparent'
        },
        margin: {
            l: 250,
            r: 100,
            t: 20,
            b: 40
        },
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('grafico-ranking-reversao', [trace], layout, config);
}

/**
 * Carrega dados do gráfico de ranking de variação
 */
function carregarGraficoRankingVariacao() {
    const payload = {
        ...filtrosGlobais,
        chart_type: 'ranking_variacao',
        tipo_variacao: tipoVariacaoRanking,
        agrupamento: agrupamentoRankingVariacao
    };
    
    fetch('/api/recursos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        criarGraficoRankingVariacao(data);
    })
    .catch(error => {
        console.error('Erro ao carregar ranking de variação:', error);
    });
}

/**
 * Cria o gráfico de ranking de variação
 */
function criarGraficoRankingVariacao(dados) {
    const trace = {
        x: dados.values,
        y: dados.labels.map(label => label + '    '),  // Espaçamento entre label e barra
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#70ad47', // Verde menta
            line: {
                width: 0
            },
            cornerradius: 5  // Arredonda pontas das barras
        },
        text: dados.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>%{y}</b><br>Variações: %{x:,.0f}<extra></extra>'
    };
    
    const layout = {
        xaxis: {
            title: '',
            fixedrange: true,
            tickformat: ',',
            tickfont: {
                size: 11
            }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            autorange: 'reversed',
            tickfont: {
                size: 11
            },
            ticklen: 10,
            tickcolor: 'transparent'
        },
        margin: {
            l: 250,
            r: 100,
            t: 20,
            b: 40
        },
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('grafico-ranking-variacao', [trace], layout, config);
}

/**
 * Função auxiliar para obter cookie CSRF
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    
    // Botões de critério para gráfico de reversões
    document.querySelectorAll('[data-grafico="reversoes"][data-criterio]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="reversoes"][data-criterio]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            criterioReversoes = this.dataset.criterio;
            carregarGraficoReversoesPolo();
        });
    });
    
    // Switch agrupar por ano - reversões
    document.getElementById('switch-agrupar-reversoes').addEventListener('change', function() {
        agruparAnoReversoes = this.checked;
        carregarGraficoReversoesPolo();
    });
    
    // Botões de critério para gráfico de alterações
    document.querySelectorAll('[data-grafico="alteracoes"][data-criterio]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="alteracoes"][data-criterio]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            criterioAlteracoes = this.dataset.criterio;
            carregarGraficoAlteracoesCondenacao();
        });
    });
    
    // Switch agrupar por ano - alterações
    document.getElementById('switch-agrupar-alteracoes').addEventListener('change', function() {
        agruparAnoAlteracoes = this.checked;
        carregarGraficoAlteracoesCondenacao();
    });
    
    // Botões de polo para ranking de reversão
    document.querySelectorAll('[data-grafico="ranking-reversao"][data-polo]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="ranking-reversao"][data-polo]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            poloRankingReversao = this.dataset.polo;
            carregarGraficoRankingReversao();
        });
    });
    
    // Botões de agrupamento para ranking de reversão
    document.querySelectorAll('[data-grafico="ranking-reversao"][data-agrupamento]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="ranking-reversao"][data-agrupamento]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            agrupamentoRankingReversao = this.dataset.agrupamento;
            carregarGraficoRankingReversao();
        });
    });
    
    // Botões de tipo de variação para ranking de variação
    document.querySelectorAll('[data-grafico="ranking-variacao"][data-variacao]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="ranking-variacao"][data-variacao]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            tipoVariacaoRanking = this.dataset.variacao;
            carregarGraficoRankingVariacao();
        });
    });
    
    // Botões de agrupamento para ranking de variação
    document.querySelectorAll('[data-grafico="ranking-variacao"][data-agrupamento]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-grafico="ranking-variacao"][data-agrupamento]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            agrupamentoRankingVariacao = this.dataset.agrupamento;
            carregarGraficoRankingVariacao();
        });
    });
});
