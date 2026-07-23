/* Ranking de taxa de êxito (advogados/magistrados) via IA */
(function(){
    var TIPO = window.EXITO_TIPO || 'advogados';
    var chart;
    function nomeCurto(n){ return n.replace(/\s*\([^)]*\)\s*$/,'').trim(); }
    function carregar(){
        var el=document.getElementById('exito-ranking'); if(!el||!window.echarts) return;
        fetch('/api/ranking-exito/', {method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify(Object.assign({tipo:TIPO}, window.globalFilters||{}))})
        .then(r=>r.json()).then(function(d){
            var tt=(d.top_taxa||[]).slice().reverse();
            chart = chart || echarts.init(el);
            chart.setOption({
                tooltip:{trigger:'axis', axisPointer:{type:'shadow'},
                    formatter:function(p){var i=p[0];var l=tt[i.dataIndex];
                        return nomeCurto(l.nome)+'<br/>Êxito: <b>'+l.taxa_exito+'%</b><br/>'+l.julgados+' pedidos julgados · '+l.processos+' processos';}},
                grid:{left:6,right:48,top:10,bottom:6,containLabel:true},
                xAxis:{type:'value', max:100, axisLabel:{formatter:'{value}%'}},
                yAxis:{type:'category', data:tt.map(x=>nomeCurto(x.nome)), axisLabel:{width:200, overflow:'truncate'}},
                series:[{type:'bar', data:tt.map(x=>x.taxa_exito),
                    label:{show:true, position:'right', formatter:'{c}%', color:'var(--muted)', fontWeight:600},
                    itemStyle:{borderRadius:[0,6,6,0], color:new echarts.graphic.LinearGradient(0,0,1,0,[
                        {offset:0,color:'#c7d2fe'},{offset:1,color:'#6366f1'}])}}]
            });
        }).catch(function(e){ console.error('exito:', e); });
    }
    if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', carregar); } else { carregar(); }
    document.addEventListener('filtersApplied', carregar);
    document.addEventListener('filtersCleared', carregar);
    window.addEventListener('resize', function(){ chart&&chart.resize(); });
})();
