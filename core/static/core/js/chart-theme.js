/* ============================================================
   Nexo Analitics — tema global de gráficos
   Aplica uma linguagem visual única a TODOS os gráficos
   (ECharts + Plotly) interceptando a inicialização, sem
   precisar editar cada módulo.
   ============================================================ */
(function () {
    'use strict';

    var PALETTE = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#f43f5e',
        '#8b5cf6', '#14b8a6', '#f97316', '#3b82f6', '#d946ef', '#22c55e', '#ec4899'];
    var INK = '#0f172a', MUTED = '#64748b', LINE = '#eef1f6';
    var FONT = "'Inter', system-ui, sans-serif";

    window.NEXO_PALETTE = PALETTE;
    // gradiente reutilizável (ECharts) — do brand-1 ao transparente
    window.nexoAreaGradient = function (color) {
        return {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
                { offset: 0, color: color + 'cc' },
                { offset: 1, color: color + '05' },
            ],
        };
    };

    /* ---------------- ECharts ---------------- */
    if (window.echarts) {
        var theme = {
            color: PALETTE,
            backgroundColor: 'transparent',
            textStyle: { fontFamily: FONT, color: MUTED },
            title: {
                textStyle: { fontFamily: FONT, color: INK, fontWeight: 700, fontSize: 15 },
                subtextStyle: { color: MUTED },
            },
            legend: {
                textStyle: { color: MUTED, fontFamily: FONT, fontSize: 12 },
                icon: 'roundRect', itemWidth: 11, itemHeight: 11, itemGap: 16,
            },
            grid: { left: 12, right: 18, top: 28, bottom: 12, containLabel: true },
            categoryAxis: {
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: MUTED, fontFamily: FONT, fontSize: 11.5 },
                splitLine: { show: false },
            },
            valueAxis: {
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: MUTED, fontFamily: FONT, fontSize: 11.5 },
                splitLine: { lineStyle: { color: LINE, type: 'dashed' } },
            },
            tooltip: {
                backgroundColor: 'rgba(15,23,42,.94)',
                borderWidth: 0, padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: FONT, fontSize: 12.5 },
                extraCssText: 'border-radius:12px;box-shadow:0 18px 40px -12px rgba(15,23,42,.4);',
                axisPointer: { lineStyle: { color: '#cbd5e1' }, crossStyle: { color: '#cbd5e1' } },
            },
            bar: { itemStyle: { borderRadius: [6, 6, 0, 0] }, barMaxWidth: 42 },
            line: { smooth: true, symbol: 'circle', symbolSize: 7, lineStyle: { width: 3 } },
            pie: {
                itemStyle: { borderColor: '#fff', borderWidth: 3 },
                label: { color: INK, fontFamily: FONT },
            },
        };
        try { echarts.registerTheme('nexo', theme); } catch (e) {}

        // injeta o tema quando o módulo chama echarts.init(dom) sem tema
        var _init = echarts.init;
        echarts.init = function (dom, t, opts) {
            if (t === undefined || t === null) t = 'nexo';
            return _init.call(echarts, dom, t, opts);
        };
    }

    /* ---------------- Plotly ---------------- */
    if (window.Plotly) {
        var baseLayout = {
            font: { family: FONT, color: MUTED, size: 12 },
            colorway: PALETTE,
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            margin: { l: 48, r: 20, t: 28, b: 44 },
            hoverlabel: {
                bgcolor: 'rgba(15,23,42,.94)', bordercolor: 'rgba(15,23,42,0)',
                font: { family: FONT, color: '#fff', size: 12.5 },
            },
            xaxis: { gridcolor: LINE, zerolinecolor: LINE, linecolor: LINE, tickfont: { color: MUTED } },
            yaxis: { gridcolor: LINE, zerolinecolor: LINE, linecolor: LINE, tickfont: { color: MUTED } },
            legend: { font: { color: MUTED } },
        };

        function mergeDeep(base, over) {
            var out = Object.assign({}, base);
            Object.keys(over || {}).forEach(function (k) {
                if (over[k] && typeof over[k] === 'object' && !Array.isArray(over[k]) && base[k]) {
                    out[k] = mergeDeep(base[k], over[k]);
                } else { out[k] = over[k]; }
            });
            return out;
        }

        ['newPlot', 'react'].forEach(function (fn) {
            var orig = Plotly[fn];
            if (!orig) return;
            Plotly[fn] = function (gd, data, layout, config) {
                layout = mergeDeep(baseLayout, layout || {});
                config = Object.assign({ displayModeBar: false, responsive: true }, config || {});
                return orig.call(Plotly, gd, data, layout, config);
            };
        });
    }

    /* -------- Ponte do FILTRO GERAL --------
       Injeta window.globalFilters em toda chamada POST aos endpoints de
       dados, de forma que TODOS os módulos respeitem o filtro sem precisar
       reescrever cada fetch. */
    var _fetch = window.fetch;
    window.fetch = function (input, init) {
        try {
            var url = typeof input === 'string' ? input : (input && input.url) || '';
            var isData = /\/api\/.*(-data|dashboard-data)/.test(url);
            init = init || {};
            var method = (init.method || (typeof input !== 'string' && input.method) || 'GET').toUpperCase();
            if (isData && method === 'POST' && window.globalFilters) {
                var body = {};
                if (typeof init.body === 'string') { try { body = JSON.parse(init.body); } catch (e) { body = {}; } }
                // filtros primeiro; parâmetros do gráfico (do módulo) prevalecem
                init.body = JSON.stringify(Object.assign({}, window.globalFilters, body));
            }
        } catch (e) { /* nunca quebra o fetch */ }
        return _fetch.call(window, input, init);
    };

    // Recarrega os gráficos do módulo atual quando o filtro muda.
    function reload() { if (typeof window.__nexoReload === 'function') { try { window.__nexoReload(); } catch (e) {} } }
    document.addEventListener('filtersApplied', reload);
    document.addEventListener('filtersCleared', reload);
})();
