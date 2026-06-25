"use strict";

const OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
];

const DEFAULT_RADIUS_METERS = 5000;
const EARTH_RADIUS_KM = 6371;

export const HEALTH_UNIT_TYPES = Object.freeze({
    ALL: "Todos os tipos",
    UBS: "Unidade Básica de Saúde",
    POSTO: "Posto de Saúde",
    CENTRO: "Centro de Saúde",
    UPA: "Unidade de Pronto Atendimento",
    HOSPITAL: "Hospital",
    CLINICA: "Clínica / Unidade Ambulatorial",
    OUTRO: "Estabelecimento de Saúde"
});

export function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (!("geolocation" in navigator)) {
            reject(new Error("Geolocalização não suportada neste navegador."));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                });
            },
            (error) => reject(new Error(resolveGeolocationError(error))),
            {
                enableHighAccuracy: true,
                timeout: 12000,
                maximumAge: 60000
            }
        );
    });
}

export async function fetchNearbyHealthUnits(latitude, longitude, radiusMeters = DEFAULT_RADIUS_METERS) {
    const query = buildHealthUnitsOverpassQuery(latitude, longitude, radiusMeters);
    const payload = await requestOverpass(query);

    return normalizeOverpassElements(payload.elements || [], {
        latitude,
        longitude
    });
}

export function buildRouteUrl(latitude, longitude, provider = "osm") {
    if (provider === "google") {
        return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`;
    }

    return `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}`;
}

function resolveGeolocationError(error) {
    switch (error.code) {
        case error.PERMISSION_DENIED:
            return "Permissão de localização negada. Autorize a localização no navegador para buscar unidades próximas.";
        case error.POSITION_UNAVAILABLE:
            return "Localização indisponível no momento. Verifique GPS, Wi-Fi ou permissões do navegador.";
        case error.TIMEOUT:
            return "Tempo limite excedido ao obter localização. Tente novamente ou reduza bloqueios de privacidade.";
        default:
            return "Erro desconhecido ao obter localização.";
    }
}

function buildHealthUnitsOverpassQuery(latitude, longitude, radiusMeters) {
    const radius = Math.max(1000, Math.min(Number(radiusMeters) || DEFAULT_RADIUS_METERS, 20000));
    const nameRegex = "UBS|UPA|Unidade Básica|Unidade Basica|Centro de Saúde|Centro de Saude|Posto de Saúde|Posto de Saude|PSF|Estratégia Saúde da Família|Estrategia Saude da Familia";

    return `
        [out:json][timeout:25];
        (
            node["name"~"${nameRegex}", i](around:${radius},${latitude},${longitude});
            way["name"~"${nameRegex}", i](around:${radius},${latitude},${longitude});
            relation["name"~"${nameRegex}", i](around:${radius},${latitude},${longitude});

            node["amenity"~"clinic|hospital|doctors"](around:${radius},${latitude},${longitude});
            way["amenity"~"clinic|hospital|doctors"](around:${radius},${latitude},${longitude});
            relation["amenity"~"clinic|hospital|doctors"](around:${radius},${latitude},${longitude});

            node["healthcare"~"clinic|hospital|doctor|centre"](around:${radius},${latitude},${longitude});
            way["healthcare"~"clinic|hospital|doctor|centre"](around:${radius},${latitude},${longitude});
            relation["healthcare"~"clinic|hospital|doctor|centre"](around:${radius},${latitude},${longitude});
        );
        out center tags;
    `;
}

async function requestOverpass(queryText) {
    let lastError = null;

    for (const endpoint of OVERPASS_ENDPOINTS) {
        const controller = new AbortController();
        const timer = window.setTimeout(() => controller.abort(), 16000);

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
                },
                body: new URLSearchParams({ data: queryText }),
                signal: controller.signal
            });

            window.clearTimeout(timer);

            if (!response.ok) {
                throw new Error(`Serviço de localização respondeu HTTP ${response.status}.`);
            }

            return response.json();
        } catch (error) {
            window.clearTimeout(timer);
            lastError = error;
        }
    }

    throw lastError || new Error("Serviço de localização indisponível no momento.");
}

function normalizeOverpassElements(elements, userPosition) {
    const uniqueMap = new Map();

    for (const element of elements) {
        const unit = toHealthUnitDto(element, userPosition);

        if (!unit) {
            continue;
        }

        const key = `${unit.name.toLowerCase()}|${unit.latitude.toFixed(5)}|${unit.longitude.toFixed(5)}`;
        if (!uniqueMap.has(key)) {
            uniqueMap.set(key, unit);
        }
    }

    return Array.from(uniqueMap.values())
        .sort((a, b) => a.distanceKm - b.distanceKm);
}

function toHealthUnitDto(element, userPosition) {
    const tags = element.tags || {};
    const center = element.center || {};
    const latitude = Number(element.lat ?? center.lat);
    const longitude = Number(element.lon ?? center.lon);

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        return null;
    }

    const name = tags.name || "Unidade de saúde sem nome informado";
    const type = classifyHealthUnit(name, tags);
    const distanceKm = calculateDistanceKm(
        userPosition.latitude,
        userPosition.longitude,
        latitude,
        longitude
    );

    return {
        id: `${element.type}-${element.id}`,
        osmId: element.id,
        name,
        type,
        typeLabel: HEALTH_UNIT_TYPES[type] || HEALTH_UNIT_TYPES.OUTRO,
        latitude,
        longitude,
        distanceKm: Math.round(distanceKm * 100) / 100,
        address: buildAddress(tags),
        phone: tags.phone || tags["contact:phone"] || null,
        website: tags.website || tags["contact:website"] || null,
        openingHours: tags.opening_hours || null,
        source: "OpenStreetMap"
    };
}

function classifyHealthUnit(name = "", tags = {}) {
    const normalizedName = normalizeText(name);

    if (normalizedName.includes("UPA") || normalizedName.includes("PRONTO ATENDIMENTO")) {
        return "UPA";
    }

    if (normalizedName.includes("UBS") || normalizedName.includes("UNIDADE BASICA")) {
        return "UBS";
    }

    if (normalizedName.includes("POSTO DE SAUDE") || normalizedName.includes("PSF")) {
        return "POSTO";
    }

    if (normalizedName.includes("CENTRO DE SAUDE") || normalizedName.includes("CENTRO SAUDE")) {
        return "CENTRO";
    }

    if (tags.amenity === "hospital" || tags.healthcare === "hospital") {
        return "HOSPITAL";
    }

    if (tags.amenity === "clinic" || tags.healthcare === "clinic" || tags.healthcare === "centre") {
        return "CLINICA";
    }

    return "OUTRO";
}

function normalizeText(value) {
    return String(value)
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toUpperCase();
}

function buildAddress(tags) {
    const street = tags["addr:street"] || tags["contact:street"] || tags["addr:place"];
    const houseNumber = tags["addr:housenumber"] || tags["contact:housenumber"];
    const suburb = tags["addr:suburb"] || tags["addr:neighbourhood"] || tags["addr:district"];
    const city = tags["addr:city"] || tags["addr:town"] || tags["addr:municipality"];

    return [street && houseNumber ? `${street}, ${houseNumber}` : street, suburb, city]
        .filter(Boolean)
        .join(" - ") || "Endereço não informado";
}

function calculateDistanceKm(lat1, lon1, lat2, lon2) {
    const dLat = degreesToRadians(lat2 - lat1);
    const dLon = degreesToRadians(lon2 - lon1);
    const originLat = degreesToRadians(lat1);
    const targetLat = degreesToRadians(lat2);

    const haversine =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(originLat) * Math.cos(targetLat) * Math.sin(dLon / 2) ** 2;

    return 2 * EARTH_RADIUS_KM * Math.atan2(
        Math.sqrt(haversine),
        Math.sqrt(1 - haversine)
    );
}

function degreesToRadians(degrees) {
    return degrees * (Math.PI / 180);
}
