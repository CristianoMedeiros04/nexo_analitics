// ============================================================================
// MÓDULO ADVOGADOS - COMPARAÇÃO
// JavaScript para gráficos com Plotly.js
// ============================================================================

// Função auxiliar para construir URL com array de parâmetros
function buildAdvogadosURL(baseURL, polo, advogados, extraParams = {}) {
    const params = new URLSearchParams();
    params.append('polo', polo);
    
    // Adicionar cada advogado como advogados[]
    advogados.forEach(adv => {
        params.append('advogados[]', adv);
    });
    
    // Adicionar parâmetros extras
    Object.entries(extraParams).forEach(([key, value]) => {
        params.append(key, value);
    });
    
    return `${baseURL}?${params.toString()}`;
}

// Função para obter advogados selecionados
function getAdvogadosSelecionados() {
    return advogadosSelecionados.filter(adv => adv !== '');
}

// Função para obter polo selecionado
function getPoloSelecionado() {
    return poloSelecionado;
}

// Carregar todos os gráficos
function carregarTodosGraficos() {
    carregarGraficoDesfechos();
    carregarGraficoDuracao();
    carregarGraficoDeferimento();
    carregarGraficoValoresMedios();
    carregarGraficoValoresTotais();
    carregarGraficoProporcaoAtivos();
}

// ============================================================================
// 1. GRÁFICO: DESFECHOS POR ADVOGADO
// ============================================================================
async function carregarGraficoDesfechos() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/desfechos/', polo, advogados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDesfechos(data);
    } catch (error) {
        console.error('Erro ao carregar desfechos:', error);
    }
}

function renderizarGraficoDesfechos(data) {
    const advogados = Object.keys(data.advogados);
    
    // Coletar todos os tipos de desfecho
    const desfechosSet = new Set();
    advogados.forEach(adv => {
        Object.keys(data.advogados[adv]).forEach(desfecho => {
            desfechosSet.add(desfecho);
        });
    });
    const desfechos = Array.from(desfechosSet);
    
    // Cores para cada tipo de desfecho
    const coresDesfechos = {
        'Pendente': '#9C27B0',
        'Procedente': '#4CAF50',
        'Acordo': '#8BC34A',
        'Improcedente': '#FF9800',
        'Parcialmente Procedente': '#CDDC39',
        'Indeferimento da Petição Inicial': '#F44336',
        'Arquivamento Ausência do Reclamante': '#E91E63',
        'Extinção sem Resolução de Mérito': '#607D8B',
        'Arquivado': '#0ea5e9',
        'Não informado': '#9E9E9E'
    };
    
    // Criar traces (uma para cada tipo de desfecho)
    const traces = desfechos.map(desfecho => {
        const valores = advogados.map(adv => data.advogados[adv][desfecho] || 0);
        
        return {
            type: 'bar',
            orientation: 'h',
            name: desfecho,
            x: valores,
            y: advogados.map(adv => adv + '    '),
            marker: {
                color: coresDesfechos[desfecho] || '#9E9E9E',
                cornerradius: 5
            },
            text: valores.map(v => v > 0 ? v : ''),
            textposition: 'inside',
            textfont: {
                color: 'white',
                size: 11
            },
            hovertemplate: '<b>%{y}</b><br>' +
                          desfecho + ': %{x}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'stack',
        height: Math.max(400, advogados.length * 60),
        margin: { l: 250, r: 100, t: 20, b: 50 },
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            autorange: 'reversed',
            fixedrange: true,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.3,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-desfechos', traces, layout, config);
}

// ============================================================================
// 2. GRÁFICO: DURAÇÃO DOS PROCESSOS
// ============================================================================
async function carregarGraficoDuracao() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/duracao/', polo, advogados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDuracao(data);
    } catch (error) {
        console.error('Erro ao carregar duração:', error);
    }
}

function renderizarGraficoDuracao(data) {
    const advogados = Object.keys(data.advogados);
    const faixas = data.faixas;
    
    // Cores para cada advogado
    const coresAdvogados = ['#0ea5e9', '#4CAF50', '#FF9800', '#9E9E9E'];
    
    // Criar traces (uma para cada advogado)
    const traces = advogados.map((adv, index) => {
        const valores = faixas.map(faixa => data.advogados[adv][faixa] || 0);
        
        return {
            type: 'bar',
            name: adv,
            x: faixas,
            y: valores,
            marker: {
                color: coresAdvogados[index % coresAdvogados.length]
            },
            text: valores.map(v => v > 0 ? v : ''),
            textposition: 'outside',
            textfont: {
                size: 11
            },
            hovertemplate: '<b>%{x}</b><br>' +
                          adv + ': %{y}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'group',
        height: 400,
        margin: { l: 50, r: 50, t: 20, b: 100 },
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.4,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-duracao', traces, layout, config);
}

// ============================================================================
// 3. GRÁFICO: DEFERIMENTO DE PEDIDOS
// ============================================================================
async function carregarGraficoDeferimento() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    const tipo = document.getElementById('deferimento-tipo').value;
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/deferimento/', polo, advogados, { tipo });
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDeferimento(data);
    } catch (error) {
        console.error('Erro ao carregar deferimento:', error);
    }
}

function renderizarGraficoDeferimento(data) {
    const advogados = Object.keys(data.advogados);
    const tiposPedidos = data.tipos_pedidos;
    
    // Cores para cada advogado
    const coresAdvogados = ['#0ea5e9', '#9E9E9E', '#4CAF50', '#FF9800'];
    
    // Criar traces (uma para cada advogado)
    const traces = advogados.map((adv, index) => {
        const valores = tiposPedidos.map(tipo => data.advogados[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: adv,
            x: tiposPedidos,
            y: valores,
            marker: {
                color: coresAdvogados[index % coresAdvogados.length]
            },
            text: valores.map(v => v > 0 ? v : ''),
            textposition: 'outside',
            textfont: {
                size: 11
            },
            hovertemplate: '<b>%{x}</b><br>' +
                          adv + ': %{y}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'group',
        height: 400,
        margin: { l: 50, r: 50, t: 20, b: 120 },
        xaxis: {
            title: '',
            fixedrange: true,
            tickangle: -45
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.5,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-deferimento', traces, layout, config);
}

// ============================================================================
// 4. GRÁFICO: VALORES MÉDIOS POR ADVOGADO
// ============================================================================
async function carregarGraficoValoresMedios() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/valores-medios/', polo, advogados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoValoresMedios(data);
    } catch (error) {
        console.error('Erro ao carregar valores médios:', error);
    }
}

function renderizarGraficoValoresMedios(data) {
    const advogados = Object.keys(data.advogados);
    const tiposValores = data.tipos_valores;
    
    // Cores para cada tipo de valor
    const coresValores = {
        'Acordo': '#0ea5e9',
        'Causa': '#607D8B',
        'Condenação': '#4CAF50',
        'Liquidação': '#FFC107'
    };
    
    // Criar traces (uma para cada tipo de valor)
    const traces = tiposValores.map(tipo => {
        const valores = advogados.map(adv => data.advogados[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: tipo,
            x: advogados,
            y: valores,
            marker: {
                color: coresValores[tipo] || '#9E9E9E'
            },
            text: valores.map(v => v > 0 ? `R$ ${v.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : ''),
            textposition: 'outside',
            textfont: {
                size: 10
            },
            hovertemplate: '<b>%{x}</b><br>' +
                          tipo + ': R$ %{y:,.2f}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'group',
        height: 400,
        margin: { l: 50, r: 50, t: 20, b: 150 },
        xaxis: {
            title: '',
            fixedrange: true,
            tickangle: -45
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.6,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-valores-medios', traces, layout, config);
}

// ============================================================================
// 5. GRÁFICO: VALORES TOTAIS POR ADVOGADO
// ============================================================================
async function carregarGraficoValoresTotais() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/valores-totais/', polo, advogados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoValoresTotais(data);
    } catch (error) {
        console.error('Erro ao carregar valores totais:', error);
    }
}

function renderizarGraficoValoresTotais(data) {
    const advogados = Object.keys(data.advogados);
    const tiposValores = data.tipos_valores;
    
    // Cores para cada tipo de valor
    const coresValores = {
        'Acordo': '#0ea5e9',
        'Causa': '#607D8B',
        'Condenação': '#4CAF50',
        'Liquidação': '#FFC107'
    };
    
    // Criar traces (uma para cada tipo de valor)
    const traces = tiposValores.map(tipo => {
        const valores = advogados.map(adv => data.advogados[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: tipo,
            x: advogados,
            y: valores,
            marker: {
                color: coresValores[tipo] || '#9E9E9E'
            },
            text: valores.map(v => v > 0 ? `R$ ${(v/1000).toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0})}k` : ''),
            textposition: 'inside',
            textfont: {
                color: 'white',
                size: 10
            },
            hovertemplate: '<b>%{x}</b><br>' +
                          tipo + ': R$ %{y:,.2f}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'stack',
        height: 400,
        margin: { l: 50, r: 50, t: 20, b: 150 },
        xaxis: {
            title: '',
            fixedrange: true,
            tickangle: -45
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.6,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-valores-totais', traces, layout, config);
}

// ============================================================================
// 6. GRÁFICO: PROPORÇÃO ENTRE PROCESSOS ATIVOS E TOTAL
// ============================================================================
async function carregarGraficoProporcaoAtivos() {
    const advogados = getAdvogadosSelecionados();
    const polo = getPoloSelecionado();
    
    if (advogados.length === 0) return;
    
    try {
        const url = buildAdvogadosURL('/api/advogados/proporcao-ativos/', polo, advogados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoProporcaoAtivos(data);
    } catch (error) {
        console.error('Erro ao carregar proporção ativos:', error);
    }
}

function renderizarGraficoProporcaoAtivos(data) {
    const advogados = Object.keys(data.advogados);
    
    // Trace para Total
    const traceTotal = {
        type: 'bar',
        orientation: 'h',
        name: 'Todos',
        x: advogados.map(adv => data.advogados[adv].total),
        y: advogados.map(adv => adv + '    '),
        marker: {
            color: '#bae6fd',
            cornerradius: 5
        },
        text: advogados.map(adv => data.advogados[adv].total),
        textposition: 'inside',
        textfont: {
            color: 'white',
            size: 11
        },
        hovertemplate: '<b>%{y}</b><br>' +
                      'Total: %{x}<br>' +
                      '<extra></extra>'
    };
    
    // Trace para Ativos
    const traceAtivos = {
        type: 'bar',
        orientation: 'h',
        name: 'Ativos',
        x: advogados.map(adv => data.advogados[adv].ativos),
        y: advogados.map(adv => adv + '    '),
        marker: {
            color: '#607D8B',
            cornerradius: 5
        },
        text: advogados.map(adv => data.advogados[adv].ativos),
        textposition: 'inside',
        textfont: {
            color: 'white',
            size: 11
        },
        hovertemplate: '<b>%{y}</b><br>' +
                      'Ativos: %{x}<br>' +
                      '<extra></extra>'
    };
    
    const traces = [traceTotal, traceAtivos];
    
    const layout = {
        barmode: 'group',
        height: Math.max(400, advogados.length * 80),
        margin: { l: 250, r: 100, t: 20, b: 50 },
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            autorange: 'reversed',
            fixedrange: true,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.2,
            xanchor: 'center',
            x: 0.5,
            font: { size: 10 }
        },
        hovermode: 'closest'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('chart-proporcao-ativos', traces, layout, config);
}
