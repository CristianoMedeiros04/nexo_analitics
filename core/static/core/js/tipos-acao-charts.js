/**
 * Gráficos do módulo Tipos de Ação
 */

/**
 * Gráfico 1: Volume de processos por classe CNJ
 */
function initVolumeClasseChart(data) {
    const trace = {
        x: data.values,
        y: data.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#91cc75',  // Verde claro
            cornerradius: 5
        },
        text: data.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Total: %{x:,.0f}<extra></extra>'
    };

    const layout = {
        xaxis: {
            title: '',
            showgrid: true,
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
        height: Math.max(400, data.labels.length * 30),
        showlegend: false,
        hovermode: 'closest'
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    Plotly.newPlot('volumeClasseChart', [trace], layout, config);
}

/**
 * Gráfico 2: Volume de processos por assunto
 */
function initVolumeAssuntoChart(data) {
    const trace = {
        x: data.values,
        y: data.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#9a7fb8',  // Roxo/Lilás
            cornerradius: 5
        },
        text: data.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Total: %{x:,.0f}<extra></extra>'
    };

    const layout = {
        xaxis: {
            title: '',
            showgrid: true,
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
        height: Math.max(400, data.labels.length * 30),
        showlegend: false,
        hovermode: 'closest'
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    Plotly.newPlot('volumeAssuntoChart', [trace], layout, config);
}

/**
 * Gráfico 3: Volume de processos por pedidos
 */
function initVolumePedidosChart(data) {
    const trace = {
        x: data.values,
        y: data.labels.map(label => label + '    '),
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#ee6666',  // Coral/Salmão
            cornerradius: 5
        },
        text: data.values.map(v => v.toLocaleString('pt-BR')),
        textposition: 'outside',
        hovertemplate: '<b>%{y}</b><br>Total: %{x:,.0f}<extra></extra>'
    };

    const layout = {
        xaxis: {
            title: '',
            showgrid: true,
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
        height: Math.max(400, data.labels.length * 30),
        showlegend: false,
        hovermode: 'closest'
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    Plotly.newPlot('volumePedidosChart', [trace], layout, config);
}
