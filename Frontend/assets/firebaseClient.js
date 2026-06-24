import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-app.js';
import {
    getAuth,
    GoogleAuthProvider,
    browserSessionPersistence,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signInWithPopup,
    signOut,
    onAuthStateChanged,
    setPersistence,
    updateProfile,
} from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js';
import {
    getFirestore,
    doc,
    getDoc,
    setDoc,
    addDoc,
    collection,
    getDocs,
    query,
    where,
    orderBy,
    limit as limitQuery,
    serverTimestamp,
} from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-firestore.js';

// Configuração pública do app Web registrada no Firebase Console.
// Essa configuração identifica o app; não é chave secreta. Regras do Firestore
// e Firebase Authentication continuam sendo a camada real de segurança.
export const firebaseConfig = Object.freeze({
    apiKey: 'AIzaSyCN4we2-58ZJXy0TCxVpcdTzo5dvlDrCXw',
    authDomain: 'conectapharma-33fd7.firebaseapp.com',
    projectId: 'conectapharma-33fd7',
    storageBucket: 'conectapharma-33fd7.firebasestorage.app',
    messagingSenderId: '137881875886',
    appId: '1:137881875886:web:499dc824977b90cebe443f',
    measurementId: 'G-QEJ27VVTM7',
});

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

export const PLATFORM_ADMIN_EMAILS = Object.freeze([
    'claudiofranciscojunior2006@gmail.com',
]);

setPersistence(auth, browserSessionPersistence).catch(() => undefined);

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

function getSafeUserId() {
    return auth.currentUser?.uid ?? null;
}

export function normalizeEmail(email) {
    return String(email ?? '').trim().toLowerCase();
}

export function isAdminEmail(email) {
    return PLATFORM_ADMIN_EMAILS.includes(normalizeEmail(email));
}

export function resolveUserRole(email) {
    return isAdminEmail(email) ? 'ADMIN' : 'USER';
}

export function isPlatformAdminUser(user) {
    return Boolean(user?.email) && isAdminEmail(user.email);
}

export function assertPlatformAdminUser(user = auth.currentUser) {
    if (!isPlatformAdminUser(user)) {
        const error = new Error('Operação restrita à conta administrativa claudiofranciscojunior2006@gmail.com.');
        error.code = 'permission-denied';
        throw error;
    }
}

export function normalizeSearchTerm(term) {
    return String(term ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

export function getFriendlyAuthError(error) {
    const errorMap = {
        'auth/email-already-in-use': 'Este e-mail já está cadastrado. Faça login ou use outro endereço.',
        'auth/invalid-email': 'Informe um e-mail válido.',
        'auth/weak-password': 'A senha deve possuir pelo menos 6 caracteres.',
        'auth/user-not-found': 'Usuário não encontrado.',
        'auth/wrong-password': 'Senha incorreta.',
        'auth/invalid-credential': 'E-mail ou senha inválidos.',
        'auth/popup-closed-by-user': 'Login com Google cancelado antes da conclusão.',
        'auth/popup-blocked': 'O navegador bloqueou a janela de login do Google. Libere pop-ups para este site e tente novamente.',
        'auth/cancelled-popup-request': 'Outra janela de login já estava em andamento. Tente novamente.',
        'auth/account-exists-with-different-credential': 'Já existe uma conta com este e-mail usando outro método de autenticação.',
        'auth/network-request-failed': 'Falha de rede. Verifique sua conexão e tente novamente.',
        'auth/operation-not-allowed': 'Este método de entrada ainda não está disponível. Tente outra opção.',
        'auth/unauthorized-domain': 'Este endereço da plataforma ainda não está autorizado para entrada.',
        'permission-denied': 'Operação não autorizada. Use a conta administrativa claudiofranciscojunior2006@gmail.com.',
    };

    return errorMap[error?.code] || error?.message || 'Não foi possível concluir a operação. Tente novamente.';
}

export function toSessionUser(user) {
    if (!user) return null;
    return {
        uid: user.uid,
        name: user.displayName || user.email || 'Usuário ConectaPharma',
        email: user.email,
        photoURL: user.photoURL || null,
        provider: user.providerData?.[0]?.providerId === 'google.com' ? 'google' : 'email',
        role: resolveUserRole(user.email),
    };
}

export async function upsertUserDocument(user, provider, name = null) {
    if (!user?.uid) {
        throw new Error('Não foi possível validar os dados da conta para criação do perfil.');
    }

    const userRef = doc(db, 'users', user.uid);
    try {
        await getDoc(userRef);
    } catch (_) {
        // A leitura pode falhar se as regras ainda não foram publicadas. A gravação
        // abaixo continua sendo a operação que determina o estado do perfil.
    }

    const resolvedName = name || user.displayName || user.email || 'Usuário ConectaPharma';
    const resolvedRole = resolveUserRole(user.email);

    await setDoc(userRef, {
        uid: user.uid,
        name: resolvedName,
        email: normalizeEmail(user.email),
        photoURL: user.photoURL || null,
        provider,
        role: resolvedRole,
        active: true,
        createdAt: serverTimestamp(),
        lastLoginAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
    }, { merge: true });

    return { role: resolvedRole };
}

async function writeLogBestEffort(collectionName, payload) {
    try {
        await addDoc(collection(db, collectionName), {
            ...payload,
            userId: payload.userId ?? getSafeUserId(),
            createdAt: serverTimestamp(),
        });
    } catch (_) {
        // Métricas opcionais nunca devem impedir navegação, login ou consulta pública.
    }
}

export async function trackPageView(pageName) {
    await writeLogBestEffort('click_logs', { pharmacyId: `page:${pageName}`, actionType: 'VIEW' });
}

export async function trackLogin(method, userId = null) {
    await writeLogBestEffort('auth_logs', { method, eventType: 'LOGIN', userId: userId || getSafeUserId() });
}

export async function trackSignUp(method, userId = null) {
    await writeLogBestEffort('auth_logs', { method, eventType: 'SIGN_UP', userId: userId || getSafeUserId() });
}

export async function trackFormSubmit(formType) {
    await writeLogBestEffort('form_submit_logs', { formType });
}

export async function trackMedicineSearch(term, resultCount = 0) {
    await writeLogBestEffort('search_logs', {
        term: String(term || '').trim(),
        normalizedTerm: normalizeSearchTerm(term),
        resultCount,
    });
}

export async function trackPharmacyClick(pharmacyId, actionType = 'VIEW') {
    await writeLogBestEffort('click_logs', { pharmacyId: String(pharmacyId), actionType });
}

export async function signUpWithEmail(name, email, password) {
    const trimmedName = String(name ?? '').trim();
    const trimmedEmail = String(email ?? '').trim();

    if (!trimmedName || !trimmedEmail || !password) {
        throw new Error('Nome, e-mail e senha são obrigatórios.');
    }

    const credential = await createUserWithEmailAndPassword(auth, trimmedEmail, password);
    await updateProfile(credential.user, { displayName: trimmedName });
    await upsertUserDocument(credential.user, 'email', trimmedName);
    await trackSignUp('email', credential.user.uid);
    return credential.user;
}

export async function signInWithEmail(email, password) {
    const trimmedEmail = String(email ?? '').trim();

    if (!trimmedEmail || !password) {
        throw new Error('E-mail e senha são obrigatórios.');
    }

    const credential = await signInWithEmailAndPassword(auth, trimmedEmail, password);
    await upsertUserDocument(credential.user, 'email');
    await trackLogin('email', credential.user.uid);
    return credential.user;
}

export async function signInWithGoogle() {
    const credential = await signInWithPopup(auth, googleProvider);
    await upsertUserDocument(credential.user, 'google');
    await trackLogin('google', credential.user.uid);
    return credential.user;
}

export async function signOutUser() {
    await signOut(auth);
}

export function getCurrentUser() {
    return auth.currentUser;
}

export async function getCurrentIdToken(forceRefresh = false) {
    const user = auth.currentUser;
    if (!user) return null;
    return user.getIdToken(forceRefresh);
}

export function onAuthStateChange(callback) {
    return onAuthStateChanged(auth, callback);
}

function validateRequired(data, fields) {
    const missing = fields.filter((field) => !String(data?.[field] ?? '').trim());
    if (missing.length > 0) {
        throw new Error(`Campos obrigatórios ausentes: ${missing.join(', ')}.`);
    }
}

function matchesQuery(record, queryText, fields) {
    const queryValue = normalizeSearchTerm(queryText);
    if (!queryValue) return true;
    const haystack = normalizeSearchTerm(fields.map((field) => record?.[field]).filter(Boolean).join(' '));
    return queryValue.split(' ').every((term) => haystack.includes(term));
}

function snapshotToRecords(snapshot) {
    return snapshot.docs.map((item) => ({ id: item.id, ...item.data() }));
}

export async function listFarmacias({ q = '', max = 100 } = {}) {
    const snapshot = await getDocs(query(collection(db, 'farmacias'), limitQuery(max)));
    return snapshotToRecords(snapshot)
        .filter((item) => item.ativo !== false)
        .filter((item) => matchesQuery(item, q, ['nome', 'name', 'endereco', 'address', 'bairro', 'cidade', 'estado', 'cep', 'telefone', 'phone', 'email', 'website', 'horario_funcionamento', 'opening_hours_label', 'observacoes']))
        .sort((a, b) => String(a.nome || a.name || '').localeCompare(String(b.nome || b.name || ''), 'pt-BR'))
        .slice(0, max);
}

export async function createFarmacia(data) {
    assertPlatformAdminUser();
    validateRequired(data, ['nome', 'endereco']);
    const userId = getSafeUserId();
    const latitude = Number(data.latitude);
    const longitude = Number(data.longitude);
    const hasValidCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude);
    const openstreetmapUrl = hasValidCoordinates
        ? `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}`
        : null;
    const normalizedWhatsapp = String(data.whatsapp || '').replace(/\D+/g, '') || null;
    const horario = data.horario_funcionamento?.trim() || 'Horário não informado';
    const nome = data.nome.trim();
    const endereco = data.endereco.trim();

    const payload = {
        nome,
        name: nome,
        endereco,
        address: endereco,
        bairro: data.bairro?.trim() || null,
        cidade: data.cidade?.trim() || 'Belo Horizonte',
        estado: data.estado?.trim() || 'MG',
        cep: data.cep?.trim() || null,
        telefone: data.telefone?.trim() || null,
        phone: data.telefone?.trim() || null,
        whatsapp: normalizedWhatsapp,
        email: data.email?.trim() || null,
        website: data.website?.trim() || null,
        horario_funcionamento: horario,
        opening_hours_label: horario,
        latitude: hasValidCoordinates ? latitude : null,
        longitude: hasValidCoordinates ? longitude : null,
        openstreetmap_url: openstreetmapUrl,
        maps_url: openstreetmapUrl,
        observacoes: data.observacoes?.trim() || null,
        origem: 'manual_firestore',
        source: 'manual_firestore',
        ativo: data.ativo !== false,
        disponibilidade_farmaco: data.disponibilidade_farmaco !== false,
        createdBy: userId,
        updatedBy: userId,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
    };
    const ref = await addDoc(collection(db, 'farmacias'), payload);
    return { id: ref.id, ...payload };
}

export async function listMedications({ q = '', max = 100 } = {}) {
    const snapshot = await getDocs(query(collection(db, 'medications'), limitQuery(max)));
    return snapshotToRecords(snapshot)
        .filter((item) => item.active !== false && item.ativo !== false)
        .filter((item) => matchesQuery(item, q, ['nome', 'name', 'categoria', 'category', 'descricao', 'description']))
        .sort((a, b) => String(a.nome || a.name || '').localeCompare(String(b.nome || b.name || ''), 'pt-BR'))
        .slice(0, max);
}

export async function createMedication(data) {
    assertPlatformAdminUser();
    validateRequired(data, ['nome']);
    const userId = getSafeUserId();
    const payload = {
        nome: data.nome.trim(),
        categoria: data.categoria?.trim() || null,
        descricao: data.descricao?.trim() || null,
        dose_diaria_comprimidos: Number(data.dose_diaria_comprimidos || 1),
        stock: Number(data.stock || 0),
        requires_prescription: Boolean(data.requires_prescription),
        active: true,
        createdBy: userId,
        updatedBy: userId,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
    };
    const ref = await addDoc(collection(db, 'medications'), payload);
    return { id: ref.id, ...payload };
}

export async function listMedicineAlerts({ role = 'USER', max = 20 } = {}) {
    const normalizedRole = String(role || 'USER').toUpperCase();
    const userId = getSafeUserId();
    const baseCollection = collection(db, 'medicine_alerts');
    const q = normalizedRole === 'ADMIN'
        ? query(baseCollection, orderBy('createdAt'), limitQuery(max))
        : query(baseCollection, where('userId', '==', userId || '__none__'), limitQuery(max));
    const snapshot = await getDocs(q);
    return snapshotToRecords(snapshot);
}

export async function submitContactForm(data) {
    validateRequired(data, ['name', 'email', 'message']);
    await addDoc(collection(db, 'contact_forms'), {
        name: data.name.trim(),
        email: data.email.trim(),
        phone: data.phone?.trim() || null,
        message: data.message.trim(),
        userId: getSafeUserId(),
        createdAt: serverTimestamp(),
        status: 'OPEN',
    });
    await trackFormSubmit('contact');
}

export async function submitFeedbackForm(data) {
    validateRequired(data, ['message']);
    await addDoc(collection(db, 'feedbacks'), {
        message: data.message.trim(),
        category: data.category || 'OTHER',
        userId: getSafeUserId(),
        createdAt: serverTimestamp(),
        status: 'OPEN',
    });
    await trackFormSubmit('feedback');
}

export async function submitPharmacyInterestForm(data) {
    validateRequired(data, ['pharmacyName', 'responsibleName', 'email', 'phone', 'city', 'state']);
    await addDoc(collection(db, 'pharmacy_interest_forms'), {
        pharmacyName: data.pharmacyName.trim(),
        responsibleName: data.responsibleName.trim(),
        email: data.email.trim(),
        phone: data.phone.trim(),
        city: data.city.trim(),
        state: data.state.trim(),
        message: data.message?.trim() || null,
        userId: getSafeUserId(),
        createdAt: serverTimestamp(),
        status: 'OPEN',
    });
    await trackFormSubmit('pharmacy_interest');
}

export async function submitMedicineSearchRequest(data) {
    validateRequired(data, ['medicineName']);
    await addDoc(collection(db, 'medicine_search_requests'), {
        medicineName: data.medicineName.trim(),
        normalizedMedicineName: normalizeSearchTerm(data.medicineName),
        city: data.city?.trim() || null,
        state: data.state?.trim() || null,
        message: data.message?.trim() || null,
        userId: getSafeUserId(),
        createdAt: serverTimestamp(),
        status: 'OPEN',
    });
    await trackFormSubmit('medicine_search_request');
}
