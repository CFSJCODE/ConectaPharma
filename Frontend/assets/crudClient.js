import {
    deleteDoc,
    doc,
    serverTimestamp,
    updateDoc,
} from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-firestore.js';
import {
    auth,
    db,
    assertPlatformAdminUser,
} from './firebaseClient.js';

function requireAuthenticatedUser() {
    const user = auth.currentUser;
    if (!user?.uid) {
        const error = new Error('Faça login para executar esta operação.');
        error.code = 'permission-denied';
        throw error;
    }
    return user;
}

function asNullableText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function parseNumber(value, fallback = 0) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeWhatsapp(value) {
    return String(value || '').replace(/\D+/g, '') || null;
}

function buildOpenStreetMapUrl(latitude, longitude) {
    const lat = Number(latitude);
    const lng = Number(longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`;
}

export async function updateMedication(documentId, data) {
    const user = requireAuthenticatedUser();
    const id = String(documentId || '').trim();

    if (!id) throw new Error('Identificador do medicamento não informado.');

    const nome = String(data?.nome ?? '').trim();
    if (!nome) throw new Error('O nome do medicamento é obrigatório.');

    const payload = {
        nome,
        categoria: asNullableText(data?.categoria),
        descricao: asNullableText(data?.descricao),
        dose_diaria_comprimidos: parseNumber(data?.dose_diaria_comprimidos, 1),
        stock: parseNumber(data?.stock, 0),
        requires_prescription: Boolean(data?.requires_prescription),
        active: data?.active !== false,
        updatedBy: user.uid,
        updatedAt: serverTimestamp(),
    };

    await updateDoc(doc(db, 'medications', id), payload);
    return { id, ...payload };
}

export async function deleteMedication(documentId) {
    requireAuthenticatedUser();
    const id = String(documentId || '').trim();

    if (!id) throw new Error('Identificador do medicamento não informado.');

    await deleteDoc(doc(db, 'medications', id));
    return { id };
}

export async function updateFarmacia(documentId, data) {
    assertPlatformAdminUser();
    const id = String(documentId || '').trim();

    if (!id) throw new Error('Identificador da farmácia não informado.');

    const nome = String(data?.nome ?? '').trim();
    const endereco = String(data?.endereco ?? '').trim();

    if (!nome || !endereco) {
        throw new Error('Nome e endereço da farmácia são obrigatórios.');
    }

    const latitude = Number(data?.latitude);
    const longitude = Number(data?.longitude);
    const hasValidCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude);
    const openstreetmapUrl = hasValidCoordinates ? buildOpenStreetMapUrl(latitude, longitude) : null;
    const horario = asNullableText(data?.horario_funcionamento) || 'Horário não informado';

    const payload = {
        nome,
        name: nome,
        endereco,
        address: endereco,
        bairro: asNullableText(data?.bairro),
        cidade: asNullableText(data?.cidade) || 'Belo Horizonte',
        estado: asNullableText(data?.estado) || 'MG',
        cep: asNullableText(data?.cep),
        telefone: asNullableText(data?.telefone),
        phone: asNullableText(data?.telefone),
        whatsapp: normalizeWhatsapp(data?.whatsapp),
        email: asNullableText(data?.email),
        website: asNullableText(data?.website),
        horario_funcionamento: horario,
        opening_hours_label: horario,
        latitude: hasValidCoordinates ? latitude : null,
        longitude: hasValidCoordinates ? longitude : null,
        openstreetmap_url: openstreetmapUrl,
        maps_url: openstreetmapUrl,
        observacoes: asNullableText(data?.observacoes),
        ativo: data?.ativo !== false,
        disponibilidade_farmaco: data?.disponibilidade_farmaco !== false,
        updatedAt: serverTimestamp(),
    };

    await updateDoc(doc(db, 'farmacias', id), payload);
    return { id, ...payload };
}

export async function deleteFarmacia(documentId) {
    assertPlatformAdminUser();
    const id = String(documentId || '').trim();

    if (!id) throw new Error('Identificador da farmácia não informado.');

    await deleteDoc(doc(db, 'farmacias', id));
    return { id };
}
