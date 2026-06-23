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

export const analyticsPromise = typeof window !== 'undefined'
    ? isSupported().then((supported) => (supported ? getAnalytics(app) : null)).catch(() => null)
    : Promise.resolve(null);

setPersistence(auth, browserSessionPersistence).catch((error) => {
    console.warn('ConectaPharma Firebase: não foi possível aplicar persistência de sessão.', error);
});

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
    };
}

export async function upsertUserDocument(user, provider, name = null) {
    if (!user?.uid) {
        throw new Error('Usuário Firebase inválido para persistência no Firestore.');
    }

    const userRef = doc(db, 'users', user.uid);
    const snapshot = await getDoc(userRef);
    const resolvedName = name || user.displayName || user.email || 'Usuário ConectaPharma';

    if (!snapshot.exists()) {
        await setDoc(userRef, {
            uid: user.uid,
            name: resolvedName,
            email: user.email,
            photoURL: user.photoURL || null,
            provider,
            role: 'USER',
            createdAt: serverTimestamp(),
            lastLoginAt: serverTimestamp(),
            active: true,
        });
        return { created: true };
    }

    await updateDoc(userRef, {
        name: resolvedName,
        email: user.email,
        photoURL: user.photoURL || null,
        lastLoginAt: serverTimestamp(),
        active: true,
    });

    return { created: false };
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
    } catch (error) {
        console.warn(`ConectaPharma Firebase: falha ao gravar log em ${collectionName}.`, error);
    }
}

async function trackAnalyticsEvent(eventName, params = {}) {
    const analytics = await analyticsPromise;
    if (!analytics) return;
    logEvent(analytics, eventName, params);
}

export async function trackPageView(pageName) {
    await trackAnalyticsEvent('page_view', {
        page_title: pageName,
        page_location: window.location.href,
        page_path: window.location.pathname,
    });
}

export async function trackLogin(method, userId = null) {
    await trackAnalyticsEvent('login', { method });
    await writeLogBestEffort('auth_logs', {
        method,
        eventType: 'LOGIN',
        userId,
    });
}

export async function trackSignUp(method, userId = null) {
    await trackAnalyticsEvent('sign_up', { method });
    await writeLogBestEffort('auth_logs', {
        method,
        eventType: 'SIGN_UP',
        userId,
    });
}

export async function trackFormSubmit(formType) {
    await trackAnalyticsEvent('form_submit', { form_type: formType });
    await writeLogBestEffort('form_submit_logs', {
        formType,
        userId: getSafeUserId(),
    });
}

export async function trackMedicineSearch(term, resultCount = 0) {
    const normalizedTerm = normalizeSearchTerm(term);
    if (!normalizedTerm) return;

    await trackAnalyticsEvent('search', {
        search_term: normalizedTerm,
        result_count: Number(resultCount) || 0,
    });

    await writeLogBestEffort('search_logs', {
        term: String(term).trim(),
        normalizedTerm,
        resultCount: Number(resultCount) || 0,
        userId: getSafeUserId(),
    });
}

export async function trackPharmacyClick(pharmacyId, actionType = 'VIEW') {
    if (!pharmacyId) return;

    await trackAnalyticsEvent('pharmacy_click', {
        pharmacy_id: String(pharmacyId),
        action_type: actionType,
    });

    await writeLogBestEffort('click_logs', {
        pharmacyId: String(pharmacyId),
        actionType,
        userId: getSafeUserId(),
    });
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
