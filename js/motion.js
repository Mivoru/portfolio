// Page motion: smooth wheel scrolling, scroll reveals, header timecode and cursor effects.
// With reduced motion only the timecode and progress bar stay. Touch keeps native scrolling.
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;

if (!still && window.Lenis) {
  const lenis = new Lenis({ autoRaf: true, lerp: 0.11 });
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href^="#"]');
    const target = link && document.querySelector(link.hash);
    if (!target) return;
    event.preventDefault();
    history.pushState(null, '', link.hash);
    lenis.scrollTo(target, { offset: -72, duration: 1.3 });
  });
}

// Headlines rise word by word from behind a mask.
function splitWords(heading) {
  const words = heading.textContent.trim().split(/\s+/);
  heading.setAttribute('aria-label', heading.textContent.trim());
  heading.textContent = '';
  words.forEach((word, index) => {
    const mask = document.createElement('span');
    mask.className = 'w';
    mask.setAttribute('aria-hidden', 'true');
    const inner = mask.appendChild(document.createElement('span'));
    inner.textContent = word;
    inner.style.setProperty('--i', index);
    heading.append(mask, index < words.length - 1 ? ' ' : '');
  });
}

// Numbers count up to their final text, for example "76 493" or "0,67 USD".
function countUp(item) {
  const match = item.textContent.match(/^([\d ]*\d)(?:,(\d+))?(.*)$/);
  if (!match) return;
  const decimals = match[2] ? match[2].length : 0;
  const end = Number(match[1].replace(/ /g, '') + (match[2] ? `.${match[2]}` : ''));
  const final = item.textContent;
  const started = performance.now();
  const show = (value) => {
    const [whole, part] = value.toFixed(decimals).split('.');
    const grouped = whole.replace(/\B(?=(\d{3})+$)/g, ' ');
    item.textContent = `${grouped}${part ? `,${part}` : ''}${match[3]}`;
  };
  const tick = (now) => {
    const progress = Math.min(1, (now - started) / 1500);
    if (progress === 1) { item.textContent = final; return; }
    show(end * (1 - (1 - progress) ** 4));
    requestAnimationFrame(tick);
  };
  show(0);
  requestAnimationFrame(tick);
}

if (!still) {
  const seen = new IntersectionObserver((entries) => {
    entries.filter((entry) => entry.isIntersecting).forEach((entry) => {
      entry.target.classList.add('in');
      seen.unobserve(entry.target);
      if (entry.target.matches('.stats')) entry.target.querySelectorAll('dt').forEach(countUp);
    });
  }, { threshold: 0.06, rootMargin: '0px 0px -7% 0px' });

  document.querySelectorAll('main h2').forEach((heading) => {
    splitWords(heading);
    seen.observe(heading);
  });

  const parts = '.block .tc, .block h3, .honest, .two>p, .big-note, .small, .rail, .rail-meter, .split>*, .gen, .table-wrap, .stats>div, .clips>figure, .flow>li, .three>div, .contact';
  const order = new Map();
  document.querySelectorAll(parts).forEach((part) => {
    const index = order.get(part.parentElement) || 0;
    order.set(part.parentElement, index + 1);
    part.classList.add('reveal');
    part.style.setProperty('--d', `${Math.min(index, 5) * 0.07}s`);
    seen.observe(part);
  });
  document.querySelectorAll('.stats').forEach((stats) => seen.observe(stats));
}

// Header: a running timecode built from the section timecodes, progress bar and active link.
const clock = document.querySelector('.clock');
const progress = document.querySelector('.progress');
const links = [...document.querySelectorAll('.top nav a')];
const parallax = [...document.querySelectorAll('[data-parallax]')];
const FPS = 25;
let marks = [];
let targets = [];

const pageTop = (element) => element.getBoundingClientRect().top + scrollY;

function timecode(seconds) {
  const pad = (value) => String(Math.floor(value)).padStart(2, '0');
  return `00:${pad(seconds / 60)}:${pad(seconds % 60)}:${pad((seconds % 1) * FPS)}`;
}

function update() {
  const room = document.documentElement.scrollHeight - innerHeight;
  const share = room > 0 ? Math.min(1, scrollY / room) : 0;
  progress.style.setProperty('--p', share);

  const probe = scrollY + share * innerHeight;
  const next = marks.findIndex((mark) => mark.top > probe);
  if (next > 0) {
    const from = marks[next - 1];
    const to = marks[next];
    clock.textContent = timecode(from.time + ((probe - from.top) / (to.top - from.top)) * (to.time - from.time));
  }

  let active = null;
  targets.forEach((target) => { if (target.top <= scrollY + innerHeight * 0.4) active = target.link; });
  links.forEach((link) => link.classList.toggle('on', link === active));

  if (!still) {
    parallax.forEach((item) => {
      const distance = Number(item.dataset.middle) - (scrollY + innerHeight / 2);
      item.style.translate = `0 ${(distance * Number(item.dataset.parallax)).toFixed(1)}px`;
    });
  }
}

function measure() {
  const end = document.documentElement.scrollHeight;
  marks = [{ top: 0, time: 0 }];
  document.querySelectorAll('.block').forEach((block) => {
    const code = block.querySelector('.tc').textContent.match(/(\d\d):(\d\d):(\d\d)/);
    marks.push({ top: pageTop(block), time: Number(code[2]) * 60 + Number(code[3]) });
  });
  marks.push({ top: end, time: marks[marks.length - 1].time + 12 });
  targets = links.map((link) => ({ link, top: pageTop(document.querySelector(link.hash)) }));
  parallax.forEach((item) => {
    item.style.translate = 'none';
    const box = item.getBoundingClientRect();
    item.dataset.middle = box.top + scrollY + box.height / 2;
  });
  update();
}

let queued = false;
addEventListener('scroll', () => {
  if (queued) return;
  queued = true;
  requestAnimationFrame(() => { queued = false; update(); });
}, { passive: true });
addEventListener('resize', measure);
addEventListener('load', measure);
new ResizeObserver(measure).observe(document.body);
measure();

// Cursor effects: magnetic buttons and images that tilt towards the pointer.
if (finePointer && !still) {
  document.querySelectorAll('.cta').forEach((button) => {
    button.addEventListener('mousemove', (event) => {
      const box = button.getBoundingClientRect();
      const x = (event.clientX - box.left - box.width / 2) * 0.18;
      const y = (event.clientY - box.top - box.height / 2) * 0.3;
      button.style.translate = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
    });
    button.addEventListener('mouseleave', () => { button.style.translate = ''; });
  });

  document.querySelectorAll('[data-tilt]').forEach((image) => {
    image.addEventListener('mousemove', (event) => {
      const box = image.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width - 0.5;
      const y = (event.clientY - box.top) / box.height - 0.5;
      image.style.setProperty('--ry', `${(x * 7).toFixed(2)}deg`);
      image.style.setProperty('--rx', `${(y * -7).toFixed(2)}deg`);
      image.style.setProperty('--sc', '1.02');
    });
    image.addEventListener('mouseleave', () => {
      ['--rx', '--ry', '--sc'].forEach((name) => image.style.removeProperty(name));
    });
  });
}
