// valores-charts.js - Gráficos do módulo Valores

// Função para carregar gráfico de ranking de valores
function carregarGraficoRankingValores() {
    // Obter filtros selecionados
    const tipoValor = document.querySelector('#tipo-valor-buttons .filter-btn.active').dataset.tipo;
    const agrupamento = document.querySelector('#agrupamento-buttons .filter-btn.active').dataset.agrupamento;
    
    // Obter filtros globais do localStorage
    const filtrosGlobais = JSON.parse(localStorage.getItem('filtrosGlobais') || '{}');
    
    // Fazer requisição para a API
    fetch('/api/valores-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            tipo_valor: tipoValor,
            agrupamento: agrupamento,
            filtros: filtrosGlobais
        })
    })
    .then(response => response.json())
    .then(data => {
        renderizarGraficoRankingValores(data);
    })
    .catch(error => {
        console.error('Erro ao carregar dados:', error);
    });
}

// Função para renderizar gráfico de ranking de valores
function renderizarGraficoRankingValores(data) {
    const trace = {
        type: 'bar',
        x: data.valores,
        y: data.labels.map(label => label + '    '),  // Espaçamento entre label e barra
        orientation: 'h',
        marker: {
            color: '#9b7bb5',  // Cor roxa/lilás conforme referência
            line: {
                width: 0
            },
            cornerradius: 5  // Arredonda pontas das barras
        },
        text: data.valores.map(v => formatarValorMonetario(v)),
        textposition: 'outside',
        textfont: {
            size: 11,
            color: '#333'
        },
        hovertemplate: '<b>%{y}</b><br>Valor médio: R$ %{x:,.2f}<extra></extra>'
    };

    const layout = {
        margin: { l: 250, r: 100, t: 20, b: 40 },
        height: Math.max(400, data.labels.length * 30),
        xaxis: {
            title: '',
            showgrid: true,
            gridcolor: '#f0f0f0',
            zeroline: false,
            tickformat: ',.0f'
        },
        yaxis: {
            title: '',
            autorange: 'reversed',
            showgrid: false,
            ticklen: 10,
            tickcolor: 'transparent'
        },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        font: {
            family: 'Roboto, sans-serif',
            size: 12,
            color: '#666'
        },
        hovermode: 'closest'
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot('ranking-valores-chart', [trace], layout, config);
}

// Função para formatar valor monetário
function formatarValorMonetario(valor) {
    if (valor >= 1000000) {
        return (valor / 1000000).toFixed(1) + 'M';
    } else if (valor >= 1000) {
        return (valor / 1000).toFixed(0) + 'k';
    } else {
        return valor.toFixed(0);
    }
}

// Função para obter cookie CSRF
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

// Listener para mudanças nos filtros globais
window.addEventListener('storage', function(e) {
    if (e.key === 'filtrosGlobais') {
        carregarGraficoRankingValores();
    }
});

// Listener para evento customizado de filtro aplicado
document.addEventListener('filtrosAplicados', function() {
    carregarGraficoRankingValores();
});
