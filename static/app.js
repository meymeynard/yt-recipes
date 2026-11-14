function toggleSidebar(forceOpen) {
    const sb = document.getElementById('sidebar-panel');
    const bd = document.getElementById('sidebar-backdrop');
    if (!sb || !bd) return;
    const isOpen = typeof forceOpen === 'boolean' ? forceOpen : !sb.classList.contains('open');
    sb.classList.toggle('open', isOpen);
    bd.classList.toggle('open', isOpen);
}

function filterPantryIngredients(query) {
    const q = (query || '').toLowerCase().trim();
    const accordions = document.querySelectorAll('#sidebar-categories details.accordion');
    accordions.forEach(acc => {
        let visibleCount = 0;
        const pills = acc.querySelectorAll('.ing-pill');
        pills.forEach(pill => {
            const text = pill.textContent.toLowerCase();
            const match = !q || text.includes(q);
            pill.style.display = match ? 'inline-flex' : 'none';
            if (match) visibleCount++;
        });
        acc.style.display = visibleCount > 0 ? 'block' : 'none';
        if (q && visibleCount > 0) acc.open = true;
    });
}
