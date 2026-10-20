/* Interaksi peta SVG lokal. Angka dan warna berasal dari server. */
(() => {
    "use strict";
    const svg = document.getElementById("population-map");
    const source = document.getElementById("population-map-data");
    if (!svg || !source) return;
    const payload = JSON.parse(source.textContent);
    const provinces = new Map(payload.provinces.map(row => [row.key, row]));
    const shapes = [...svg.querySelectorAll("[data-province]")];
    const select = document.getElementById("map-province-select");
    const tip = document.getElementById("map-tooltip");
    const viewport = document.getElementById("map-viewport");
    const format = value => new Intl.NumberFormat("id-ID", {maximumFractionDigits: 0}).format(value);
    let selected = "", view = {x:0,y:0,w:960,h:390}, drag = null, moved = false;
    function describe(key) {
        const row = provinces.get(key);
        if (!row) return;
        document.getElementById("map-province-name").textContent = row.name;
        document.getElementById("map-population-value").textContent = row.people === null ? "Tidak tersedia" : `${format(row.people)} jiwa`;
        document.getElementById("map-population-category").textContent = row.people === null ? "Wilayah ini belum memiliki nilai pada tahun yang dipilih; tidak dianggap nol." : `Kelompok warna: ${row.category} penduduk.`;
        document.getElementById("map-status").textContent = `${row.name} · ${payload.year} · ${row.people === null ? "data tidak tersedia" : format(row.people)+" jiwa"}`;
    }
    function choose(key) {
        selected = key;
        select.value = key;
        shapes.forEach(shape => {const active = shape.dataset.province === key; shape.classList.toggle("is-selected",active);shape.setAttribute("aria-pressed",String(active));});
        describe(key);
        // Pilihan wilayah juga memperbarui grafik perkembangan demografi.
        const region = document.getElementById("population-region");
        const row = provinces.get(key);
        if (region && row) {region.value = row.name;region.dispatchEvent(new Event("change"));}
    }
    function hideTip() {tip.hidden = true;}
    function showTip(shape, event) {
        if (drag && moved) return;
        const row = provinces.get(shape.dataset.province);
        if (!row) return;
        describe(row.key);
        tip.textContent = `${row.name} · ${row.people === null ? "Data tidak tersedia" : format(row.people)+" jiwa"}`;
        tip.hidden = false;
        const r = viewport.getBoundingClientRect();
        const point = event && Number.isFinite(event.clientX) ? {x:event.clientX,y:event.clientY} : (()=>{const b=shape.getBoundingClientRect();return{x:b.left+b.width/2,y:b.top};})();
        tip.style.left = `${Math.max(5,Math.min(point.x-r.left+12,r.width-tip.offsetWidth-5))}px`;
        tip.style.top = `${Math.max(5,Math.min(point.y-r.top-40,r.height-tip.offsetHeight-5))}px`;
    }
    shapes.forEach(shape => {
        shape.addEventListener("pointerenter",event=>showTip(shape,event));
        shape.addEventListener("pointermove",event=>showTip(shape,event));
        shape.addEventListener("pointerleave",hideTip);
        shape.addEventListener("focus",()=>showTip(shape));
        shape.addEventListener("blur",hideTip);
        shape.addEventListener("click",()=>{if(!moved)choose(shape.dataset.province);});
        shape.addEventListener("keydown",event=>{if(event.key==="Enter" || event.key===" "){event.preventDefault();choose(shape.dataset.province);}});
    });
    select.addEventListener("change",()=>{if(select.value)choose(select.value);});
    function updateView() {
        view.x = Math.max(0,Math.min(960-view.w,view.x));
        view.y = Math.max(0,Math.min(390-view.h,view.y));
        svg.setAttribute("viewBox",`${view.x} ${view.y} ${view.w} ${view.h}`);
        document.getElementById("map-zoom-out").disabled = view.w >= 960;
        document.getElementById("map-zoom-in").disabled = view.w <= 160;
        hideTip();
    }
    function zoom(factor) {
        const width=Math.max(160,Math.min(960,view.w*factor));
        const height=width*390/960;
        view={x:view.x+(view.w-width)/2,y:view.y+(view.h-height)/2,w:width,h:height};updateView();
    }
    document.getElementById("map-zoom-in").addEventListener("click",()=>zoom(1/1.5));
    document.getElementById("map-zoom-out").addEventListener("click",()=>zoom(1.5));
    document.getElementById("map-reset").addEventListener("click",()=>{view={x:0,y:0,w:960,h:390};updateView();});
    svg.addEventListener("pointerdown",event=>{
        if(event.button!==0)return;
        const matrix=svg.getScreenCTM();
        drag={x:event.clientX,y:event.clientY,view:{...view},scale:matrix ? matrix.a : 1};moved=false;
    });
    svg.addEventListener("pointermove",event=>{
        if(!drag)return;
        const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
        if(Math.hypot(dx,dy)>4){moved=true;svg.setPointerCapture(event.pointerId);svg.classList.add("is-dragging");}
        if(moved){view={...drag.view,x:drag.view.x-dx/drag.scale,y:drag.view.y-dy/drag.scale};updateView();}
    });
    const endDrag=()=>{drag=null;svg.classList.remove("is-dragging");};
    svg.addEventListener("pointerup",endDrag);svg.addEventListener("pointercancel",endDrag);
    updateView();
})();
