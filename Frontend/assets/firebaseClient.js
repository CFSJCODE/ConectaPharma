import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-app.js';
import { getAnalytics, isSupported, logEvent } from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-analytics.js';
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
    updateDoc,
    addDoc,
    collection,
    serverTimestamp,
} from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-firestore.js';

// Configuração pública do app Web registrada no Firebase Console.
// Este é o local correto para a configuração no projeto estático atual.
// Não inserir a tag <script> gerada pelo Console diretamente nas páginas HTML;
// as páginas devem importar este módulo para preservar a camada de serviço.
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

export function normalizeEmail(email) {
    return String(email ?? '').trim().toLowerCase();
}

export function isAdminEmail(email) {
    return PLATFORM_ADMIN_EMAILS.includes(normalizeEmail(email));
}

export function resolveUserRole(email, currentRole = 'USER') {
    if (String(currentRole || '').toUpperCase() === 'ADMIN' || isAdminEmail(email)) {
        return 'ADMIN';
    }
    return 'USER';
}

let analyticsInstancePromise = null;

export function getAnalyticsSafe() {
    if (typeof window === 'undefined') return Promise.resolve(null);
    if (!analyticsInstancePromise) {
        analyticsInstancePromise = isSupported()
            .then((supported) => (supported ? getAnalytics(app) : null))
            .catch(() => null);
    }
    return analyticsInstancePromise;
}

setPersistence(auth, browserSessionPersistence).catch(() => undefined);

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

function getSafeUserId() {
    return auth.currentUser?.uid ?? null;
}

export function normalizeSearchTerm(term) {
    return String(term ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
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
        'auth/account-exists-with-different-credential': 'Já existe uma conta com este e-mail usando outro método de autenticação.',
        'auth/network-request-failed': 'Falha de rede. Verifique sua conexão e tente novamente.',
        'permission-denied': 'Operação bloqueada pelas regras do Firestore. Verifique a publicação das regras de segurança.',
    };

    return errorMap[error?.code] || 'Não foi possível concluir a operação. Tente novamente.';
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
        throw new Error('Usuário Firebase inválido para persistência no Firestore.');
    }

    const userRef = doc(db, 'users', user.uid);
    const snapshot = await getDoc(userRef);
    const resolvedName = name || user.displayName || user.email || 'Usuário ConectaPharma';
    const existingRole = snapshot.exists() ? snapshot.data()?.role : 'USER';
    const resolvedRole = resolveUserRole(user.email, existingRole);

    if (!snapshot.exists()) {
        await setDoc(userRef, {
            uid: user.uid,
            name: resolvedName,
            email: normalizeEmail(user.email),
            photoURL: user.photoURL || null,
            provider,
            role: resolvedRole,
            createdAt: serverTimestamp(),
            lastLoginAt: serverTimestamp(),
            active: true,
        });
        return { created: true, role: resolvedRole };
    }

    await updateDoc(userRef, {
        name: resolvedName,
        email: normalizeEmail(user.email),
        photoURL: user.photoURL || null,
        role: resolvedRole,
        lastLoginAt: serverTimestamp(),
        active: true,
    });

    return { created: false, role: resolvedRole };
}

async function writeLog(collectionName, payload) {
    await addDoc(collection(db, collectionName), {
        ...payload,
        userId: payload.userId ?? getSafeUserId(),
        createdAt: serverTimestamp(),
    });
}

async function writeLogBestEffort(collectionName, payload) {
    try {
        await writeLog(collectionName, payload);
    } catch (_) {
        // Métrica opcional: falha silenciosa para não impactar a experiência.
    }
}

async function trackAnalyticsEvent(_eventName, _params = {}) {
    return undefined;
}

export async function trackPageView(_pageName) {
    return undefined;
}

export async function trackLogin(_method, _userId = null) {
    return undefined;
}

export async function trackSignUp(_method, _userId = null) {
    return undefined;
}

export async function trackFormSubmit(_formType) {
    return undefined;
}

export async function trackMedicineSearch(_term, _resultCount = 0) {
    return undefined;
}

export async function trackPharmacyClick(_pharmacyId, _actionType = 'VIEW') {
    return undefined;
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
    const result = await upsertUserDocument(credential.user, 'google');

    if (result.created) {
        await trackSignUp('google', credential.user.uid);
    } else {
        await trackLogin('google', credential.user.uid);
    }

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
