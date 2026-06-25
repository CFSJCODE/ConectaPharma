const ENDPOINTS = Object.freeze([
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.osm.ch/api/interpreter',
]);

const byId = (id) => document.getElementById(id);

function html(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function norm(value) {
    return String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function setMessage(id, value, type = '') {
    const element = byId(id);
    if (!element) return;
    element.innerText = value;
    element.className = `message ${type}`.trim();
}

function setHtml(id, value) {
    const element = byId(id);
    if (element) element.innerHTML = value;
}

function locateUser() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocalização não é suportada neste navegador.'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => resolve({ lat: position.coords.latitude, lng: position.coords.longitude }),
            () => reject(new Error('Permissão de localização negada ou indisponível.')),
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
        );
    });
}

function rad(value) {
    return value * Math.PI / 180;
}

function distanceKm(a, b) {
    const radius = 6371;
    const dLat = rad(b.lat - a.lat);
    const dLng = rad(b.lng - a.lng);
    const lat1 = rad(a.lat);
    const lat2 = rad(b.lat);
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * radius * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function selector(type, filter, radius, lat, lng) {
    return `${type}${filter}(around:${radius},${lat},${lng});`;
}

function buildQuery(lat, lng, radiusKm) {
    const radius = Math.round(radiusKm * 1000);
    const operator = '(SUS|Prefeitura|Municipal|Estadual|Secretaria|Ministerio|Ministério|Governo)';
    const name = '(UBS|U B S|UPA|U P A|Posto de Saude|Posto de Saúde|Centro de Saude|Centro de Saúde|Unidade Basica|Unidade Básica|Unidade de Pronto Atendimento|Pronto Atendimento|Policlinica|Policlínica|Hospital Municipal|Hospital Estadual|Hospital Publico|Hospital Público|CAPS|Centro de Atencao Psicossocial|Centro de Atenção Psicossocial|SAMU)';
    const filters = [
        `["name"~"${name}",i]`,
        `["operator"~"${operator}",i]`,
        '["operator:type"="public"]',
        '["ownership"="public"]',
        '["healthcare"="centre"]',
        `["healthcare"="hospital"]["operator"~"${operator}",i]`,
        `["healthcare"="clinic"]["operator"~"${operator}",i]`,
        `["amenity"="hospital"]["operator"~"${operator}",i]`,
        `["amenity"="clinic"]["operator"~"${operator}",i]`,
        `["emergency"="yes"]["operator"~"${operator}",i]`,
    ];
    const body = filters.flatMap((filter) => [
        selector('node', filter, radius, lat, lng),
        selector('way', filter, radius, lat, lng),
        selector('relation', filter, radius, lat, lng),
    ]).join('');
    return `[out:json][timeout:45];(${body});out center tags 160;`;
}

async function overpass(queryText) {
    let lastError = null;

    for (const endpoint of ENDPOINTS) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), 36000);
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
                body: new URLSearchParams({ data: queryText }),
                signal: controller.signal,
            });
            window.clearTimeout(timer);
            if (!response.ok) throw new Error(`O serviço de mapas respondeu HTTP ${response.status}.`);
            return response.json();
        } catch (error) {
            window.clearTimeout(timer);
            const aborted = error?.name === 'AbortError' || String(error?.message || '').toLowerCase().includes('aborted');
            lastError = aborted ? new Error('A consulta aos mapas excedeu o tempo limite.') : error;
        }
    }

    throw lastError || new Error('O serviço de mapas está indisponível.');
}

function address(tags) {
    const street = tags['addr:street'] || tags['contact:street'] || tags['addr:place'];
    const number = tags['addr:housenumber'] || tags['contact:housenumber'];
    const suburb = tags['addr:suburb'] || tags['addr:neighbourhood'] || tags['addr:district'];
    const city = tags['addr:city'] || tags['addr:town'] || tags['addr:municipality'];
    return [street && number ? `${street}, ${number}` : street, suburb, city].filter(Boolean).join(' - ') || 'Endereço não informado';
}

function kind(tags) {
    const raw = norm(`${tags.name || ''} ${tags.healthcare || ''} ${tags.amenity || ''}`);
    if (raw.includes('upa') || raw.includes('pronto atendimento')) return 'UPA / Pronto atendimento';
    if (raw.includes('ubs') || raw.includes('unidade basica')) return 'UBS / Unidade básica';
    if (raw.includes('posto de saude')) return 'Posto de saúde';
    if (raw.includes('centro de saude') || tags.healthcare === 'centre') return 'Centro de saúde';
    if (raw.includes('hospital')) return 'Hospital público';
    if (raw.includes('caps') || raw.includes('psicossocial')) return 'CAPS / Saúde mental';
    if (raw.includes('policlinica')) return 'Policlínica';
    if (raw.includes('samu')) return 'SAMU';
    return 'Serviço de saúde pública';
}

function isPrivate(tags) {
    const raw = norm(`${tags.name || ''} ${tags.operator || ''} ${tags.description || ''}`);
    return raw.includes('particular') || raw.includes('privado') || raw.includes('privada') || raw.includes('unimed');
}

function toRecord(element, origin) {
    const tags = element.tags || {};
    if (isPrivate(tags)) return null;

    const center = element.center || {};
    const lat = Number(element.lat ?? center.lat);
    const lng = Number(element.lon ?? center.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

    const mapUrl = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`;
    return {
        id: `osm-${element.type}-${element.id}`,
        name: tags.name || 'Serviço de saúde localizado',
        kind: kind(tags),
        address: address(tags),
        phone: tags.phone || tags['contact:phone'] || null,
        website: tags.website || tags['contact:website'] || null,
        distance: Math.round(distanceKm(origin, { lat, lng }) * 100) / 100,
        openingHours: tags.opening_hours || 'Horário não informado',
        mapUrl,
    };
}

function render(items) {
    if (!items.length) {
        return '<p class="loading-text">Nenhum local de saúde pública foi encontrado no raio configurado. Amplie o raio ou verifique se os dados da sua região estão mapeados no OpenStreetMap.</p>';
    }

    return items.map((item) => {
        const links = [];
        if (item.phone) links.push(`<a href="tel:${html(item.phone)}">Telefone</a>`);
        if (item.website) links.push(`<a href="${html(item.website)}" target="_blank" rel="noopener">Site oficial</a>`);
        links.push(`<a href="${html(item.mapUrl)}" target="_blank" rel="noopener">Abrir no mapa</a>`);
        return `<div class="item-card"><div class="item-head"><div><strong>${html(item.name)}</strong><p>${html(item.kind)} · ${String(item.distance.toFixed(2)).replace('.', ',')} km</p><p>${html(item.address)}</p><p>${html(item.openingHours)}</p></div><span class="badge ok">Localizado</span></div><div class="item-actions">${links.join(' · ')}</div></div>`;
    }).join('');
}

async function loadNearbyHealth() {
    const button = byId('btn-nearby-health');
    const radiusInput = byId('health-radius');
    if (!button || !radiusInput) return;

    button.disabled = true;
    setMessage('health-status', 'Obtendo sua localização autorizada...');
    setHtml('health-list', '<p class="loading-text">Consultando rede pública de saúde próxima...</p>');

    try {
        const origin = await locateUser();
        const radiusKm = Number(radiusInput.value || 5);
        setMessage('health-status', 'Consultando UBSs, UPAs, postos, centros de saúde e outros locais públicos...');
        const payload = await overpass(buildQuery(origin.lat, origin.lng, radiusKm));
        const seen = new Set();
        const items = (payload.elements || [])
            .map((element) => toRecord(element, origin))
            .filter(Boolean)
            .filter((item) => {
                if (seen.has(item.id)) return false;
                seen.add(item.id);
                return true;
            })
            .sort((a, b) => a.distance - b.distance)
            .slice(0, 40);

        setMessage('health-status', `${items.length} local(is) de saúde pública localizado(s).`, items.length ? 'success' : 'warn');
        setHtml('health-list', render(items));
    } catch (error) {
        const message = String(error?.message || 'Não foi possível consultar locais próximos.');
        setMessage('health-status', message.toLowerCase().includes('tempo limite') ? 'A consulta demorou demais. Tente novamente em alguns segundos ou reduza o raio.' : message, 'error');
        setHtml('health-list', '<p class="loading-text">A busca depende dos servidores públicos do OpenStreetMap/Overpass. Tente novamente, reduza o raio ou verifique a permissão de localização.</p>');
    } finally {
        button.disabled = false;
    }
}

function installPatch() {
    const button = byId('btn-nearby-health');
    if (!button || button.dataset.healthLookupPatch === 'true') return;

    button.dataset.healthLookupPatch = 'true';
    button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        loadNearbyHealth();
    }, { capture: true });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installPatch, { once: true });
} else {
    installPatch();
}
