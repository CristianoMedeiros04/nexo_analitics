/**
 * Gráficos do módulo Distribuição
 */

// Variável global para armazenar dados de ranking
let rankingDistribuicaoData = null;
let criterioAtualDistribuicao = 'comarca';

/**
 * Gráfico 1: Volume de processos distribuídos por ano
 */
function criarGraficoVolumeDistribuicao(data) {
    const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
            color: '#CD7F5F'  // Cor coral/salmão conforme imagem
        },
        text: data.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#000'
        },
        hovertemplate: '<b>%{x}</b><br>Processos: %{y:,.0f}<extra></extra>'
    };

    const layout = {
        margin: { t: 40, r: 20, b: 60, l: 80 },
        xaxis: {
            title: '',
            fixedrange: true,
            tickfont: { size: 11 }
        },
        yaxis: {
            title: '',
            fixedrange: true,
            tickfont: { size: 11 },
            tickformat: ',d'
        },
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    Plotly.newPlot('grafico-volume-distribuicao', [trace], layout, config);
}


/**
 * Gráfico 2: Ranking de distribuição de processos
 */
function criarRankingDistribuicao(data) {
    // Armazenar dados globalmente
    rankingDistribuicaoData = data;
    
    // Renderizar gráfico com critério inicial (comarca)
    renderizarRankingDistribuicao('comarca');
    
    // Adicionar event listeners aos botões de critério
    document.querySelectorAll('.ranking-tab').forEach(button => {
        button.addEventListener('click', function() {
            // Remover classe active de todos os botões
            document.querySelectorAll('.ranking-tab').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Adicionar classe active ao botão clicado
            this.classList.add('active');
            
            // Obter critério e renderizar gráfico
            const criterio = this.getAttribute('data-criterio');
            criterioAtualDistribuicao = criterio;
            renderizarRankingDistribuicao(criterio);
        });
    });
}


function renderizarRankingDistribuicao(criterio) {
    if (!rankingDistribuicaoData || !rankingDistribuicaoData[criterio]) {
        console.error('Dados não disponíveis para critério:', criterio);
        return;
    }
    
    const dados = rankingDistribuicaoData[criterio];
    
    const trace = {
        x: dados.values,
        y: dados.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#6BAED6',  // Cor azul claro conforme imagem
            cornerradius: 5
        },
        text: dados.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#000'
        },
        hovertemplate: '<b>%{y}</b><br>Processos: %{x:,.0f}<extra></extra>'
    };

    const layout = {
        margin: { t: 20, r: 100, b: 60, l: 250 },
        xaxis: {
            title: '',
            fixedrange: true,
            tickfont: { size: 11 },
            tickformat: ',d'
        },
        yaxis: {
            title: '',
            fixedrange: true,
            tickfont: { size: 11 },
            autorange: 'reversed',  // Maior valor no topo
            ticklen: 10,
            tickcolor: 'transparent'
        },
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        height: Math.max(400, dados.labels.length * 30)  // Altura dinâmica baseada no número de itens
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    Plotly.newPlot('grafico-ranking-distribuicao', [trace], layout, config);
}
