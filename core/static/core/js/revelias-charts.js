// revelias-charts.js - Gráficos do módulo Revelias

let dadosRevelias = null;
let criterioAtual = 'Comarca';

/**
 * Carrega dados da API de revelias
 */
function carregarDadosRevelias(filtros = {}) {
    fetch('/api/revelias-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(filtros)
    })
    .then(response => response.json())
    .then(data => {
        dadosRevelias = data;
        criarGraficoVolumeRevelias(data.volume_por_ano);
        criarGraficoRankingRevelias(data.ranking_revelias, criterioAtual);
        configurarBotoesCriterio(data.ranking_revelias);
    })
    .catch(error => {
        console.error('Erro ao carregar dados de revelias:', error);
    });
}

/**
 * Cria o gráfico de volume de revelias por ano
 */
function criarGraficoVolumeRevelias(dados) {
    const trace = {
        x: dados.labels,
        y: dados.values,
        type: 'bar',
        marker: {
            color: '#66c2a5', // Verde água
            line: {
                width: 0
            }
        },
        text: dados.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>%{x}</b><br>Revelias: %{y:,.0f}<extra></extra>'
    };

    const layout = {
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
            b: 40
        },
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };

    const config = {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
    };

    Plotly.newPlot('grafico-volume-revelias', [trace], layout, config);
}

/**
 * Cria o gráfico de ranking de revelias
 */
function criarGraficoRankingRevelias(dados, criterio) {
    const dadosCriterio = dados[criterio];
    
    if (!dadosCriterio || dadosCriterio.labels.length === 0) {
        // Se não houver dados, mostrar gráfico vazio
        document.getElementById('grafico-ranking-revelias').innerHTML = 
            '<div style="text-align: center; padding: 40px; color: #999;">Nenhum dado disponível para este critério</div>';
        return;
    }

    const trace = {
        x: dadosCriterio.values,
        y: dadosCriterio.labels.map(label => label + '    '),  // Espaçamento entre label e barra
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#ec407a', // Rosa/Magenta
            line: {
                width: 0
            },
            cornerradius: 5  // Arredonda pontas das barras
        },
        text: dadosCriterio.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 10,
            color: '#333'
        },
        hovertemplate: '<b>%{y}</b><br>Revelias: %{x:,.0f}<extra></extra>'
    };

    const layout = {
        xaxis: {
            title: '',
            fixedrange: true,
            tickformat: ',',
            tickfont: {
                size: 10
            }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            autorange: 'reversed',
            tickfont: {
                size: 10
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
        paper_bgcolor: 'white',
        height: Math.max(400, dadosCriterio.labels.length * 25)
    };

    const config = {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
    };

    Plotly.newPlot('grafico-ranking-revelias', [trace], layout, config);
}

/**
 * Configura os botões de critério
 */
function configurarBotoesCriterio(dadosRanking) {
    const botoes = document.querySelectorAll('.criterio-btn');
    
    botoes.forEach(botao => {
        botao.addEventListener('click', function() {
            // Remover classe active de todos os botões
            botoes.forEach(b => b.classList.remove('active'));
            
            // Adicionar classe active ao botão clicado
            this.classList.add('active');
            
            // Atualizar gráfico com o novo critério
            const novoCriterio = this.getAttribute('data-criterio');
            criterioAtual = novoCriterio;
            criarGraficoRankingRevelias(dadosRanking, novoCriterio);
        });
    });
}

/**
 * Obtém o cookie CSRF
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
