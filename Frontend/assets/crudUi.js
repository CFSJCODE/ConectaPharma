import {
    listFarmacias,
    listMedications,
    onAuthStateChange,
    isPlatformAdminUser,
} from './firebaseClient.js';
import {
    deleteFarmacia,
    deleteMedication,
    updateFarmacia,
    updateMedication,
} from './crudClient.js';

const state = {
    user: null,
    isAdmin: false,
    medicines: [],
    pharmacies: [],
    selectedMedicineId: null,
    selectedPharmacyId: null,
};

function byId(id) {
    return document.getElementById(id);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function setText(id, value) {
    const element = byId(id);
    if (element) element.innerText = String(value ?? '');
}

function asText(value) {
    return String(value ?? '').trim();
}

function canManageMedicine(item) {
    return state.isAdmin || Boolean(item?.createdBy && item.createdBy === state.user?.uid);
}

function injectStyles() {
    if (byId('crud-ui-style')) return;

    const style = document.createElement('style');
    style.id = 'crud-ui-style';
    style.textContent = `
        .crud-panel { border: 1px dashed rgba(0, 93, 170, 0.22); background: linear-gradient(135deg, #FFFFFF, #F5F9FF); }
        .crud-title-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; justify-content: space-between; }
        .crud-subgrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 1.2rem; }
        .crud-box { padding: 1rem; border-radius: 18px; background: #FFFFFF; border: 1px solid var(--color-border); }
        .crud-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; margin-top: 0.85rem; }
        .crud-form .span-2 { grid-column: 1 / -1; }
        .crud-list { display: grid; gap: 0.75rem; margin-top: 0.85rem; max-height: 520px; overflow: auto; padding-right: 0.25rem; }
        .crud-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
        .btn-danger { background: #B91C1C; color: #FFFFFF; }
        .btn-danger:hover { background: #991B1B; }
        .btn-small { padding: 0.55rem 0.8rem; font-size: 0.82rem; }
        .crud-muted { color: var(--color-muted); font-size: 0.92rem; line-height: 1.45; }
        @media (max-width: 980px) { .crud-subgrid, .crud-form { grid-template-columns: 1fr; } .crud-form .span-2 { grid-column: auto; } }
    `;
    document.head.appendChild(style);
}

function ensureSection() {
    const pageBody = document.querySelector('.page-body');
    if (!pageBody) return null;

    let section = byId('crud-management-section');
    if (section) return section;

    section = document.createElement('section');
    section.id = 'crud-management-section';
    section.className = 'card card-wide crud-panel';
    section.innerHTML = `
        <div class="crud-title-row">
            <div>
                <h2 class="section-title">Gestão de registros</h2>
                <p class="section-subtitle" id="crud-access-description">Carregando permissões de gestão...</p>
            </div>
            <button class="btn btn-secondary" id="btn-crud-refresh" type="button">Atualizar gestão</button>
        </div>
        <p id="crud-global-status" class="message">Aguardando autenticação.</p>
        <div class="crud-subgrid">
            <div class="crud-box" id="medicine-crud-box"></div>
            <div class="crud-box" id="pharmacy-crud-box"></div>
        </div>
    `;

    pageBody.appendChild(section);
    byId('btn-crud-refresh').addEventListener('click', refreshCrudData);
    return section;
}

function medicineFormHtml() {
    return `
        <form id="crud-medicine-form" class="crud-form" autocomplete="off" hidden>
            <input id="crud-medicine-name" class="input" type="text" placeholder="Nome do medicamento" required>
            <input id="crud-medicine-category" class="input" type="text" placeholder="Categoria">
            <input id="crud-medicine-dose" class="input" type="number" min="0.1" max="20" step="0.1" placeholder="Dose diária">
            <input id="crud-medicine-stock" class="input" type="number" min="0" max="100000" step="1" placeholder="Estoque">
            <select id="crud-medicine-prescription" class="select">
                <option value="true">Requer prescrição</option>
                <option value="false">Não requer prescrição</option>
            </select>
            <textarea id="crud-medicine-description" class="span-2" rows="3" placeholder="Descrição ou observação"></textarea>
            <div class="span-2 crud-actions">
                <button class="btn btn-accent btn-small" type="submit">Salvar alteração</button>
                <button class="btn btn-secondary btn-small" id="crud-cancel-medicine" type="button">Cancelar</button>
            </div>
        </form>
    `;
}

function pharmacyFormHtml() {
    return `
        <form id="crud-pharmacy-form" class="crud-form" autocomplete="off" hidden>
            <input id="crud-pharmacy-name" class="input" type="text" placeholder="Nome da farmácia" required>
            <input id="crud-pharmacy-phone" class="input" type="tel" placeholder="Telefone">
            <input id="crud-pharmacy-address" class="input span-2" type="text" placeholder="Endereço completo" required>
            <input id="crud-pharmacy-neighborhood" class="input" type="text" placeholder="Bairro">
            <input id="crud-pharmacy-city" class="input" type="text" placeholder="Cidade">
            <input id="crud-pharmacy-state" class="input" type="text" placeholder="UF" maxlength="2">
            <input id="crud-pharmacy-cep" class="input" type="text" placeholder="CEP">
            <input id="crud-pharmacy-whatsapp" class="input" type="tel" placeholder="WhatsApp">
            <input id="crud-pharmacy-email" class="input" type="email" placeholder="E-mail">
            <input id="crud-pharmacy-website" class="input span-2" type="url" placeholder="Site">
            <input id="crud-pharmacy-hours" class="input span-2" type="text" placeholder="Horário de funcionamento">
            <input id="crud-pharmacy-latitude" class="input" type="number" step="0.000001" placeholder="Latitude">
            <input id="crud-pharmacy-longitude" class="input" type="number" step="0.000001" placeholder="Longitude">
            <select id="crud-pharmacy-availability" class="select">
                <option value="true">Disponível na plataforma</option>
                <option value="false">Verificar estoque</option>
            </select>
            <select id="crud-pharmacy-active" class="select">
                <option value="true">Ativa</option>
                <option value="false">Inativa</option>
            </select>
            <textarea id="crud-pharmacy-notes" class="span-2" rows="3" placeholder="Observações administrativas"></textarea>
            <div class="span-2 crud-actions">
                <button class="btn btn-accent btn-small" type="submit">Salvar alteração</button>
                <button class="btn btn-secondary btn-small" id="crud-cancel-pharmacy" type="button">Cancelar</button>
            </div>
        </form>
    `;
}

function renderMedicineManager() {
    const box = byId('medicine-crud-box');
    if (!box) return;

    const canEditAny = state.isAdmin;
    const intro = canEditAny
        ? 'Conta administrativa: leitura, criação pelo formulário do catálogo, edição e exclusão de medicamentos.'
        : 'Conta comum: leitura do catálogo e edição/exclusão apenas dos medicamentos vinculados à sua conta.';

    box.innerHTML = `
        <h3 class="section-title">Medicamentos</h3>
        <p class="crud-muted">${intro}</p>
        ${medicineFormHtml()}
        <p id="crud-medicine-status" class="message">${state.medicines.length} medicamento(s) carregado(s).</p>
        <div class="crud-list" id="crud-medicine-list"></div>
    `;

    byId('crud-medicine-form').addEventListener('submit', saveMedicineEdit);
    byId('crud-cancel-medicine').addEventListener('click', cancelMedicineEdit);

    const list = byId('crud-medicine-list');
    if (!state.medicines.length) {
        list.innerHTML = '<p class="loading-text">Nenhum medicamento cadastrado.</p>';
        return;
    }

    list.innerHTML = state.medicines.map((item) => {
        const canManage = canManageMedicine(item);
        const badge = item.requires_prescription ? 'Prescrição' : 'Livre';
        return `
            <div class="item-card">
                <div class="item-head">
                    <div>
                        <strong>${escapeHtml(item.nome || item.name || 'Medicamento')}</strong>
                        <p>${escapeHtml(item.categoria || item.category || 'Categoria não informada')} · Estoque: ${escapeHtml(item.stock ?? 0)}</p>
                        <p>${escapeHtml(item.descricao || item.description || 'Sem descrição operacional.')}</p>
                    </div>
                    <span class="badge ${item.requires_prescription ? 'warn' : 'ok'}">${badge}</span>
                </div>
                <div class="crud-actions">
                    <button class="btn btn-secondary btn-small" data-crud-action="edit-medicine" data-id="${escapeHtml(item.id)}" ${canManage ? '' : 'disabled'}>Editar</button>
                    <button class="btn btn-danger btn-small" data-crud-action="delete-medicine" data-id="${escapeHtml(item.id)}" ${canManage ? '' : 'disabled'}>Excluir</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderPharmacyManager() {
    const box = byId('pharmacy-crud-box');
    if (!box) return;

    if (!state.isAdmin) {
        box.innerHTML = `
            <h3 class="section-title">Farmácias</h3>
            <p class="crud-muted">Contas comuns podem consultar farmácias cadastradas e usar a busca por proximidade. A criação, edição e exclusão de farmácias permanecem restritas ao responsável autorizado.</p>
            <p class="message">Acesso administrativo não habilitado para esta conta.</p>
        `;
        return;
    }

    box.innerHTML = `
        <h3 class="section-title">Farmácias</h3>
        <p class="crud-muted">Conta administrativa: criação, leitura, edição e exclusão de farmácias cadastradas.</p>
        <div class="crud-actions">
            <a class="btn btn-accent btn-small" href="cadastrar-farmacias.html">Criar nova farmácia</a>
        </div>
        ${pharmacyFormHtml()}
        <p id="crud-pharmacy-status" class="message">${state.pharmacies.length} farmácia(s) carregada(s).</p>
        <div class="crud-list" id="crud-pharmacy-list"></div>
    `;

    byId('crud-pharmacy-form').addEventListener('submit', savePharmacyEdit);
    byId('crud-cancel-pharmacy').addEventListener('click', cancelPharmacyEdit);

    const list = byId('crud-pharmacy-list');
    if (!state.pharmacies.length) {
        list.innerHTML = '<p class="loading-text">Nenhuma farmácia cadastrada.</p>';
        return;
    }

    list.innerHTML = state.pharmacies.map((item) => `
        <div class="item-card">
            <div class="item-head">
                <div>
                    <strong>${escapeHtml(item.nome || item.name || 'Farmácia')}</strong>
                    <p>${escapeHtml(item.endereco || item.address || 'Endereço não informado')}</p>
                    <p>${escapeHtml(item.horario_funcionamento || item.opening_hours_label || 'Horário não informado')}</p>
                </div>
                <span class="badge ${item.ativo === false ? 'warn' : 'ok'}">${item.ativo === false ? 'Inativa' : 'Ativa'}</span>
            </div>
            <div class="crud-actions">
                <button class="btn btn-secondary btn-small" data-crud-action="edit-pharmacy" data-id="${escapeHtml(item.id)}">Editar</button>
                <button class="btn btn-danger btn-small" data-crud-action="delete-pharmacy" data-id="${escapeHtml(item.id)}">Excluir</button>
            </div>
        </div>
    `).join('');
}

function renderAll() {
    ensureSection();
    setText('crud-access-description', state.isAdmin
        ? 'Seu perfil possui CRUD administrativo completo para farmácias e medicamentos.'
        : 'Seu perfil possui leitura geral e RUD operacional apenas nos registros permitidos para sua conta.');
    renderMedicineManager();
    renderPharmacyManager();
}

async function refreshCrudData() {
    if (!state.user) return;

    setText('crud-global-status', 'Atualizando registros de gestão...');

    try {
        const [medicines, pharmacies] = await Promise.all([
            listMedications({ max: 200 }),
            state.isAdmin ? listFarmacias({ max: 200 }) : Promise.resolve([]),
        ]);

        state.medicines = Array.isArray(medicines) ? medicines : [];
        state.pharmacies = Array.isArray(pharmacies) ? pharmacies : [];
        renderAll();
        setText('crud-global-status', 'Registros atualizados.');
    } catch (error) {
        setText('crud-global-status', error?.message || 'Não foi possível atualizar os registros de gestão.');
    }
}

function populateMedicineForm(item) {
    state.selectedMedicineId = item.id;
    const form = byId('crud-medicine-form');
    form.hidden = false;
    byId('crud-medicine-name').value = item.nome || item.name || '';
    byId('crud-medicine-category').value = item.categoria || item.category || '';
    byId('crud-medicine-dose').value = item.dose_diaria_comprimidos ?? 1;
    byId('crud-medicine-stock').value = item.stock ?? 0;
    byId('crud-medicine-prescription').value = item.requires_prescription ? 'true' : 'false';
    byId('crud-medicine-description').value = item.descricao || item.description || '';
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function cancelMedicineEdit() {
    state.selectedMedicineId = null;
    const form = byId('crud-medicine-form');
    if (form) {
        form.reset();
        form.hidden = true;
    }
}

async function saveMedicineEdit(event) {
    event.preventDefault();
    if (!state.selectedMedicineId) return;

    setText('crud-medicine-status', 'Salvando medicamento...');

    try {
        await updateMedication(state.selectedMedicineId, {
            nome: asText(byId('crud-medicine-name').value),
            categoria: asText(byId('crud-medicine-category').value),
            descricao: asText(byId('crud-medicine-description').value),
            dose_diaria_comprimidos: Number(byId('crud-medicine-dose').value || 1),
            stock: Number(byId('crud-medicine-stock').value || 0),
            requires_prescription: byId('crud-medicine-prescription').value === 'true',
            active: true,
        });
        cancelMedicineEdit();
        await refreshCrudData();
        setText('crud-medicine-status', 'Medicamento atualizado com sucesso.');
    } catch (error) {
        setText('crud-medicine-status', error?.message || 'Não foi possível atualizar o medicamento.');
    }
}

function populatePharmacyForm(item) {
    state.selectedPharmacyId = item.id;
    const form = byId('crud-pharmacy-form');
    form.hidden = false;
    byId('crud-pharmacy-name').value = item.nome || item.name || '';
    byId('crud-pharmacy-phone').value = item.telefone || item.phone || '';
    byId('crud-pharmacy-address').value = item.endereco || item.address || '';
    byId('crud-pharmacy-neighborhood').value = item.bairro || '';
    byId('crud-pharmacy-city').value = item.cidade || 'Belo Horizonte';
    byId('crud-pharmacy-state').value = item.estado || 'MG';
    byId('crud-pharmacy-cep').value = item.cep || '';
    byId('crud-pharmacy-whatsapp').value = item.whatsapp || '';
    byId('crud-pharmacy-email').value = item.email || '';
    byId('crud-pharmacy-website').value = item.website || '';
    byId('crud-pharmacy-hours').value = item.horario_funcionamento || item.opening_hours_label || '';
    byId('crud-pharmacy-latitude').value = item.latitude ?? '';
    byId('crud-pharmacy-longitude').value = item.longitude ?? '';
    byId('crud-pharmacy-availability').value = item.disponibilidade_farmaco === false ? 'false' : 'true';
    byId('crud-pharmacy-active').value = item.ativo === false ? 'false' : 'true';
    byId('crud-pharmacy-notes').value = item.observacoes || '';
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function cancelPharmacyEdit() {
    state.selectedPharmacyId = null;
    const form = byId('crud-pharmacy-form');
    if (form) {
        form.reset();
        form.hidden = true;
    }
}

async function savePharmacyEdit(event) {
    event.preventDefault();
    if (!state.selectedPharmacyId) return;

    setText('crud-pharmacy-status', 'Salvando farmácia...');

    try {
        await updateFarmacia(state.selectedPharmacyId, {
            nome: asText(byId('crud-pharmacy-name').value),
            endereco: asText(byId('crud-pharmacy-address').value),
            bairro: asText(byId('crud-pharmacy-neighborhood').value),
            cidade: asText(byId('crud-pharmacy-city').value),
            estado: asText(byId('crud-pharmacy-state').value),
            cep: asText(byId('crud-pharmacy-cep').value),
            telefone: asText(byId('crud-pharmacy-phone').value),
            whatsapp: asText(byId('crud-pharmacy-whatsapp').value),
            email: asText(byId('crud-pharmacy-email').value),
            website: asText(byId('crud-pharmacy-website').value),
            horario_funcionamento: asText(byId('crud-pharmacy-hours').value),
            latitude: asText(byId('crud-pharmacy-latitude').value),
            longitude: asText(byId('crud-pharmacy-longitude').value),
            disponibilidade_farmaco: byId('crud-pharmacy-availability').value === 'true',
            ativo: byId('crud-pharmacy-active').value === 'true',
            observacoes: asText(byId('crud-pharmacy-notes').value),
        });
        cancelPharmacyEdit();
        await refreshCrudData();
        setText('crud-pharmacy-status', 'Farmácia atualizada com sucesso.');
    } catch (error) {
        setText('crud-pharmacy-status', error?.message || 'Não foi possível atualizar a farmácia.');
    }
}

async function handleCrudClick(event) {
    const button = event.target.closest('[data-crud-action]');
    if (!button) return;

    const action = button.dataset.crudAction;
    const id = button.dataset.id;

    if (action === 'edit-medicine') {
        const item = state.medicines.find((record) => record.id === id);
        if (item) populateMedicineForm(item);
        return;
    }

    if (action === 'delete-medicine') {
        const item = state.medicines.find((record) => record.id === id);
        if (!item || !window.confirm(`Excluir o medicamento "${item.nome || item.name || 'selecionado'}"?`)) return;
        setText('crud-medicine-status', 'Excluindo medicamento...');
        await deleteMedication(id);
        await refreshCrudData();
        return;
    }

    if (action === 'edit-pharmacy') {
        const item = state.pharmacies.find((record) => record.id === id);
        if (item) populatePharmacyForm(item);
        return;
    }

    if (action === 'delete-pharmacy') {
        const item = state.pharmacies.find((record) => record.id === id);
        if (!item || !window.confirm(`Excluir a farmácia "${item.nome || item.name || 'selecionada'}"?`)) return;
        setText('crud-pharmacy-status', 'Excluindo farmácia...');
        await deleteFarmacia(id);
        await refreshCrudData();
    }
}

function bootCrudUi() {
    injectStyles();
    ensureSection();
    document.addEventListener('click', (event) => {
        handleCrudClick(event).catch((error) => {
            setText('crud-global-status', error?.message || 'Não foi possível executar a ação solicitada.');
        });
    });

    onAuthStateChange((user) => {
        state.user = user || null;
        state.isAdmin = isPlatformAdminUser(user);

        if (!user) {
            setText('crud-access-description', 'Entre na plataforma para acessar a gestão de registros.');
            setText('crud-global-status', 'Sessão não autenticada.');
            return;
        }

        refreshCrudData();
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootCrudUi);
} else {
    bootCrudUi();
}
