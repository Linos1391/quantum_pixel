//cSpell:ignore fastapi
(function () {
    // switching tabs functioning.
    const headers = document.getElementById('tabs-headers');
    const panels = document.getElementById('tabs-panels');
    if (headers && panels) {
        headers.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab-btn');
            if (!btn) return;
            const target = btn.dataset.target;
            headers.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            panels.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
            btn.classList.add('active');
            const panel = document.getElementById(target);
            if (panel) panel.style.display = '';
        });
    }

    // Functions within the tabs section.
    const forms = document.getElementsByClassName('panel-controls');    
    Array.from(forms).forEach(function(form){
        form.addEventListener('submit', async (e) => {
            const fd = new FormData(form);
            const save_path = crypto.randomUUID() + ".png";
            const selected = document.querySelector('#tabs-headers .tab-btn.active').dataset.target;
            fd.append('save_path', save_path);
            fd.append('selected', selected);

            const result = document.querySelector(`#${selected} #result`)
            result.textContent = 'Loading, please wait patiently.';

            try {
                e.preventDefault();
                const r = await fetch(location.pathname, {
                    method: 'POST',
                    body: fd
                });
                const text = await r.text();
                result.innerHTML = text;
            } catch (err) {
                console.error(err);
            }
        });
    })

    // remove file when user left.
    window.addEventListener('beforeunload', async (e) => {
        e.preventDefault();
        await fetch(`/remove/${location.pathname.split("/").at(-1)}`, {
            method: 'POST',
            keepalive: true
        });
    });
})();
