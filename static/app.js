'use strict';
const select = document.getElementById('productSelect');
const analyze = document.getElementById('analyzeBtn');
const error = document.getElementById('error');
const loading = document.getElementById('loading');
const output = document.getElementById('content-individual');
const results = document.getElementById('results');
const input = document.getElementById('chatInput');
const send = document.getElementById('chatSendBtn');
const messages = document.getElementById('chatMessages');
let chatBusy = false;

async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 70000);
    try {
        const response = await fetch(path, {signal: controller.signal,
            ...(body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})});
        if (response.status === 401) throw new Error('Oturum sona erdi. Giriş sayfasından yeniden oturum açın.');
        const data = await response.json();
        if (!response.ok || data.success === false) throw new Error(data.error || 'İstek tamamlanamadı.');
        return data;
    } catch (err) {
        if (err.name === 'AbortError') throw new Error('Yanıt zaman aşımına uğradı. Yeniden deneyin.');
        throw err;
    } finally { clearTimeout(timeout); }
}

function showError(message) { error.textContent = message; error.classList.remove('hidden'); }
function message(text, sender) {
    const element = document.createElement('div');
    element.className = `${sender}-message`;
    element.textContent = text;
    messages.appendChild(element);
    messages.scrollTop = messages.scrollHeight;
    return element;
}

async function load() {
    analyze.disabled = true;
    try {
        const health = await api('/api/health');
        document.getElementById('serviceStatus').textContent = health.mode === 'local_sources'
            ? 'Yerel kaynak modu · API anahtarı gerekmez · Model çağrısı yapılmaz'
            : 'Model destekli mod · Yanıtlar harici servisten gelir';
        const data = await api('/api/products');
        for (const product of data.products) {
            const option = document.createElement('option');
            option.value = product.key;
            option.textContent = `[${product.category}] ${product.name}`;
            select.appendChild(option);
        }
        if (!data.products.length) throw new Error('Katalog boş. Veri dosyalarını kontrol edin.');
    } catch (err) { showError(err.message); }
}
select.addEventListener('change', () => { analyze.disabled = !select.value; });
document.getElementById('retryBtn').addEventListener('click', () => {
    select.length = 1;
    error.classList.add('hidden');
    load();
});

for (const tab of document.querySelectorAll('.main-tab')) {
    tab.addEventListener('click', () => {
        for (const item of document.querySelectorAll('.main-tab')) {
            item.classList.toggle('active', item === tab);
            item.setAttribute('aria-selected', String(item === tab));
        }
        for (const panel of document.querySelectorAll('.main-content')) panel.classList.remove('active');
        document.getElementById(`main-${tab.dataset.mainTab}`).classList.add('active');
    });
}

analyze.addEventListener('click', async () => {
    if (!select.value || analyze.disabled) return;
    analyze.disabled = true;
    loading.classList.remove('hidden');
    error.classList.add('hidden');
    results.classList.add('hidden');
    try {
        const data = await api('/api/analyze', {product_key: select.value});
        output.textContent = data.analysis;
        results.classList.remove('hidden');
    } catch (err) { showError(err.message); }
    finally { loading.classList.add('hidden'); analyze.disabled = !select.value; }
});

async function ask() {
    const query = input.value.trim();
    if (!query || chatBusy) return;
    chatBusy = true;
    send.disabled = true;
    message(query, 'user');
    input.value = '';
    const pending = message('Kaynaklar aranıyor…', 'bot');
    try {
        const data = await api('/api/chatbot', {query});
        pending.textContent = data.response;
    } catch (err) { pending.textContent = err.message; }
    finally { chatBusy = false; send.disabled = false; input.focus(); }
}
send.addEventListener('click', ask);
input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); ask(); }
});
load();
