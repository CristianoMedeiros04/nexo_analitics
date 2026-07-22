// ========================================
// GRÁFICO 1: DURAÇÃO DE PROCESSOS POR FASE
// ========================================

function criarGraficoDuracaoFase(dados) {
    // Preparar dados para o gráfico
    const ufs = Object.keys(dados).sort();
    
    const conhecimentoValues = ufs.map(uf => dados[uf]['Conhecimento'] || 0);
    const liquidacaoValues = ufs.map(uf => dados[uf]['Liquidação'] || 0);
    const execucaoValues = ufs.map(uf => dados[uf]['Execução'] || 0);
    
    const trace1 = {
        x: ufs,
        y: conhecimentoValues,
        name: 'Conhecimento',
        type: 'bar',
        marker: {
            color: '#6baed6' // Azul claro
        },
        text: conhecimentoValues.map(v => v.toString()),
        textposition: 'outside',
        textfont: {
            size: 10
        }
    };
    
    const trace2 = {
        x: ufs,
        y: liquidacaoValues,
        name: 'Liquidação',
        type: 'bar',
        marker: {
            color: '#636363' // Cinza escuro
        },
        text: liquidacaoValues.map(v => v.toString()),
        textposition: 'outside',
        textfont: {
            size: 10
        }
    };
    
    const trace3 = {
        x: ufs,
        y: execucaoValues,
        name: 'Execução',
        type: 'bar',
        marker: {
            color: '#74c476' // Verde claro
        },
        text: execucaoValues.map(v => v.toString()),
        textposition: 'outside',
        textfont: {
            size: 10
        }
    };
    
    const layout = {
        barmode: 'group',
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        legend: {
            orientation: 'h',
            x: 0.5,
            xanchor: 'center',
            y: 1.15,
            yanchor: 'top'
        },
        margin: {
            l: 50,
            r: 20,
            t: 60,
            b: 50
        },
        height: 400
    };
    
    const config = {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-duracao-fase', [trace1, trace2, trace3], layout, config);
}


// ========================================
// GRÁFICO 2: QUANTIDADE POR DURAÇÃO E POR FASE
// ========================================

let dadosQuantidadeDuracao = null;

function criarGraficoQuantidadeDuracao(dados) {
    dadosQuantidadeDuracao = dados;
    
    // Renderizar gráfico inicial (Conhecimento)
    renderizarGraficoQuantidadeDuracao('Conhecimento');
    
    // Adicionar event listeners nos botões de fase
    document.querySelectorAll('.fase-tab').forEach(button => {
        button.addEventListener('click', function() {
            // Remover classe active de todos
            document.querySelectorAll('.fase-tab').forEach(btn => btn.classList.remove('active'));
            
            // Adicionar classe active no botão clicado
            this.classList.add('active');
            
            // Renderizar gráfico da fase selecionada
            const fase = this.getAttribute('data-fase');
            renderizarGraficoQuantidadeDuracao(fase);
        });
    });
}

function renderizarGraficoQuantidadeDuracao(fase) {
    if (!dadosQuantidadeDuracao || !dadosQuantidadeDuracao[fase]) {
        console.error('Dados não disponíveis para a fase:', fase);
        return;
    }
    
    const dadosFase = dadosQuantidadeDuracao[fase];
    
    const trace = {
        x: dadosFase.values,
        y: dadosFase.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#9370db',  // Roxo médio
            cornerradius: 5
        },
        text: dadosFase.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        textfont: {
            size: 11
        }
    };
    
    const layout = {
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
        margin: {
            l: 250,
            r: 100,
            t: 20,
            b: 40
        },
        height: 400
    };
    
    const config = {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-quantidade-duracao', [trace], layout, config);
}


// ========================================
// GRÁFICO 3: DURAÇÃO DE PROCESSOS POR MARCO
// ========================================

let dadosDuracaoMarco = null;

function criarGraficoDuracaoMarco(dados) {
    dadosDuracaoMarco = dados;
    
    // Renderizar gráfico inicial (Distribuição -> Acordo)
    renderizarGraficoDuracaoMarco('Distribuição', 'Acordo');
    
    // Adicionar event listeners nos selects
    document.getElementById('marco-inicial').addEventListener('change', function() {
        const marcoInicial = this.value;
        const marcoFinal = document.getElementById('marco-final').value;
        renderizarGraficoDuracaoMarco(marcoInicial, marcoFinal);
    });
    
    document.getElementById('marco-final').addEventListener('change', function() {
        const marcoInicial = document.getElementById('marco-inicial').value;
        const marcoFinal = this.value;
        renderizarGraficoDuracaoMarco(marcoInicial, marcoFinal);
    });
}

function renderizarGraficoDuracaoMarco(marcoInicial, marcoFinal) {
    const chave = `${marcoInicial}_${marcoFinal}`;
    
    if (!dadosDuracaoMarco || !dadosDuracaoMarco[chave]) {
        console.log('Dados não disponíveis para:', chave);
        
        // Mostrar gráfico vazio
        const layout = {
            xaxis: {
                title: '',
                fixedrange: true
            },
            yaxis: {
                title: '',
                fixedrange: true
            },
            annotations: [{
                text: 'Dados não disponíveis para esta combinação de marcos',
                xref: 'paper',
                yref: 'paper',
                x: 0.5,
                y: 0.5,
                xanchor: 'center',
                yanchor: 'middle',
                showarrow: false,
                font: {
                    size: 14,
                    color: '#999'
                }
            }],
            margin: {
                l: 50,
                r: 20,
                t: 20,
                b: 50
            },
            height: 400
        };
        
        const config = {
            displayModeBar: false,
            responsive: true,
            scrollZoom: false
        };
        
        Plotly.newPlot('grafico-duracao-marco', [], layout, config);
        return;
    }
    
    const dadosMarco = dadosDuracaoMarco[chave];
    const ufs = Object.keys(dadosMarco).sort();
    const values = ufs.map(uf => dadosMarco[uf]);
    
    const trace = {
        x: ufs,
        y: values,
        type: 'bar',
        marker: {
            color: '#66c2a5' // Verde água
        },
        text: values.map(v => v.toString()),
        textposition: 'outside',
        textfont: {
            size: 10
        }
    };
    
    const layout = {
        xaxis: {
            title: '',
            fixedrange: true
        },
        yaxis: {
            title: '',
            fixedrange: true
        },
        margin: {
            l: 50,
            r: 20,
            t: 20,
            b: 50
        },
        height: 400
    };
    
    const config = {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
    };
    
    Plotly.newPlot('grafico-duracao-marco', [trace], layout, config);
}
