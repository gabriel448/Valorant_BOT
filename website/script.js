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