// Scroll reveal com stagger por grupo
// Emil: elementos que entram juntos devem escalonar 50ms entre si
const SELECTORS = '.step, .persona-card, .rule-card, .cmd-card, .antirank-item';

document.querySelectorAll(SELECTORS).forEach(el => el.classList.add('reveal'));

const observer = new IntersectionObserver(entries => {
  // Agrupar os que ficaram visíveis neste tick pelo container pai
  const byParent = new Map();
  entries.forEach(e => {
    if (!e.isIntersecting || e.target.classList.contains('visible')) return;
    const key = e.target.parentElement;
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key).push(e.target);
  });

  byParent.forEach(siblings => {
    siblings.forEach((el, i) => {
      // Emil: stagger máximo de 50ms entre irmãos, sob 300ms no total
      el.style.transitionDelay = `${i * 55}ms`;
      el.classList.add('visible');
      // Limpar delay após a animação terminar para não afetar futuras transições
      el.addEventListener('transitionend', () => {
        el.style.transitionDelay = '';
      }, { once: true });
    });
  });
}, { threshold: 0.1 });

document.querySelectorAll(SELECTORS).forEach(el => observer.observe(el));

// Nav scroll shadow
const nav = document.querySelector('.nav');
window.addEventListener('scroll', () => {
  nav.style.boxShadow = window.scrollY > 10
    ? '0 4px 40px rgba(0,0,0,0.4)'
    : '';
}, { passive: true });

// Mobile nav toggle
// Emil: aria-expanded como fonte de verdade do estado — sem flags extras
const navToggle = document.querySelector('.nav-toggle');
const navMobile = document.querySelector('.nav-mobile');

if (navToggle && navMobile) {
  function openMenu() {
    navToggle.setAttribute('aria-expanded', 'true');
    navMobile.classList.add('is-open');
    navToggle.setAttribute('aria-label', 'Fechar menu');
  }
  function closeMenu() {
    navToggle.setAttribute('aria-expanded', 'false');
    navMobile.classList.remove('is-open');
    navToggle.setAttribute('aria-label', 'Abrir menu');
  }

  navToggle.addEventListener('click', () => {
    navToggle.getAttribute('aria-expanded') === 'true' ? closeMenu() : openMenu();
  });

  // Fecha ao clicar em qualquer link do menu
  navMobile.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Fecha ao clicar fora — usa capture para pegar antes do bubbling
  document.addEventListener('click', e => {
    if (!nav.contains(e.target)) closeMenu();
  }, { passive: true });

  // Fecha ao pressionar Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeMenu();
  });
}