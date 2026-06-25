"use strict";

import {
    HEALTH_UNIT_TYPES,
    buildRouteUrl,
    fetchNearbyHealthUnits,
    getUserLocation
} from "./health-units-service.js";

let healthMap = null;
let userMarker = null;
let unitMarkers = [];
let cachedUnits = [];

const elements = {
    button: document.getElementById("btnFindHealthUnits"),
    radius: document.getElementById("healthUnitRadius"),
    filter: document.getElementById("healthUnitFilter"),
    status: document.getElementById("healthUnitsStatus"),
    list: document.getElementById("healthUnitsList"),
    resultCount: document.getElementById("healthUnitsResultCount"),
    map: document.getElementById("healthMap")
};

elements.button?.addEventListener("click", handleFindHealthUnits);
elements.filter?.addEventListener("change", renderFilteredUnits);

renderTypeOptions();

async function handleFindHealthUnits() {
    try {
        setStatus("Obtendo sua localização autorizada...", "loading");
        setResultCount("—");
        elements.button.disabled = true;

        const userPosition = await getUserLocation();
        const radiusMeters = Number(elements.radius?.value || 5000);

        initializeMap(userPosition.latitude, userPosition.longitude);
        renderUserMarker(userPosition);

        setStatus("Consultando UBSs, postos, centros de saúde e UPAs próximos...", "loading");

        cachedUnits = await fetchNearbyHealthUnits(
            userPosition.latitude,
            userPosition.longitude,
            radiusMeters
        );

        setResultCount(cachedUnits.length);
        renderFilteredUnits();

        if (cachedUnits.length === 0) {
            setStatus("Nenhuma unidade de saúde foi localizada no raio configurado. Amplie o raio e tente novamente.", "warn");
            return;
        }

        setStatus(`${cachedUnits.length} unidade(s) localizada(s), ordenadas por proximidade.`, "success");
    } catch (error) {
        console.error(error);
        clearUnitMarkers();
        setResultCount("0");
        renderEmptyState(error?.message || "Não foi possível localizar unidades próximas.");
        setStatus(error?.message || "Não foi possível localizar unidades próximas.", "error");
    } finally {
        elements.button.disabled = false;
    }
}

function renderTypeOptions() {
    if (!elements.filter) {
        return;
    }

    elements.filter.innerHTML = Object.entries(HEALTH_UNIT_TYPES)
        .map(([value, label]) => `<option value="${value}">${label}</option>`)
        .join("");
}

function initializeMap(latitude, longitude) {
    if (!elements.map || !("L" in window)) {
        return;
    }

    if (healthMap) {
        healthMap.setView([latitude, longitude], 14);
        return;
    }

    healthMap = L.map("healthMap", {
        scrollWheelZoom: false
    }).setView([latitude, longitude], 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(healthMap);
}

function renderUserMarker(position) {
    if (!healthMap) {
        return;
    }

    const coordinates = [position.latitude, position.longitude];

    if (userMarker) {
        userMarker.setLatLng(coordinates);
        return;
    }

    userMarker = L.marker(coordinates)
        .addTo(healthMap)
        .bindPopup("Sua localização aproximada")
        .openPopup();
}

function renderFilteredUnits() {
    const selectedType = elements.filter?.value || "ALL";
    const units = selectedType === "ALL"
        ? cachedUnits
        : cachedUnits.filter((unit) => unit.type === selectedType);

    renderUnitMarkers(units);
    renderUnitsList(units);
}

function renderUnitMarkers(units) {
    clearUnitMarkers();

    if (!healthMap) {
        return;
    }

    for (const unit of units) {
        const marker = L.marker([unit.latitude, unit.longitude])
            .addTo(healthMap)
            .bindPopup(`
                <strong>${escapeHtml(unit.name)}</strong><br>
                ${escapeHtml(unit.typeLabel)}<br>
                ${formatDistance(unit.distanceKm)}<br>
                <a href="${buildRouteUrl(unit.latitude, unit.longitude)}" target="_blank" rel="noopener">Abrir rota</a>
            `);

        unitMarkers.push(marker);
    }
}

function clearUnitMarkers() {
    for (const marker of unitMarkers) {
        marker.remove();
    }

    unitMarkers = [];
}

function renderUnitsList(units) {
    if (!elements.list) {
        return;
    }

    if (!Array.isArray(units) || units.length === 0) {
        renderEmptyState("Nenhuma unidade encontrada para o filtro selecionado.");
        return;
    }

    elements.list.innerHTML = units
        .slice(0, 30)
        .map((unit) => renderUnitCard(unit))
        .join("");
}

function renderUnitCard(unit) {
    const phone = unit.phone
        ? `<a href="tel:${escapeHtml(unit.phone)}">Telefone</a>`
        : `<span>Telefone não informado</span>`;

    const website = unit.website
        ? `<a href="${escapeHtml(unit.website)}" target="_blank" rel="noopener">Site</a>`
        : "";

    return `
        <article class="health-unit-card">
            <div class="health-unit-card-header">
                <span class="health-unit-type">${escapeHtml(unit.typeLabel)}</span>
                <strong>${formatDistance(unit.distanceKm)}</strong>
            </div>
            <h3>${escapeHtml(unit.name)}</h3>
            <p>${escapeHtml(unit.address)}</p>
            <p><strong>Horário:</strong> ${escapeHtml(unit.openingHours || "não informado")}</p>
            <div class="health-unit-actions">
                <a class="btn btn-secondary" href="${buildRouteUrl(unit.latitude, unit.longitude)}" target="_blank" rel="noopener">Abrir no mapa</a>
                <a class="btn btn-secondary" href="${buildRouteUrl(unit.latitude, unit.longitude, "google")}" target="_blank" rel="noopener">Rota Google Maps</a>
                ${phone}
                ${website}
            </div>
            <small>Fonte: ${escapeHtml(unit.source)}. Dados sujeitos à atualização pela comunidade e bases abertas.</small>
        </article>
    `;
}

function renderEmptyState(message) {
    if (!elements.list) {
        return;
    }

    elements.list.innerHTML = `
        <div class="empty-state">
            ${escapeHtml(message)}
        </div>
    `;
}

function setStatus(message, type = "info") {
    if (!elements.status) {
        return;
    }

    elements.status.textContent = message;
    elements.status.dataset.status = type;
}

function setResultCount(value) {
    if (elements.resultCount) {
        elements.resultCount.textContent = String(value);
    }
}

function formatDistance(distanceKm) {
    return `${distanceKm.toFixed(2).replace(".", ",")} km`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
