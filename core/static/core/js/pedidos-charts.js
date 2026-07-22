// Variáveis globais para controle de filtros
let pedidoConcessaoSelecionado = 'antecipacao_tutela';
let resultadoConcessaoSelecionado = 'concedida';
let agrupamentoSelecionado = 'comarca';

// Carregar dados ao iniciar a página
document.addEventListener('DOMContentLoaded', function() {
    carregarGraficoVolumeDeferimentos();
    carregarGraficoProporcaoDeferimentos();
    carregarGraficoRankingConcessoes();
    
    // Event listeners para dropdowns
    setupDropdowns();
    
    // Event listeners para botões de agrupamento
    document.querySelectorAll('[data-agrupamento]').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remover active de todos
            document.querySelectorAll('[data-agrupamento]').forEach(b => b.classList.remove('active'));
            // Adicionar active no clicado
            this.classList.add('active');
            // Atualizar variável e recarregar
            agrupamentoSelecionado = this.dataset.agrupamento;
            carregarGraficoRankingConcessoes();
        });
    });
});

function setupDropdowns() {
    // Dropdown Pedido de Concessão
    const dropdownPedidoBtn = document.getElementById('dropdown-pedido-btn');
    const dropdownPedido = document.getElementById('dropdown-pedido');
    const selectedPedido = document.getElementById('selected-pedido');
    
    dropdownPedidoBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownPedido.classList.toggle('show');
        document.getElementById('dropdown-resultado').classList.remove('show');
    });
    
    dropdownPedido.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function() {
            pedidoConcessaoSelecionado = this.dataset.value;
            selectedPedido.textContent = this.textContent;
            dropdownPedido.classList.remove('show');
            carregarGraficoRankingConcessoes();
        });
    });
    
    // Dropdown Resultado de Concessão
    const dropdownResultadoBtn = document.getElementById('dropdown-resultado-btn');
    const dropdownResultado = document.getElementById('dropdown-resultado');
    const selectedResultado = document.getElementById('selected-resultado');
    
    dropdownResultadoBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownResultado.classList.toggle('show');
        document.getElementById('dropdown-pedido').classList.remove('show');
    });
    
    dropdownResultado.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function() {
            resultadoConcessaoSelecionado = this.dataset.value;
            selectedResultado.textContent = this.textContent;
            dropdownResultado.classList.remove('show');
            carregarGraficoRankingConcessoes();
        });
    });
    
    // Fechar dropdowns ao clicar fora
    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-content').forEach(dropdown => {
            dropdown.classList.remove('show');
        });
    });
}

function carregarGraficoVolumeDeferimentos() {
    const filtros = obterFiltrosGlobais();
    
    fetch('/api/pedidos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            tipo: 'volume',
            filtros: filtros
        })
    })
    .then(response => response.json())
    .then(data => {
        renderizarGraficoVolumeDeferimentos(data);
    })
    .catch(error => console.error('Erro ao carregar dados:', error));
}

function renderizarGraficoVolumeDeferimentos(data) {
    const traces = [
        {
            name: 'CONCEDIDA',
            x: ['Justiça Gratuita', 'Antecipação de Tutela', 'Medida Liminar'],
            y: [
                data.justica_gratuita.concedida,
                data.antecipacao_tutela.concedida,
                data.medida_liminar.concedida
            ],
            type: 'bar',
            marker: { color: '#6ba3d8' },
            text: [
                data.justica_gratuita.concedida,
                data.antecipacao_tutela.concedida,
                data.medida_liminar.concedida
            ],
            textposition: 'outside',
            textfont: { size: 11 }
        },
        {
            name: 'NÃO CONCEDIDA',
            x: ['Justiça Gratuita', 'Antecipação de Tutela', 'Medida Liminar'],
            y: [
                data.justica_gratuita.nao_concedida,
                data.antecipacao_tutela.nao_concedida,
                data.medida_liminar.nao_concedida
            ],
            type: 'bar',
            marker: { color: '#7a7a7a' },
            text: [
                data.justica_gratuita.nao_concedida,
                data.antecipacao_tutela.nao_concedida,
                data.medida_liminar.nao_concedida
            ],
            textposition: 'outside',
            textfont: { size: 11 }
        },
        {
            name: 'CONCEDIDA EM PARTE',
            x: ['Justiça Gratuita', 'Antecipação de Tutela', 'Medida Liminar'],
            y: [
                data.justica_gratuita.concedida_em_parte,
                data.antecipacao_tutela.concedida_em_parte,
                data.medida_liminar.concedida_em_parte
            ],
            type: 'bar',
            marker: { color: '#a8d08d' },
            text: [
                data.justica_gratuita.concedida_em_parte,
                data.antecipacao_tutela.concedida_em_parte,
                data.medida_liminar.concedida_em_parte
            ],
            textposition: 'outside',
            textfont: { size: 11 }
        },
        {
            name: 'REVOGADA',
            x: ['Justiça Gratuita', 'Antecipação de Tutela', 'Medida Liminar'],
            y: [
                data.justica_gratuita.revogada,
                data.antecipacao_tutela.revogada,
                data.medida_liminar.revogada
            ],
            type: 'bar',
            marker: { color: '#f4a261' },
            text: [
                data.justica_gratuita.revogada,
                data.antecipacao_tutela.revogada,
                data.medida_liminar.revogada
            ],
            textposition: 'outside',
            textfont: { size: 11 }
        }
    ];
    
    const layout = {
        barmode: 'group',
        showlegend: true,
        legend: {
            orientation: 'h',
            x: 0.5,
            xanchor: 'center',
            y: -0.15
        },
        margin: { l: 60, r: 40, t: 40, b: 80 },
        xaxis: {
            title: '',
            tickfont: { size: 12 }
        },
        yaxis: {
            title: '',
            tickfont: { size: 11 }
        },
        height: 400
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('chart-volume-deferimentos', traces, layout, config);
}

function carregarGraficoProporcaoDeferimentos() {
    const filtros = obterFiltrosGlobais();
    
    fetch('/api/pedidos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            tipo: 'proporcao',
            filtros: filtros
        })
    })
    .then(response => response.json())
    .then(data => {
        renderizarGraficoProporcaoDeferimentos(data);
    })
    .catch(error => console.error('Erro ao carregar dados:', error));
}

function renderizarGraficoProporcaoDeferimentos(data) {
    // Cores conforme a imagem de referência
    const cores = [
        '#6ba3d8',  // Azul claro (Justiça Gratuita CONCEDIDA - maior fatia)
        '#7a7a7a',  // Cinza (Justiça Gratuita NÃO CONCEDIDA)
        '#4a7ba7',  // Azul escuro (Antecipação de Tutela NÃO CONCEDIDA)
        '#5a8fc4',  // Azul médio (Antecipação de Tutela CONCEDIDA)
        '#a8d08d',  // Verde (Antecipação de Tutela CONCEDIDA EM PARTE)
        '#f4a261',  // Laranja (Medida Liminar NÃO CONCEDIDA)
        '#e76f51',  // Vermelho (Medida Liminar CONCEDIDA)
        '#d4a373'   // Bege (Medida Liminar CONCEDIDA EM PARTE)
    ];
    
    const trace = {
        labels: data.labels,
        values: data.values,
        type: 'pie',
        marker: { colors: cores },
        textinfo: 'label+percent',
        textposition: 'outside',
        automargin: true,
        textfont: { size: 11 }
    };
    
    const layout = {
        showlegend: false,
        margin: { l: 20, r: 20, t: 20, b: 20 },
        height: 500
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('chart-proporcao-deferimentos', [trace], layout, config);
}

function carregarGraficoRankingConcessoes() {
    const filtros = obterFiltrosGlobais();
    
    fetch('/api/pedidos-data/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            tipo: 'ranking',
            pedido_concessao: pedidoConcessaoSelecionado,
            resultado_concessao: resultadoConcessaoSelecionado,
            agrupamento: agrupamentoSelecionado,
            filtros: filtros
        })
    })
    .then(response => response.json())
    .then(data => {
        renderizarGraficoRankingConcessoes(data);
    })
    .catch(error => console.error('Erro ao carregar dados:', error));
}

function renderizarGraficoRankingConcessoes(data) {
    const trace = {
        x: data.values,
        y: data.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: { 
            color: '#e07856',
            cornerradius: 5
        },
        text: data.values,
        textposition: 'outside',
        textfont: { size: 11 }
    };
    
    const layout = {
        showlegend: false,
        margin: { l: 250, r: 100, t: 20, b: 40 },
        xaxis: {
            title: '',
            tickfont: { size: 11 }
        },
        yaxis: {
            title: '',
            tickfont: { size: 11 },
            autorange: 'reversed',
            ticklen: 10,
            tickcolor: 'transparent'
        },
        height: 400
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('chart-ranking-concessoes', [trace], layout, config);
}

function obterFiltrosGlobais() {
    // Obter filtros do localStorage (mesma lógica dos outros módulos)
    const filtrosStr = localStorage.getItem('filtrosGlobais');
    return filtrosStr ? JSON.parse(filtrosStr) : {};
}

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

// Listener para atualização de filtros globais
window.addEventListener('filtrosAtualizados', function() {
    carregarGraficoVolumeDeferimentos();
    carregarGraficoProporcaoDeferimentos();
    carregarGraficoRankingConcessoes();
});
