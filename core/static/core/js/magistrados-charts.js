// ============================================================================
// MÓDULO MAGISTRADOS - COMPARAÇÃO
// JavaScript para gráficos com Plotly.js
// ============================================================================

// Função auxiliar para construir URL com array de parâmetros
function buildMagistradosURL(baseURL, polo, magistrados, extraParams = {}) {
    const params = new URLSearchParams();
    params.append('polo', polo);
    
    // Adicionar cada magistrado como magistrados[]
    magistrados.forEach(adv => {
        params.append('magistrados[]', adv);
    });
    
    // Adicionar parâmetros extras
    Object.entries(extraParams).forEach(([key, value]) => {
        params.append(key, value);
    });
    
    return `${baseURL}?${params.toString()}`;
}

// Função para obter magistrados selecionados
function getMagistradosSelecionados() {
    return magistradosSelecionados.filter(adv => adv !== '');
}

// Função para obter polo selecionado
function getPoloSelecionado() {
    return poloSelecionado;
}

// Carregar todos os gráficos
function carregarTodosGraficos() {
    carregarGraficoDesfechos();
    carregarGraficoDecisoes();
    carregarGraficoDuracao();
    carregarGraficoDeferimento();
    carregarGraficoValoresMedios();
    carregarGraficoValoresTotais();
    carregarGraficoProporcaoAtivos();
}

// ============================================================================
// 1. GRÁFICO: DESFECHOS POR MAGISTRADO
// ============================================================================
async function carregarGraficoDesfechos() {
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/desfechos/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDesfechos(data);
    } catch (error) {
        console.error('Erro ao carregar desfechos:', error);
    }
}

function renderizarGraficoDesfechos(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todos os tipos de desfecho
    const desfechosSet = new Set();
    magistrados.forEach(adv => {
        Object.keys(data[adv]).forEach(desfecho => {
            desfechosSet.add(desfecho);
        });
    });
    const desfechos = Array.from(desfechosSet);
    
    // Cores para cada tipo de desfecho (paleta diversificada)
    const coresDesfechos = {
        'Pendente': '#9C27B0',                     // Roxo
        'Procedente': '#4CAF50',                   // Verde
        'Parcialmente Procedente': '#FDD835',      // Amarelo
        'Improcedente': '#FF7043',                 // Laranja
        'Acordo': '#42A5F5',                       // Azul
        'Arquivado': '#26A69A',                    // Teal
        'Indeferimento da Petição Inicial': '#F44336',           // Vermelho
        'Arquivamento Ausência do Reclamante': '#E91E63',        // Rosa
        'Extinção sem Resolução de Mérito': '#6366f1',           // Índigo
        'Extinção': '#AB47BC',                     // Roxo claro
        'Homologação de Acordo': '#29B6F6',        // Azul claro
        'Não informado': '#BDBDBD'                // Cinza
    };
    
    // Criar traces (uma para cada tipo de desfecho)
    const traces = desfechos.map(desfecho => {
        const valores = magistrados.map(adv => data[adv][desfecho] || 0);
        
        return {
            type: 'bar',
            orientation: 'h',
            name: desfecho,
            x: valores,
            y: magistrados.map(mag => mag + '    '),
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
        height: Math.max(400, magistrados.length * 60),
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
// 2. GRÁFICO: DECISÕES POR MAGISTRADO
// ============================================================================
async function carregarGraficoDecisoes() {
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/decisoes/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDecisoes(data);
    } catch (error) {
        console.error('Erro ao carregar decisões:', error);
    }
}

function renderizarGraficoDecisoes(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todos os tipos de decisão
    const decisoesSet = new Set();
    magistrados.forEach(mag => {
        Object.keys(data[mag]).forEach(decisao => {
            decisoesSet.add(decisao);
        });
    });
    const decisoes = Array.from(decisoesSet);
    
    // Cores para cada tipo de decisão (paleta diversificada)
    const coresDecisoes = {
        'Totalmente Procedente': '#4CAF50',        // Verde
        'Procedente': '#66BB6A',                   // Verde claro
        'Parcialmente Procedente': '#FDD835',      // Amarelo
        'Improcedente': '#FF7043',                 // Laranja
        'Acordo': '#42A5F5',                       // Azul
        'Extinção': '#AB47BC',                     // Roxo
        'Provido': '#26A69A',                      // Teal
        'Não Provido': '#EF5350',                  // Vermelho
        'Parcialmente Provido': '#FFA726',         // Laranja claro
        'Conhecido': '#6366f1',                    // Índigo
        'Não Conhecido': '#EC407A',                // Rosa
        'Desprovido': '#8D6E63',                   // Marrom
        'Não-Acolhimento de Embargos de Declaração': '#78909C',  // Cinza azulado
        'Indeferimento da Petição Inicial': '#F44336',           // Vermelho escuro
        'Arquivamento Ausência do Reclamante': '#E91E63',        // Rosa escuro
        'Extinção sem Resolução de Mérito': '#9575CD',           // Roxo claro
        'Audiência das Condições da Ação': '#29B6F6',            // Azul claro
        'Outros': '#BDBDBD'                        // Cinza
    };
    
    // Criar traces (uma para cada tipo de decisão)
    const traces = decisoes.map(decisao => {
        const valores = magistrados.map(mag => data[mag][decisao] || 0);
        
        return {
            type: 'bar',
            orientation: 'h',
            name: decisao,
            x: valores,
            y: magistrados.map(mag => mag + '    '),
            marker: {
                color: coresDecisoes[decisao] || '#9E9E9E',
                cornerradius: 5
            },
            text: valores.map(v => v > 0 ? v : ''),
            textposition: 'inside',
            textfont: {
                color: 'white',
                size: 11
            },
            hovertemplate: '<b>%{y}</b><br>' +
                          decisao + ': %{x}<br>' +
                          '<extra></extra>'
        };
    });
    
    const layout = {
        barmode: 'stack',
        height: Math.max(400, magistrados.length * 60),
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
    
    Plotly.newPlot('chart-decisoes', traces, layout, config);
}

// ============================================================================
// 3. GRÁFICO: DURAÇÃO DOS PROCESSOS
// ============================================================================
async function carregarGraficoDuracao() {
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/duracao/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDuracao(data);
    } catch (error) {
        console.error('Erro ao carregar duração:', error);
    }
}

function renderizarGraficoDuracao(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todas as faixas de duração
    const faixasSet = new Set();
    magistrados.forEach(mag => {
        Object.keys(data[mag]).forEach(faixa => {
            faixasSet.add(faixa);
        });
    });
    const faixas = Array.from(faixasSet);
    
    // Cores para cada magistrado
    const coresMagistrados = ['#0ea5e9', '#4CAF50', '#FF9800', '#9E9E9E'];
    
    // Criar traces (uma para cada magistrado)
    const traces = magistrados.map((adv, index) => {
        const valores = faixas.map(faixa => data[adv][faixa] || 0);
        
        return {
            type: 'bar',
            name: adv,
            x: faixas,
            y: valores,
            marker: {
                color: coresMagistrados[index % coresMagistrados.length]
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
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    const tipo = document.getElementById('deferimento-tipo').value;
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/deferimento/', polo, magistrados, { tipo });
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoDeferimento(data);
    } catch (error) {
        console.error('Erro ao carregar deferimento:', error);
    }
}

function renderizarGraficoDeferimento(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todos os tipos de pedidos
    const tiposSet = new Set();
    magistrados.forEach(mag => {
        Object.keys(data[mag]).forEach(tipo => {
            tiposSet.add(tipo);
        });
    });
    const tiposPedidos = Array.from(tiposSet);
    
    // Cores para cada magistrado
    const coresMagistrados = ['#0ea5e9', '#9E9E9E', '#4CAF50', '#FF9800'];
    
    // Criar traces (uma para cada magistrado)
    const traces = magistrados.map((adv, index) => {
        const valores = tiposPedidos.map(tipo => data[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: adv,
            x: tiposPedidos,
            y: valores,
            marker: {
                color: coresMagistrados[index % coresMagistrados.length]
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
// 4. GRÁFICO: VALORES MÉDIOS POR MAGISTRADO
// ============================================================================
async function carregarGraficoValoresMedios() {
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/valores-medios/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoValoresMedios(data);
    } catch (error) {
        console.error('Erro ao carregar valores médios:', error);
    }
}

function renderizarGraficoValoresMedios(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todos os tipos de valores
    const tiposSet = new Set();
    magistrados.forEach(mag => {
        Object.keys(data[mag]).forEach(tipo => {
            tiposSet.add(tipo);
        });
    });
    const tiposValores = Array.from(tiposSet);
    
    // Cores para cada tipo de valor
    const coresValores = {
        'Acordo': '#0ea5e9',
        'Causa': '#607D8B',
        'Condenação': '#4CAF50',
        'Liquidação': '#FFC107'
    };
    
    // Criar traces (uma para cada tipo de valor)
    const traces = tiposValores.map(tipo => {
        const valores = magistrados.map(adv => data[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: tipo,
            x: magistrados,
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
// 5. GRÁFICO: VALORES TOTAIS POR MAGISTRADO
// ============================================================================
async function carregarGraficoValoresTotais() {
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/valores-totais/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoValoresTotais(data);
    } catch (error) {
        console.error('Erro ao carregar valores totais:', error);
    }
}

function renderizarGraficoValoresTotais(data) {
    const magistrados = Object.keys(data);
    
    // Coletar todos os tipos de valores
    const tiposSet = new Set();
    magistrados.forEach(mag => {
        Object.keys(data[mag]).forEach(tipo => {
            tiposSet.add(tipo);
        });
    });
    const tiposValores = Array.from(tiposSet);
    
    // Cores para cada tipo de valor
    const coresValores = {
        'Acordo': '#0ea5e9',
        'Causa': '#607D8B',
        'Condenação': '#4CAF50',
        'Liquidação': '#FFC107'
    };
    
    // Criar traces (uma para cada tipo de valor)
    const traces = tiposValores.map(tipo => {
        const valores = magistrados.map(adv => data[adv][tipo] || 0);
        
        return {
            type: 'bar',
            name: tipo,
            x: magistrados,
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
    const magistrados = getMagistradosSelecionados();
    const polo = getPoloSelecionado();
    
    if (magistrados.length === 0) return;
    
    try {
        const url = buildMagistradosURL('/api/magistrados/proporcao-ativos/', polo, magistrados);
        const response = await fetch(url);
        const data = await response.json();
        
        renderizarGraficoProporcaoAtivos(data);
    } catch (error) {
        console.error('Erro ao carregar proporção ativos:', error);
    }
}

function renderizarGraficoProporcaoAtivos(data) {
    const magistrados = Object.keys(data);
    
    // Trace para Total
    const traceTotal = {
        type: 'bar',
        orientation: 'h',
        name: 'Todos',
        x: magistrados.map(adv => data[adv].total),
        y: magistrados.map(mag => mag + '    '),
        marker: {
            color: '#bae6fd',
            cornerradius: 5
        },
        text: magistrados.map(adv => data[adv].total),
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
        x: magistrados.map(adv => data[adv].ativos),
        y: magistrados.map(mag => mag + '    '),
        marker: {
            color: '#607D8B',
            cornerradius: 5
        },
        text: magistrados.map(adv => data[adv].ativos),
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
        height: Math.max(400, magistrados.length * 80),
        margin: { l: 250, r: 100, t: 20, b: 50 },
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            autorange: 'reversed',
            fixedrange: true
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
