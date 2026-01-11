(async function () {
    // get the image filename from the current path, e.g. /decode/<filename>
    const save_path = crypto.randomUUID() + ".png";
    try {
        preventDefault()
        const r = await fetch(location.pathname, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ save_path })
        });
        const text = await r.text();
        document.documentElement.innerHTML = text
    } catch (err) {
        console.error(err);
    }

    // remove file when user left.
    window.addEventListener('beforeunload', async (e) => {
        e.preventDefault();
        await fetch(`/remove/${location.pathname.split("/").at(-1)}`, {
            method: 'POST',
            keepalive: true
        });
    });
})();