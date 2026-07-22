// ===========================
// GRÁFICO 1: Volume de Processos por Tipo de Desfecho
// ===========================
function criarGraficoVolumeDesfechos(data) {
    console.log('Criando gráfico de volume de desfechos:', data);
    
    if (!data || !data.labels || data.labels.length === 0) {
        document.getElementById('grafico-volume-desfechos').innerHTML = '<p style="text-align: center; color: #999;">Nenhum dado disponível</p>';
        return;
    }
    
    const trace = {
        x: data.values,
        y: data.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#2b538f',
            cornerradius: 5
        },
        text: data.values,
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Quantidade: %{x}<extra></extra>'
    };
    
    const layout = {
        margin: { l: 250, r: 100, t: 20, b: 50 },
        xaxis: {
            title: 'Quantidade de Processos',
            showgrid: true,
            gridcolor: '#f0f0f0',
            fixedrange: true
        },
        yaxis: {
            automargin: true,
            fixedrange: true,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        height: data.labels.length * 40 + 100,
        showlegend: false,
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-volume-desfechos', [trace], layout, config);
}

// ===========================
// GRÁFICO 2: Ranking por Tipo de Desfecho
// ===========================
let rankingDesfechosData = null;
let desfechoSelecionado = 'todos';
let criterioSelecionado = 'comarca';

function criarRankingDesfechos(data) {
    console.log('Criando ranking de desfechos:', data);
    rankingDesfechosData = data;
    
    // Preencher dropdown de desfechos - por enquanto mantém apenas "Tipos de desfecho"
    const selector = document.getElementById('desfecho-selector');
    selector.innerHTML = '<option value="todos">Tipos de desfecho</option>';
    
    // Event listener para dropdown
    selector.addEventListener('change', function(e) {
        desfechoSelecionado = e.target.value;
        atualizarRankingDesfechos();
    });
    
    // Event listeners para tabs de critério
    document.querySelectorAll('.ranking-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Remover active de todos
            document.querySelectorAll('.ranking-tab').forEach(t => t.classList.remove('active'));
            // Adicionar active no clicado
            this.classList.add('active');
            // Atualizar critério
            criterioSelecionado = this.getAttribute('data-criterio');
            atualizarRankingDesfechos();
        });
    });
    
    // Renderizar gráfico inicial
    atualizarRankingDesfechos();
}

function atualizarRankingDesfechos() {
    if (!rankingDesfechosData) {
        document.getElementById('grafico-ranking-desfechos').innerHTML = '<p style="text-align: center; color: #999;">Nenhum dado disponível</p>';
        return;
    }
    
    // Obter dados do critério selecionado
    const criterioData = rankingDesfechosData[criterioSelecionado];
    
    if (!criterioData || !criterioData.labels || criterioData.labels.length === 0) {
        document.getElementById('grafico-ranking-desfechos').innerHTML = '<p style="text-align: center; color: #999;">Nenhum dado disponível para este critério</p>';
        return;
    }
    
    // Pegar top 20
    const labels = criterioData.labels.slice(0, 20);
    const values = criterioData.values.slice(0, 20);
    
    const trace = {
        x: values,
        y: labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#2b538f',
            cornerradius: 5
        },
        text: values,
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Quantidade: %{x}<extra></extra>'
    };
    
    const layout = {
        margin: { l: 300, r: 100, t: 20, b: 50 },
        xaxis: {
            title: 'Quantidade de Processos',
            showgrid: true,
            gridcolor: '#f0f0f0',
            fixedrange: true
        },
        yaxis: {
            title: '',
            fixedrange: true,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        height: labels.length * 40 + 100,
        showlegend: false,
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-ranking-desfechos', [trace], layout, config);
}

// ===========================
// GRÁFICO 3: Decisões por Instâncias
// ===========================
function criarGraficoDecisoesInstancias(data) {
    console.log('Criando gráfico de decisões por instâncias:', data);
    
    if (!data || !data.labels || data.labels.length === 0) {
        document.getElementById('grafico-decisoes-instancias').innerHTML = '<p style="text-align: center; color: #999;">Nenhum dado disponível</p>';
        return;
    }
    
    // Cores para diferentes instâncias
    const cores = {
        'primeira_instancia': '#2b538f',
        'segunda_instancia': '#4a90e2',
        'instancia_superior': '#7cb5ec'
    };
    
    const nomes = {
        'primeira_instancia': '1ª Instância',
        'segunda_instancia': '2ª Instância',
        'instancia_superior': 'Instância Superior'
    };
    
    const traces = [];
    
    // Criar uma trace para cada instância
    ['primeira_instancia', 'segunda_instancia', 'instancia_superior'].forEach(instancia => {
        if (data[instancia]) {
            const trace = {
                x: data[instancia],
                y: data.labels.map(label => label + '    '),
                name: nomes[instancia],
                type: 'bar',
                orientation: 'h',
                marker: {
                    color: cores[instancia],
                    cornerradius: 5
                },
                hovertemplate: '<b>%{y}</b><br>' + nomes[instancia] + ': %{x}<extra></extra>'
            };
            traces.push(trace);
        }
    });
    
    const layout = {
        barmode: 'stack',
        margin: { l: 250, r: 100, t: 80, b: 50 },
        xaxis: {
            title: 'Quantidade de Processos',
            showgrid: true,
            gridcolor: '#f0f0f0',
            fixedrange: true
        },
        yaxis: {
            automargin: true,
            fixedrange: true,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        height: data.labels.length * 50 + 150,
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'top',
            y: 1.15,
            xanchor: 'center',
            x: 0.5
        },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-decisoes-instancias', traces, layout, config);
}
