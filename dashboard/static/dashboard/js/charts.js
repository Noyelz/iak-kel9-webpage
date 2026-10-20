/* Grafik SVG lokal: tanpa CDN. Data JSON disediakan template Django. */
(() => {
    "use strict";
    const source = document.getElementById("analytics-data");
    if (!source) return;
    const data = JSON.parse(source.textContent);
    const colors = ["#065f46", "#10b981", "#5478ac", "#ad6927"];
    const format = value => value === null || value === undefined ? "—" : new Intl.NumberFormat("id-ID", {maximumFractionDigits: 4}).format(value);
    const svgNode = (tag, attrs = {}, content) => {
        const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        if (content !== undefined) node.textContent = content;
        return node;
    };
    function table(host, dataset, unit) {
        const details = document.createElement("details");
        details.className = "chart-data";
        const summary = document.createElement("summary");
        summary.textContent = "Lihat angka grafik";
        details.append(summary);
        const wrap = document.createElement("div"); wrap.className = "table-scroll";
        const tbl = document.createElement("table");
        const caption = tbl.createCaption(); caption.textContent = `Satuan: ${unit}. Tanda — berarti data tidak tersedia.`;
        const header = tbl.createTHead().insertRow();
        ["Periode / kategori", ...dataset.series.map(s => s.name)].forEach(label => {
            const th = document.createElement("th"); th.scope = "col"; th.textContent = label; header.append(th);
        });
        const body = tbl.createTBody();
        dataset.labels.forEach((label, i) => {
            const row = body.insertRow(); const th = document.createElement("th"); th.scope = "row"; th.textContent = label; row.append(th);
            dataset.series.forEach(series => { row.insertCell().textContent = format(series.values[i]); });
        });
        wrap.append(tbl); details.append(wrap); host.append(details);
    }
    function tooltip(host, element, text) {
        const show = () => {
            host.querySelector(".chart-tip")?.remove();
            const tip = document.createElement("div"); tip.className = "chart-tip"; tip.textContent = text;
            host.append(tip);
            const r = element.getBoundingClientRect(), h = host.getBoundingClientRect();
            tip.style.left = `${Math.max(0, Math.min(r.left-h.left, h.width-tip.offsetWidth))}px`;
            tip.style.top = `${Math.max(0,r.top-h.top-tip.offsetHeight-8)}px`;
        };
        const hide = () => host.querySelector(".chart-tip")?.remove();
        element.addEventListener("mouseenter", show); element.addEventListener("mouseleave", hide);
        element.addEventListener("focus", show); element.addEventListener("blur", hide);
        element.addEventListener("click", show);
    }
    function chart(id, dataset, {unit = "", bars = false} = {}) {
        const host = document.getElementById(id);
        if (!host) return;
        host.replaceChildren();
        const values = dataset.series.flatMap(s => s.values).filter(v => v !== null && Number.isFinite(v));
        if (!values.length) {
            const p = document.createElement("p"); p.className = "chart-empty"; p.textContent = "Data grafik belum tersedia."; host.append(p);
            table(host,dataset,unit); return;
        }
        const legend = document.createElement("div"); legend.className = "chart-legend";
        dataset.series.forEach((series, i) => {
            const label = document.createElement("span"), dot = document.createElement("i"); dot.className = "legend-dot"; dot.style.background = colors[i % colors.length];
            label.append(dot, document.createTextNode(series.name)); legend.append(label);
        });
        host.append(legend);
        const w = 640, h = bars ? Math.max(240, dataset.labels.length * 35 + 35) : 280;
        const pad = {left: bars ? 160 : 55, right: 20, top: 18, bottom: 35};
        const width = w-pad.left-pad.right, height = h-pad.top-pad.bottom;
        const svg = svgNode("svg", {viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": `${dataset.series.map(s=>s.name).join(", ")} — ${unit}. Angka lengkap tersedia di bawah grafik.`});
        svg.append(svgNode("title",{},`${dataset.series.map(s=>s.name).join(", ")} (${unit})`));
        host.append(svg);
        let low = Math.min(0,...values), high = Math.max(0,...values);
        if (high === low) high = low+1;
        const span = high-low;
        high += span*.10;
        if (low < 0) low -= span*.05;
        const x = i => pad.left+(dataset.labels.length === 1 ? width/2 : i*width/(dataset.labels.length-1));
        const y = v => pad.top+height-(v-low)/(high-low)*height;
        if (bars) {
            const min = Math.min(0,...values), max = Math.max(1,...values);
            const extent = (max-min)*1.15;
            const bx = value => pad.left+(value-min)/extent*width;
            svg.append(svgNode("line",{x1:bx(0),x2:bx(0),y1:pad.top,y2:h-pad.bottom,stroke:"#cbded3"}));
            dataset.labels.forEach((label,i) => {
                const v = dataset.series[0].values[i];
                const top = pad.top+i*height/dataset.labels.length;
                svg.append(svgNode("text",{x:pad.left-12,y:top+16,"text-anchor":"end"},label));
                if (v === null || !Number.isFinite(v)) return;
                const rect = svgNode("rect",{x:Math.min(bx(0),bx(v)),y:top+2,width:Math.abs(bx(v)-bx(0)),height:20,rx:4,fill:i%2 ? "#10b981":"#065f46",tabindex:0,class:"chart-point","aria-label":`${label}: ${format(v)} ${unit}`});
                rect.append(svgNode("title",{},`${label}: ${format(v)} ${unit}`)); svg.append(rect);
                svg.append(svgNode("text",{x:v<0?bx(v)-6:bx(v)+8,y:top+17,"text-anchor":v<0?"end":"start"},format(v)));
                tooltip(host,rect,`${label}: ${format(v)} ${unit}`);
            });
        } else {
            for (let t=0;t<=4;t++) {
                const value = low+(high-low)*t/4;
                svg.append(svgNode("line",{x1:pad.left,x2:w-pad.right,y1:y(value),y2:y(value),stroke:"#e5eee8","stroke-dasharray":"3 4"}));
                svg.append(svgNode("text",{x:pad.left-10,y:y(value)+4,"text-anchor":"end"},new Intl.NumberFormat("id-ID",{maximumFractionDigits:Math.abs(high)>1000?0:1}).format(value)));
            }
            dataset.labels.forEach((label,i) => svg.append(svgNode("text",{x:x(i),y:h-10,"text-anchor":"middle"},label)));
            dataset.series.forEach((series,si) => {
                const color = colors[si%colors.length]; let path = "", connected = false;
                series.values.forEach((value,i) => {
                    if (value === null || !Number.isFinite(value)) {connected=false;return;}
                    path += `${connected?"L":"M"}${x(i)},${y(value)} `;connected=true;
                });
                svg.append(svgNode("path",{d:path,fill:"none",stroke:color,"stroke-width":2.6,"stroke-linejoin":"round","stroke-linecap":"round",...(si===3?{"stroke-dasharray":"5 4"}:{})}));
                series.values.forEach((value,i) => {
                    if (value === null || !Number.isFinite(value)) return;
                    const desc = `${dataset.labels[i]} · ${series.name}: ${format(value)} ${unit}`;
                    const dot = svgNode("circle",{cx:x(i),cy:y(value),r:4.3,fill:color,stroke:"white","stroke-width":1.5,tabindex:0,class:"chart-point","aria-label":desc});
                    dot.append(svgNode("title",{},desc)); svg.append(dot); tooltip(host,dot,desc);
                });
            });
        }
        table(host,dataset,unit);
    }
    chart("premium-chart",data.monthly,{unit:"Rp triliun"});
    chart("finance-chart",data.finance,{unit:"Rp triliun"});
    chart("ratio-chart",data.ratio,{unit:"%"});
    chart("density-chart",data.density,{unit:"Rp/orang/tahun"});
    chart("macro-chart",data.macro,{unit:"%"});
    chart("companies-chart",data.companies,{unit:"unit",bars:true});
    chart("population-chart",data.population,{unit:"juta jiwa",bars:true});
    const explorerNode = document.getElementById("explorer-data");
    if (explorerNode) {
        const explorer = JSON.parse(explorerNode.textContent);
        const search = document.getElementById("indicator-search");
        const select = document.getElementById("indicator-select");
        const allYears = [...new Set(explorer.records.map(r=>Number(r.tahun)))].sort((a,b)=>a-b);
        function renderIndicator() {
            const entry = explorer.catalogue.find(r=>r.kode_indikator===select.value);
            if (!entry) {
                document.getElementById("indicator-title").textContent="Tidak ada indikator yang cocok";
                document.getElementById("indicator-source").textContent="";
                document.getElementById("indicator-unit").textContent="";
                document.getElementById("indicator-availability").textContent="Coba kata pencarian lain.";
                chart("indicator-chart",{labels:allYears,series:[]}); return;
            }
            const records = explorer.records.filter(r=>r.kode_indikator===entry.kode_indikator);
            const groups = [...new Set(records.map(r=>r.kode_industri))];
            const unit = entry.satuan || "Satuan tidak dicantumkan sumber";
            document.getElementById("indicator-title").textContent=entry.nama_indikator;
            document.getElementById("indicator-source").textContent=`BI ${entry.sumber_tabel} · ${entry.kode_indikator}`;
            document.getElementById("indicator-unit").textContent=unit;
            document.getElementById("indicator-availability").textContent=records.length ? `${records.length} observasi tersedia. Seluruh tahun ditampilkan; filter tahun ringkasan tidak membatasi grafik ini.` : "Indikator tercatat dalam katalog, tetapi belum memiliki nilai fakta untuk tahun yang dimuat. Tidak diisi dengan angka nol.";
            chart("indicator-chart",{labels:allYears.map(String),series:groups.map(group=>({name:records.find(r=>r.kode_industri===group).nama_industri || group,values:allYears.map(year=>{const r=records.find(r=>r.kode_industri===group && Number(r.tahun)===year); return r ? r.nilai : null;})}))},{unit});
        }
        function populateIndicators() {
            const old=select.value || "T6-022", term=search.value.toLocaleLowerCase("id-ID").trim();
            const words=term.split(/\s+/).filter(Boolean);
            select.replaceChildren();
            explorer.catalogue.filter(r=>words.every(word=>`${r.kode_indikator} ${r.nama_indikator} ${r.sumber_tabel} ${r.satuan || ""}`.toLocaleLowerCase("id-ID").includes(word))).forEach(r=>{
                const option=document.createElement("option");option.value=r.kode_indikator;
                option.textContent=`${r.kode_indikator} · ${r.nama_indikator} [${r.satuan || "tanpa satuan"}]${r.fact_count ? "" : " · belum ada nilai"}`;
                select.append(option);
            });
            if ([...select.options].some(o=>o.value===old))select.value=old;
            renderIndicator();
        }
        search.addEventListener("input",populateIndicators);
        select.addEventListener("change",renderIndicator);
        populateIndicators();
        const metric=document.getElementById("population-metric"), limit=document.getElementById("population-limit"), region=document.getElementById("population-region");
        explorer.metrics.forEach(m=>{const option=document.createElement("option");option.value=m.key;option.textContent=`${m.label} (${m.unit})`;metric.append(option);});
        const regions=[...new Set(explorer.population.map(r=>r.nama_provinsi))].sort((a,b)=>a==="Indonesia"?-1:b==="Indonesia"?1:a.localeCompare(b,"id"));
        regions.forEach(name=>{const option=document.createElement("option");option.value=name;option.textContent=name;region.append(option);});
        function renderPopulation() {
            const m=explorer.metrics.find(r=>r.key===metric.value);
            const rows=explorer.population.filter(r=>Number(r.tahun)===Number(explorer.year) && !r.is_nasional).sort((a,b)=>a[m.key]===null?1:b[m.key]===null?-1:b[m.key]-a[m.key]).slice(0,Number(limit.value));
            chart("demography-chart",{labels:rows.map(r=>r.nama_provinsi),series:[{name:m.label,values:rows.map(r=>r[m.key])}]},{unit:m.unit,bars:true});
            const regional=explorer.population.filter(r=>r.nama_provinsi===region.value);
            const years=[...new Set(explorer.population.map(r=>Number(r.tahun)))].sort((a,b)=>a-b);
            chart("region-chart",{labels:years.map(String),series:[{name:`${m.label} · ${region.value}`,values:years.map(year=>{const r=regional.find(row=>Number(row.tahun)===year);return r ? r[m.key] : null;})}]},{unit:m.unit});
        }
        metric.addEventListener("change",renderPopulation);limit.addEventListener("change",renderPopulation);region.addEventListener("change",renderPopulation);
        renderPopulation();
    }
    document.querySelectorAll("[data-mode]").forEach(button => button.addEventListener("click", () => {
        document.querySelectorAll("[data-mode]").forEach(item => { const active=item===button; item.classList.toggle("active",active); item.setAttribute("aria-pressed",String(active)); });
        chart("premium-chart",data[button.dataset.mode],{unit:"Rp triliun"});
        document.getElementById("premium-note").textContent = button.dataset.mode === "ytd" ? "Nilai kumulatif dari Januari sampai bulan terpilih. Nilai antarbulan tidak dijumlahkan." : "Nilai bulanan = selisih YTD antarbulan pada tahun yang sama. Januari = nilai YTD Januari.";
    }));
})();
