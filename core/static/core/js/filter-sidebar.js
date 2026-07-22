// Filter Sidebar Controller
(function() {
    'use strict';
    
    // Elements
    const btnOpenFilter = document.getElementById('btn-open-filter');
    const btnCloseFilter = document.getElementById('btn-close-filter');
    const filterSidebar = document.getElementById('filter-sidebar');
    const filterOverlay = document.getElementById('filter-overlay');
    const btnApplyFilters = document.getElementById('btn-apply-filters');
    const btnClearFilters = document.getElementById('btn-clear-filters');
    
    // Global filters object
    window.globalFilters = {};
    
    // Open sidebar
    function openFilterSidebar() {
        filterSidebar.classList.add('active');
        filterOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    // Close sidebar
    function closeFilterSidebar() {
        filterSidebar.classList.remove('active');
        filterOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // Event listeners
    btnOpenFilter.addEventListener('click', openFilterSidebar);
    btnCloseFilter.addEventListener('click', closeFilterSidebar);
    filterOverlay.addEventListener('click', closeFilterSidebar);
    
    // ESC key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && filterSidebar.classList.contains('active')) {
            closeFilterSidebar();
        }
    });
    
    // Populate filter lists with data from API
    function populateFilterLists() {
        fetch('/api/filter-options/')
            .then(response => response.json())
            .then(data => {
                // UFs
                populateList('list-ufs', 'search-ufs', data.ufs || []);
                
                // Comarcas
                populateList('list-comarcas', 'search-comarcas', data.comarcas || []);
                
                // Órgão de Origem
                populateList('list-orgao-origem', 'search-orgao-origem', data.orgao_origem || []);
                
                // Órgão Julgador
                populateList('list-orgao-julgador', 'search-orgao-julgador', data.orgao_julgador || []);
                
                // Tribunais
                populateList('list-tribunais', 'search-tribunais', data.tribunais || []);
                
                // Partes
                populateList('list-partes', 'search-partes', data.partes || []);
                
                // CNPJ
                populateList('list-cnpj', 'search-cnpj', data.cnpj || []);
                
                // Advogados
                populateList('list-advogados', 'search-advogados', data.advogados || []);
                
                // Magistrados
                populateList('list-magistrados', 'search-magistrados', data.magistrados || []);
                
                // Tipo de Cargos
                populateList('list-tipo-cargos', 'search-tipo-cargos', data.tipo_cargos || []);
                
                // Cargos
                populateList('list-cargos', 'search-cargos', data.cargos || []);
                
                // Desfecho
                populateList('list-desfecho', 'search-desfecho', data.desfecho || []);
                
                // Assuntos
                populateList('list-assuntos', 'search-assuntos', data.assuntos || []);
                
                // Classes
                populateList('list-classes', 'search-classes', data.classes || []);
                
                // Tipos de Recurso
                populateList('list-tipos-recurso', 'search-tipos-recurso', data.tipos_recurso || []);
                
                // Tipos de Pedido
                populateList('list-tipos-pedido', 'search-tipos-pedido', data.tipos_pedido || []);
            })
            .catch(error => {
                console.error('Erro ao carregar opções de filtro:', error);
            });
    }
    
    // Populate a single list with checkboxes
    function populateList(listId, searchId, items) {
        const listElement = document.getElementById(listId);
        const searchInput = document.getElementById(searchId);
        
        if (!listElement || !searchInput) return;
        
        // Store original items
        listElement.dataset.items = JSON.stringify(items);
        
        // Render items
        renderListItems(listElement, items);
        
        // Search functionality
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const filteredItems = items.filter(item => 
                item.toLowerCase().includes(searchTerm)
            );
            renderListItems(listElement, filteredItems);
        });
    }
    
    // Render list items
    function renderListItems(listElement, items) {
        if (items.length === 0) {
            listElement.innerHTML = '<div class="filter-list-empty">Nenhum item encontrado</div>';
            return;
        }
        
        const fieldName = listElement.id.replace('list-', '');
        
        listElement.innerHTML = items.map((item, index) => `
            <div class="filter-list-item">
                <input type="checkbox" id="${fieldName}-${index}" name="${fieldName}" value="${item}">
                <label for="${fieldName}-${index}">${item}</label>
            </div>
        `).join('');
    }
    
    // Collect all filter values
    function collectFilters() {
        const filters = {};
        
        // UFs
        filters.ufs = getCheckedValues('ufs');
        
        // Comarcas
        filters.comarcas = getCheckedValues('comarcas');
        
        // Órgão de Origem
        filters.orgao_origem = getCheckedValues('orgao-origem');
        
        // Órgão Julgador
        filters.orgao_julgador = getCheckedValues('orgao-julgador');
        
        // Tribunais
        filters.tribunais = getCheckedValues('tribunais');
        
        // Partes
        filters.partes = getCheckedValues('partes');
        
        // CNPJ
        filters.cnpj = getCheckedValues('cnpj');
        
        // Advogados
        filters.advogados = getCheckedValues('advogados');
        
        // Magistrados
        filters.magistrados = getCheckedValues('magistrados');
        
        // Tipo de Cargos
        filters.tipo_cargos = getCheckedValues('tipo-cargos');
        
        // Cargos
        filters.cargos = getCheckedValues('cargos');
        
        // Tipo de Data
        const tipoData = document.getElementById('filter-tipo-data').value;
        if (tipoData) filters.tipo_data = tipoData;
        
        // Período
        const dataInicio = document.getElementById('filter-data-inicio').value;
        const dataFim = document.getElementById('filter-data-fim').value;
        if (dataInicio) filters.data_inicio = dataInicio;
        if (dataFim) filters.data_fim = dataFim;
        
        // Status do Processo
        filters.status = getCheckedValues('status');
        
        // Fase
        filters.fase = getCheckedValues('fase');
        
        // Desfecho
        filters.desfecho = getCheckedValues('desfecho');
        
        // Assuntos
        filters.assuntos = getCheckedValues('assuntos');
        
        // Classes
        filters.classes = getCheckedValues('classes');
        
        // Tipos de Recurso
        filters.tipos_recurso = getCheckedValues('tipos-recurso');
        
        // Tipos de Pedido
        filters.tipos_pedido = getCheckedValues('tipos-pedido');
        
        // Valores
        const valorCausaMin = document.getElementById('filter-valor-causa-min').value;
        const valorCausaMax = document.getElementById('filter-valor-causa-max').value;
        if (valorCausaMin) filters.valor_causa_min = parseFloat(valorCausaMin);
        if (valorCausaMax) filters.valor_causa_max = parseFloat(valorCausaMax);
        
        const valorCondenacaoMin = document.getElementById('filter-valor-condenacao-min').value;
        const valorCondenacaoMax = document.getElementById('filter-valor-condenacao-max').value;
        if (valorCondenacaoMin) filters.valor_condenacao_min = parseFloat(valorCondenacaoMin);
        if (valorCondenacaoMax) filters.valor_condenacao_max = parseFloat(valorCondenacaoMax);
        
        const valorAcordoMin = document.getElementById('filter-valor-acordo-min').value;
        const valorAcordoMax = document.getElementById('filter-valor-acordo-max').value;
        if (valorAcordoMin) filters.valor_acordo_min = parseFloat(valorAcordoMin);
        if (valorAcordoMax) filters.valor_acordo_max = parseFloat(valorAcordoMax);
        
        const valorLiquidacaoMin = document.getElementById('filter-valor-liquidacao-min').value;
        const valorLiquidacaoMax = document.getElementById('filter-valor-liquidacao-max').value;
        if (valorLiquidacaoMin) filters.valor_liquidacao_min = parseFloat(valorLiquidacaoMin);
        if (valorLiquidacaoMax) filters.valor_liquidacao_max = parseFloat(valorLiquidacaoMax);
        
        const valorDepositoMin = document.getElementById('filter-valor-deposito-min').value;
        const valorDepositoMax = document.getElementById('filter-valor-deposito-max').value;
        if (valorDepositoMin) filters.valor_deposito_min = parseFloat(valorDepositoMin);
        if (valorDepositoMax) filters.valor_deposito_max = parseFloat(valorDepositoMax);
        
        const valorApoliceMin = document.getElementById('filter-valor-apolice-min').value;
        const valorApoliceMax = document.getElementById('filter-valor-apolice-max').value;
        if (valorApoliceMin) filters.valor_apolice_min = parseFloat(valorApoliceMin);
        if (valorApoliceMax) filters.valor_apolice_max = parseFloat(valorApoliceMax);
        
        // Trânsito em Julgado
        const transito = document.querySelector('input[name="transito"]:checked');
        if (transito) filters.transito = transito.value;
        
        // Acordo
        const acordo = document.querySelector('input[name="acordo"]:checked');
        if (acordo) filters.acordo = acordo.value;
        
        // Bloqueio
        const bloqueio = document.querySelector('input[name="bloqueio"]:checked');
        if (bloqueio) filters.bloqueio = bloqueio.value;
        
        // Desfecho do Pedido de Substituição
        filters.desfecho_substituicao = getCheckedValues('desfecho-sub');
        
        // Grau de Jurisdição
        filters.jurisdicao = getCheckedValues('jurisdicao');
        
        // Maior Grau de Jurisdição
        filters.maior_jurisdicao = getCheckedValues('maior-jurisdicao');
        
        return filters;
    }
    
    // Helper function to get checked values
    function getCheckedValues(prefix) {
        const checkboxes = document.querySelectorAll(`input[type="checkbox"][id^="${prefix}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    // Apply filters
    btnApplyFilters.addEventListener('click', function() {
        console.log('=== BOTÃO APLICAR FILTROS CLICADO ===');
        
        const filters = collectFilters();
        console.log('Filtros coletados:', filters);
        console.log('Número de chaves:', Object.keys(filters).length);
        
        window.globalFilters = filters;
        
        // Count active filters
        const filterCount = Object.keys(filters).filter(key => {
            const value = filters[key];
            const isActive = value && (Array.isArray(value) ? value.length > 0 : true);
            if (isActive) {
                console.log(`Filtro ativo: ${key} =`, value);
            }
            return isActive;
        }).length;
        
        console.log('Total de filtros ativos:', filterCount);
        
        // Update button appearance
        if (filterCount > 0) {
            btnOpenFilter.classList.add('has-filters');
            const existingBadge = btnOpenFilter.querySelector('.filter-count-badge');
            if (existingBadge) {
                existingBadge.textContent = filterCount;
            } else {
                btnOpenFilter.insertAdjacentHTML('beforeend', `<span class="filter-count-badge">${filterCount}</span>`);
            }
        } else {
            btnOpenFilter.classList.remove('has-filters');
            const existingBadge = btnOpenFilter.querySelector('.filter-count-badge');
            if (existingBadge) existingBadge.remove();
        }
        
        // Trigger custom event for charts to update
        console.log('Disparando evento filtersApplied com dados:', filters);
        const event = new CustomEvent('filtersApplied', { detail: filters });
        document.dispatchEvent(event);
        console.log('Evento filtersApplied disparado');
        
        // Close sidebar
        closeFilterSidebar();
        
        console.log('=== FIM DA APLICAÇÃO DE FILTROS ===');
    });
    
    // Clear filters
    btnClearFilters.addEventListener('click', function() {
        // Clear all checkboxes
        document.querySelectorAll('.filter-sidebar input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        // Clear all radio buttons
        document.querySelectorAll('.filter-sidebar input[type="radio"]').forEach(rb => rb.checked = false);
        
        // Clear all text inputs
        document.querySelectorAll('.filter-sidebar input[type="text"]').forEach(input => input.value = '');
        
        // Clear all number inputs
        document.querySelectorAll('.filter-sidebar input[type="number"]').forEach(input => input.value = '');
        
        // Clear all date inputs
        document.querySelectorAll('.filter-sidebar input[type="date"]').forEach(input => input.value = '');
        
        // Clear all selects
        document.querySelectorAll('.filter-sidebar select').forEach(select => select.value = '');
        
        // Clear search inputs
        document.querySelectorAll('.filter-search-input').forEach(input => {
            input.value = '';
            // Trigger input event to refresh lists
            input.dispatchEvent(new Event('input'));
        });
        
        // Reset global filters
        window.globalFilters = {};
        
        // Remove badge
        btnOpenFilter.classList.remove('has-filters');
        const existingBadge = btnOpenFilter.querySelector('.filter-count-badge');
        if (existingBadge) existingBadge.remove();
        
        // Trigger event
        const event = new CustomEvent('filtersCleared');
        document.dispatchEvent(event);
        
        console.log('Filtros limpos');
    });
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        populateFilterLists();
    });
    
})();
