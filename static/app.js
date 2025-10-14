// static/app.js (SON GÜNCELLEME - SEKMESİZ, TEK BLOK ÇIKTI)

// --- GENEL UI VE ANALİZ MANTIĞI ---
const productSelect = document.getElementById('productSelect'); 
const analyzeBtn = document.getElementById('analyzeBtn');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const results = document.getElementById('results');
// Analiz çıktısını gösterecek tek bir alan seçeceğiz (mevcut HTML'de content-individual'ı kullanabiliriz)
const analysisOutputPanel = document.getElementById('content-individual');


// --- ÜRÜN LİSTESİNİ DOLDURMA FONKSİYONU ---
async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const data = await response.json();
        
        if (data.success) {
            data.products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.key; 
                option.textContent = `[${product.category.toUpperCase()}] ${product.name}`;
                productSelect.appendChild(option);
            });
        } else {
            showError(`Ürün listesi yüklenirken hata: ${data.error}`);
        }
    } catch (err) {
        showError('Sunucuya bağlanılamadı veya ürün listesi çekilemedi.');
    }
}

// Sayfa yüklendiğinde ürün listesini çek
loadProducts();


// Ana Tabları Yönetme (Analyze/Chatbot) - AYNI KALIR
document.querySelectorAll('.main-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const targetTab = tab.dataset.mainTab;

        document.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        document.querySelectorAll('.main-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`main-${targetTab}`).classList.add('active');
    });
});

// Alt Tabları Yönetme (Individual/Economic/Governmental) - İPTAL EDİLDİ
// Bu kısım (alt tab yönetimi) artık gereksiz, düğmeler HTML'den kaldırılmalıdır.

// Analiz butonu
analyzeBtn.addEventListener('click', async () => {
    const productKey = productSelect.value;
    
    if (!productKey) {
        showError('Lütfen analiz etmek için listeden bir ürün seçin.');
        return;
    }

    loading.classList.remove('hidden');
    error.classList.add('hidden');
    results.classList.add('hidden');

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_key: productKey }) 
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Analiz başarısız oldu.');
        }

        displayResults(data.analysis);

    } catch (err) {
        showError(err.message);
    } finally {
        loading.classList.add('hidden');
    }
});


function displayResults(analysis) {
    // 1. Analiz çıktısını AI'ın kullandığı başlıklar (Emoji/Markdown) üzerinden bölümlere ayır.
    const sections = parseAnalysis(analysis); 
    
    // AI'ın prompt'ta kullandığı kesin başlıkları yeniden tanımla
    const individualHeader = '**👤 Bireysel Perspektif:**';
    const economicHeader = '**💰 Ekonomik Perspektif:**';
    const governmentalHeader = '**🏛️ Devlet/Politika Perspektifi:**';
    
    // 2. Ana başlığı al. (AI çıktısının ilk satırı)
    const lines = analysis.split('\n');
    const mainTitleLine = lines.find(line => line.startsWith('# Xiaomi'));
    const mainTitle = mainTitleLine ? `<h1>${mainTitleLine.replace('# ', '').trim()}</h1>` : '';

    // 3. Tüm bölümleri tek bir string'de birleştir.
    let combinedOutput = mainTitle;
    
    // Bireysel kısım
    if (sections.individual && sections.individual !== 'Analiz verisi bulunamadı.') {
        combinedOutput += formatMarkdown(individualHeader + '\n' + sections.individual);
        combinedOutput += '<br><br>'; 
    }

    // Ekonomik kısım
    if (sections.economic && sections.economic !== 'Analiz verisi bulunamadı.') {
        combinedOutput += formatMarkdown(economicHeader + '\n' + sections.economic);
        combinedOutput += '<br><br>';
    }

    // Devlet kısmı
    if (sections.governmental && sections.governmental !== 'Analiz verisi bulunamadı.') {
        combinedOutput += formatMarkdown(governmentalHeader + '\n' + sections.governmental);
        combinedOutput += '<br><br>';
    }
    
    // 4. Çıktıyı tek bir alana yaz.
    // HTML/CSS'i basitleştirmeniz önerilir, ancak JS tarafında mevcut content-individual panelini kullanıyoruz.
    
    // Tüm tab panellerini inaktif yap ve sadece bir tanesine (content-individual) içeriği yükle
    document.querySelectorAll('.content-panel').forEach(p => p.classList.remove('active'));
    analysisOutputPanel.innerHTML = combinedOutput;
    analysisOutputPanel.classList.add('active'); // Görüntülenmesini sağla

    results.classList.remove('hidden');
}

function formatMarkdown(text) {
    // Basit Markdown (**, *) ve yeni satırları (<br>) HTML'e dönüştürür.
    if (!text) return 'Analiz verisi bulunamadı.';
    
    // Markdown listeleri için düzeltme (* madde -> <li>madde</li>)
    let html = text.split('\n').map(line => {
        if (line.trim().startsWith('* ')) {
            return `<li>${line.trim().substring(2).trim()}</li>`;
        }
        return line;
    }).join('\n');
    
    // <li> elemanlarını <ul> içine sarar
    if (html.includes('<li>')) {
        // Ardışık <li>'leri tek bir <ul> bloğuna toplar
        html = html.replace(/(\n?<li>.*?<\/li>(\n?))+/gs, match => `<ul>\n${match.trim()}\n</ul>\n`);
    }
    
    // Diğer Markdown formatları ve yeni satırlar
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic/Vurgu
    html = html.replace(/\n/g, '<br>'); // Yeni satırlar
    
    // Listelerden kalan gereksiz <br> ve \n karakterlerini temizle
    html = html.replace(/<\/li><br>/g, '</li>');
    html = html.replace(/<br><ul>/g, '<ul>');
    html = html.replace(/<\/ul><br>/g, '</ul>');
    
    return html;
}

// AI'ın kullandığı EMOJI/HEADER'lara göre içerik ayrıştırma (PARSING)
function parseAnalysis(text) {
    const sections = {
        individual: '', 
        economic: '',
        governmental: ''
    };
    
    const lines = text.split('\n');
    let currentSection = null;

    for (const line of lines) {
        const lower = line.toLowerCase().trim();
        
        // Ana başlıkları, ayırıcıları ve boş satırları atla
        if (line.startsWith('# Xiaomi') || line.startsWith('---') || lower === '') {
            continue;
        }
        
        // Header'ları yakala (AI'ın kullandığı EMOJI/HEADER'lara göre)
        // Burada başlık satırını atlıyoruz (continue), sadece içeriği alıyoruz.
        if (lower.includes('👤 bireysel perspektif')) {
            currentSection = 'individual';
            continue; 
        } else if (lower.includes('💰 ekonomik perspektif')) {
            currentSection = 'economic';
            continue; 
        } else if (lower.includes('🏛️ devlet/politika perspektifi') || lower.includes('🏛️ devlet perspektifi')) {
            currentSection = 'governmental';
            continue; 
        }
        
        // Mevcut bölüme satırı ekle
        if (currentSection) {
            sections[currentSection] += line + '\n';
        }
    }
    
    // Final trimming ve "Analiz bulunamadı" kontrolü
    for (let key in sections) {
        sections[key] = sections[key].trim();
        if (sections[key] === '') {
            sections[key] = 'Analiz verisi bulunamadı.';
        }
    }

    return sections;
}


function showError(message) {
    error.textContent = message;
    error.classList.remove('hidden');
}


// --- CHATBOT MANTIĞI (Aynı kalır) ---

const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const chatMessages = document.getElementById('chatMessages');

chatSendBtn.addEventListener('click', sendChatQuery);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatQuery();
});

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `${sender}-message`;
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight; // En alta kaydır
}

function addLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'bot-message loading-indicator';
    loadingDiv.textContent = 'Yapay Zeka düşünüyor...';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return loadingDiv;
}

async function sendChatQuery() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Kullanıcı mesajını ekle ve input'u temizle
    addMessage(query, 'user');
    chatInput.value = '';

    const loadingIndicator = addLoadingIndicator();

    try {
        const response = await fetch('/api/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        // Yükleniyor indicator'ını kaldır
        chatMessages.removeChild(loadingIndicator);

        if (data.success) {
            addMessage(data.response, 'bot');
        } else {
            addMessage(`Hata: ${data.error}`, 'bot');
        }

    } catch (err) {
        chatMessages.removeChild(loadingIndicator);
        addMessage(`Sunucuya bağlanılamadı: ${err.message}`, 'bot');
    }
}