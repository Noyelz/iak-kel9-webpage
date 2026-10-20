(() => {
    const search = document.getElementById("warehouse-search");
    if (!search) return;
    const rows = [...document.querySelectorAll("#warehouse-table tbody tr")];
    const normalized = rows.map(row => row.textContent.toLocaleLowerCase("id-ID"));
    search.addEventListener("input", () => {
        const words = search.value.toLocaleLowerCase("id-ID").trim().split(/\s+/).filter(Boolean);
        let visible = 0;
        rows.forEach((row,i) => { row.hidden = !words.every(word => normalized[i].includes(word)); if (!row.hidden) visible++; });
        document.getElementById("warehouse-result").textContent = `${visible} dari ${rows.length} baris ditampilkan. Unduhan CSV tetap berisi seluruh tabel.`;
    });
})();
