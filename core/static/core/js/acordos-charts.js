// acordos-charts.js - Funções para criar gráficos do módulo Acordos

// 1. PROPORÇÃO DE ACORDOS POR ANO (Faixa 1)
function criarGraficoProporcaoAcordos(data) {
    const trace1 = {
        x: data.labels,
        y: data.total_processos,
        name: 'Total de Processos',
        type: 'bar',
        marker: {
            color: '#6366f1'
        }
    };
    
    const trace2 = {
        x: data.labels,
        y: data.total_acordos,
        name: 'Total de Acordos',
        type: 'bar',
        marker: {
            color: '#28a745'
        }
    };
    
    const layout = {
        barmode: 'group',
        xaxis: {
            title: 'Ano',
            showgrid: false,
            fixedrange: true
        },
        yaxis: {
            title: 'Quantidade',
            showgrid: true,
            gridcolor: '#e0e0e0',
            fixedrange: true
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {
            family: 'Roboto, sans-serif',
            size: 12,
            color: '#666'
        },
        legend: {
            orientation: 'h',
            yanchor: 'top',
            y: 1.15,
            xanchor: 'center',
            x: 0.5
        },
        margin: { l: 60, r: 40, t: 60, b: 60 }
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    try { Plotly.purge('grafico-proporcao-acordos'); } catch(e) {}
    Plotly.newPlot('grafico-proporcao-acordos', [trace1, trace2], layout, config);
}

// 2. ACORDOS POR FASE (Faixa 2)
function criarGraficoAcordosFase(data) {
    const trace = {
        type: 'bar',
        x: data.values,
        y: data.labels.map(label => label + '    '),  // Adiciona espaços para criar distância
        orientation: 'h',
        marker: {
            color: '#6366f1',
            cornerradius: 5
        },
        text: data.values.map(v => formatNumber(v)),
        textposition: 'outside'
    };
    
    const layout = {
        margin: { l: 250, r: 100, t: 20, b: 50 },
        xaxis: {
            title: 'Quantidade de Acordos',
            showgrid: true,
            gridcolor: '#e0e0e0',
            fixedrange: true
        },
        yaxis: {
            autorange: 'reversed',
            fixedrange: true
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {
            family: 'Roboto, sans-serif',
            size: 12,
            color: '#666'
        }
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    try { Plotly.purge('grafico-acordos-fase'); } catch(e) {}
    Plotly.newPlot('grafico-acordos-fase', [trace], layout, config);
}

// 3. VOLUME DE ACORDOS POR ANO (Faixa 2)
function criarGraficoVolumeAcordos(data) {
    const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
            color: '#6366f1'
        },
        text: data.values.map(v => formatCurrency(v)),
        textposition: 'outside',
        textangle: 0
    };
    
    const layout = {
        xaxis: {
            title: 'Ano',
            showgrid: false,
            fixedrange: true
        },
        yaxis: {
            title: 'Valor Total (R$)',
            showgrid: true,
            gridcolor: '#e0e0e0',
            tickformat: ',.0f',
            fixedrange: true
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {
            family: 'Roboto, sans-serif',
            size: 12,
            color: '#666'
        },
        margin: { l: 80, r: 40, t: 20, b: 60 }
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    try { Plotly.purge('grafico-volume-acordos'); } catch(e) {}
    Plotly.newPlot('grafico-volume-acordos', [trace], layout, config);
}

// 4. VALOR DE CAUSA VS ACORDO (Faixa 3)
function criarGraficoCausaAcordo(data) {
    const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
            color: ['#6366f1', '#28a745']
        },
        text: data.values.map(v => formatCurrency(v)),
        textposition: 'outside',
        textangle: 0
    };
    
    const layout = {
        xaxis: {
            showgrid: false,
            fixedrange: true
        },
        yaxis: {
            title: 'Valor Médio (R$)',
            showgrid: true,
            gridcolor: '#e0e0e0',
            tickformat: ',.0f',
            fixedrange: true
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {
            family: 'Roboto, sans-serif',
            size: 11,
            color: '#666'
        },
        margin: { l: 80, r: 20, t: 20, b: 80 }
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    try { Plotly.purge('grafico-causa-acordo'); } catch(e) {}
    Plotly.newPlot('grafico-causa-acordo', [trace], layout, config);
}

// 5. VALOR DE CONDENAÇÃO VS ACORDO (Faixa 3)
function criarGraficoCondenacaoAcordo(data) {
    const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
            color: ['#6366f1', '#28a745']
        },
        text: data.values.map(v => formatCurrency(v)),
        textposition: 'outside',
        textangle: 0
    };
    
    const layout = {
        xaxis: {
            showgrid: false,
            fixedrange: true
        },
        yaxis: {
            title: 'Valor Médio (R$)',
            showgrid: true,
            gridcolor: '#e0e0e0',
            tickformat: ',.0f',
            fixedrange: true
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        font: {
            family: 'Roboto, sans-serif',
            size: 11,
            color: '#666'
        },
        margin: { l: 80, r: 20, t: 20, b: 80 }
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    try { Plotly.purge('grafico-condenacao-acordo'); } catch(e) {}
    Plotly.newPlot('grafico-condenacao-acordo', [trace], layout, config);
}

// 6. RANKING DE ACORDOS (Faixa 4)
let rankingDataGlobal = {};

function criarRankingAcordos(data) {
    // Armazenar dados globalmente
    rankingDataGlobal = data;
    
    // Renderizar ranking inicial (comarca)
    renderizarRanking(data.comarca);
    
    // Adicionar listener para mudança de critério
    const selectorElement = document.getElementById('ranking-criterio');
    if (selectorElement && !selectorElement.hasAttribute('data-listener-added')) {
        selectorElement.addEventListener('change', function() {
            const criterio = this.value;
            renderizarRanking(rankingDataGlobal[criterio]);
        });
        selectorElement.setAttribute('data-listener-added', 'true');
    }
}

function renderizarRanking(data) {
    const container = document.getElementById('ranking-acordos');
    
    if (!data || !data.labels || data.labels.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Nenhum dado disponível</div>';
        return;
    }
    
    const maxValue = Math.max(...data.values);
    
    let html = '';
    data.labels.forEach((label, index) => {
        const value = data.values[index];
        const percentage = (value / maxValue) * 100;
        
        html += `
            <div class="ranking-item">
                <div class="ranking-position">${index + 1}º</div>
                <div class="ranking-name">${label}</div>
                <div class="ranking-bar-container">
                    <div class="ranking-bar" style="width: ${percentage}%"></div>
                </div>
                <div class="ranking-value">${formatNumber(value)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Funções auxiliares
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return new Intl.NumberFormat('pt-BR').format(Math.round(num));
}

function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}
