// Filter Sidebar Controller — Nexo Analitics
(function () {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const val = (id) => { const el = $(id); return el ? el.value : ''; };

    const btnOpenFilter = $('btn-open-filter');
    const btnCloseFilter = $('btn-close-filter');
    const filterSidebar = $('filter-sidebar');
    const filterOverlay = $('filter-overlay');
    const btnApplyFilters = $('btn-apply-filters');
    const btnClearFilters = $('btn-clear-filters');

    window.globalFilters = {};

    function openFilterSidebar() {
        filterSidebar.classList.add('active');
        filterOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    function closeFilterSidebar() {
        filterSidebar.classList.remove('active');
        filterOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (btnOpenFilter) btnOpenFilter.addEventListener('click', openFilterSidebar);
    if (btnCloseFilter) btnCloseFilter.addEventListener('click', closeFilterSidebar);
    if (filterOverlay) filterOverlay.addEventListener('click', closeFilterSidebar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && filterSidebar.classList.contains('active')) closeFilterSidebar();
    });

    // ---- Popular listas a partir da API
    function populateFilterLists() {
        fetch('/api/filter-options/')
            .then((r) => r.json())
            .then((data) => {
                const map = {
                    'ufs': data.ufs, 'comarcas': data.comarcas,
                    'orgao-origem': data.orgao_origem, 'orgao-julgador': data.orgao_julgador,
                    'tribunais': data.tribunais, 'partes': data.partes, 'cnpj': data.cnpj,
                    'advogados': data.advogados, 'magistrados': data.magistrados,
                    'tipo-cargos': data.tipo_cargos, 'desfecho': data.desfecho,
                    'assuntos': data.assuntos, 'classes': data.classes,
                    'tipos-recurso': data.tipos_recurso, 'tipos-pedido': data.tipos_pedido,
                };
                Object.keys(map).forEach((k) => populateList('list-' + k, 'search-' + k, map[k] || []));
            })
            .catch((e) => console.error('Erro ao carregar opções de filtro:', e));
    }

    function populateList(listId, searchId, items) {
        const listEl = $(listId), searchEl = $(searchId);
        if (!listEl || !searchEl) return;
        renderListItems(listEl, items);
        searchEl.addEventListener('input', function () {
            const t = this.value.toLowerCase();
            renderListItems(listEl, items.filter((i) => String(i).toLowerCase().includes(t)));
        });
    }

    function renderListItems(listEl, items) {
        if (!items.length) { listEl.innerHTML = '<div class="filter-list-empty">Nenhum item encontrado</div>'; return; }
        const field = listEl.id.replace('list-', '');
        listEl.innerHTML = items.map((item, i) => `
            <div class="filter-list-item">
                <input type="checkbox" id="${field}-${i}" name="${field}" value="${String(item).replace(/"/g, '&quot;')}">
                <label for="${field}-${i}">${item}</label>
            </div>`).join('');
    }

    const checked = (prefix) =>
        Array.from(document.querySelectorAll(`input[type="checkbox"][id^="${prefix}"]:checked`)).map((c) => c.value);
    const radio = (name) => { const el = document.querySelector(`input[name="${name}"]:checked`); return el ? el.value : ''; };
    const num = (id) => { const v = val(id); return v === '' ? null : parseFloat(v); };

    function collectFilters() {
        const f = {};
        f.ufs = checked('ufs');
        f.comarcas = checked('comarcas');
        f.orgao_origem = checked('orgao-origem');
        f.orgao_julgador = checked('orgao-julgador');
        f.tribunais = checked('tribunais');
        f.partes = checked('partes');
        f.cnpj = checked('cnpj');
        f.advogados = checked('advogados');
        f.magistrados = checked('magistrados');
        f.tipo_cargos = checked('tipo-cargos');
        f.status = checked('status');
        f.fase = checked('fase');
        f.desfecho = checked('desfecho');
        f.assuntos = checked('assuntos');
        f.classes = checked('classes');
        f.tipos_recurso = checked('tipos-recurso');
        f.tipos_pedido = checked('tipos-pedido');
        f.jurisdicao = checked('jurisdicao');

        if (val('filter-tipo-data')) f.tipo_data = val('filter-tipo-data');
        if (val('filter-data-inicio')) f.data_inicio = val('filter-data-inicio');
        if (val('filter-data-fim')) f.data_fim = val('filter-data-fim');

        const ranges = {
            valor_causa: ['filter-valor-causa-min', 'filter-valor-causa-max'],
            valor_condenacao: ['filter-valor-condenacao-min', 'filter-valor-condenacao-max'],
            valor_acordo: ['filter-valor-acordo-min', 'filter-valor-acordo-max'],
        };
        Object.keys(ranges).forEach((k) => {
            const mn = num(ranges[k][0]), mx = num(ranges[k][1]);
            if (mn !== null) f[k + '_min'] = mn;
            if (mx !== null) f[k + '_max'] = mx;
        });

        if (radio('transito')) f.transito = radio('transito');
        if (radio('bloqueio')) f.bloqueio = radio('bloqueio');
        if (radio('revelia')) f.revelia = radio('revelia');

        // remove chaves vazias para deixar o payload limpo
        Object.keys(f).forEach((k) => {
            const v = f[k];
            if (v == null || (Array.isArray(v) && v.length === 0) || v === '') delete f[k];
        });
        return f;
    }

    function countActive(f) { return Object.keys(f).length; }

    if (btnApplyFilters) btnApplyFilters.addEventListener('click', function () {
        const filters = collectFilters();
        window.globalFilters = filters;
        const n = countActive(filters);
        if (n > 0) {
            btnOpenFilter.classList.add('has-filters');
            let b = btnOpenFilter.querySelector('.filter-count-badge');
            if (b) b.textContent = n;
            else btnOpenFilter.insertAdjacentHTML('beforeend', `<span class="filter-count-badge">${n}</span>`);
        } else {
            btnOpenFilter.classList.remove('has-filters');
            const b = btnOpenFilter.querySelector('.filter-count-badge');
            if (b) b.remove();
        }
        document.dispatchEvent(new CustomEvent('filtersApplied', { detail: filters }));
        closeFilterSidebar();
    });

    if (btnClearFilters) btnClearFilters.addEventListener('click', function () {
        document.querySelectorAll('.filter-sidebar input[type="checkbox"], .filter-sidebar input[type="radio"]').forEach((c) => (c.checked = false));
        document.querySelectorAll('.filter-sidebar input[type="text"], .filter-sidebar input[type="number"], .filter-sidebar input[type="date"]').forEach((i) => (i.value = ''));
        document.querySelectorAll('.filter-sidebar select').forEach((s) => (s.value = ''));
        document.querySelectorAll('.filter-search-input').forEach((i) => { i.value = ''; i.dispatchEvent(new Event('input')); });
        window.globalFilters = {};
        btnOpenFilter.classList.remove('has-filters');
        const b = btnOpenFilter.querySelector('.filter-count-badge');
        if (b) b.remove();
        document.dispatchEvent(new CustomEvent('filtersCleared'));
    });

    document.addEventListener('DOMContentLoaded', populateFilterLists);
})();
