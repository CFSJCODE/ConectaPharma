const HEALTH_UNITS_PATH = 'unidades-saude.html';
const currentPage = window.location.pathname.split('/').pop() || 'index.html';

function ensureHealthUnitsNavigation() {
    document.querySelectorAll('.nav-links').forEach((navLinks) => {
        const hasHealthUnitsLink = navLinks.querySelector(`a[href="${HEALTH_UNITS_PATH}"]`);

        if (!hasHealthUnitsLink) {
            const item = document.createElement('li');
            const link = document.createElement('a');
            link.href = HEALTH_UNITS_PATH;
            link.textContent = 'Unidades de saúde';

            if (currentPage === HEALTH_UNITS_PATH) {
                link.setAttribute('aria-current', 'page');
            }

            item.appendChild(link);

            const mobileLogin = navLinks.querySelector('.nav-login-mobile');
            const afterHowItWorks = Array.from(navLinks.querySelectorAll('a')).find((anchor) => anchor.getAttribute('href') === 'como-funciona.html')?.parentElement;

            if (afterHowItWorks?.nextSibling) {
                navLinks.insertBefore(item, afterHowItWorks.nextSibling);
            } else if (mobileLogin) {
                navLinks.insertBefore(item, mobileLogin);
            } else {
                navLinks.appendChild(item);
            }
        }
    });

    document.querySelectorAll('.footer-links').forEach((footerLinks) => {
        if (footerLinks.querySelector(`a[href="${HEALTH_UNITS_PATH}"]`)) {
            return;
        }

        const link = document.createElement('a');
        link.href = HEALTH_UNITS_PATH;
        link.textContent = 'Unidades de saúde';
        footerLinks.append(' · ', link);
    });
}

ensureHealthUnitsNavigation();

const revealElements = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });
    revealElements.forEach((element) => observer.observe(element));
} else {
    revealElements.forEach((element) => element.classList.add('is-visible'));
}

const countElement = document.getElementById('farmacias-count');
const statusElement = document.getElementById('public-data-status');
if (countElement) {
    import('./firebaseClient.js')
        .then(({ listFarmacias }) => listFarmacias({ max: 500 }))
        .then((items) => {
            countElement.textContent = String(items.length);
            if (statusElement) statusElement.innerHTML = '<span class="status-dot" aria-hidden="true"></span> Informações disponíveis';
        })
        .catch(() => {
            countElement.textContent = '—';
            if (statusElement) statusElement.textContent = 'Consulte após entrar';
        });
}

const listenButton = document.getElementById('listen-summary');
if (listenButton && 'speechSynthesis' in window) {
    listenButton.hidden = false;
    listenButton.addEventListener('click', () => {
        const summary = listenButton.dataset.summary || 'O ConectaPharma ajuda você a consultar farmácias cadastradas, horários de atendimento e serviços de saúde próximos com mais facilidade.';
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(summary);
        utterance.lang = 'pt-BR';
        utterance.rate = 0.92;
        window.speechSynthesis.speak(utterance);
    });
}
