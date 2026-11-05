// Respect reduced motion: the hero loop stays on its poster frame.
if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const hero = document.querySelector('.hero-video video');
  hero.removeAttribute('autoplay');
  hero.pause();
  hero.controls = true;
}

// Only one video with sound plays at a time.
const players = [...document.querySelectorAll('video[controls]')];
players.forEach((video) => video.addEventListener('play', () => {
  players.filter((other) => other !== video).forEach((other) => other.pause());
}));

// Image rails: slow drift on their own, and with a mouse the rail follows the cursor.
// Left of centre pans left, right of centre pans right, the middle stays still.
// Speed grows steeply towards the edge, and the rail brakes before it hits an end.
// Touch keeps native swiping. Reduced motion keeps manual scrolling only.
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
const mouse = matchMedia('(hover: hover) and (pointer: fine)').matches;

document.querySelectorAll('[data-pan]').forEach((rail) => {
  const meter = document.createElement('div');
  meter.className = 'rail-meter';
  meter.setAttribute('aria-hidden', 'true');
  const bar = meter.appendChild(document.createElement('i'));
  rail.after(meter);

  const DRIFT = 26;      // px per second on its own
  const MAX_SPEED = 2600; // px per second at the rail's edge
  let pos = 0;
  let dir = 1;
  let hover = null;      // cursor position from -1 to 1 while hovering
  let speed = 0;
  let visible = false;
  let heldUntil = 0;     // manual scrolling pauses the drift
  let last = 0;

  function paint() {
    const share = rail.clientWidth / rail.scrollWidth;
    meter.style.visibility = share >= 1 ? 'hidden' : 'visible';
    bar.style.setProperty('--w', `${share * 100}%`);
    bar.style.setProperty('--x', `${(rail.scrollLeft / rail.clientWidth) * 100}%`);
  }

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const max = rail.scrollWidth - rail.clientWidth;
    let target = 0;
    if (hover !== null) {
      const dead = 0.1;
      const full = 0.92; // cursor position where top speed is reached
      const push = Math.min(1, Math.max(0, Math.abs(hover) - dead) / (full - dead));
      target = Math.sign(hover) * (0.12 * push + 0.88 * push ** 3) * MAX_SPEED;
    } else if (!calm && now > heldUntil) {
      target = dir * DRIFT;
    }
    speed += (target - speed) * (1 - Math.exp(-dt * (hover === null ? 4 : 9)));
    if (max > 0 && Math.abs(speed) > 0.5) {
      const room = speed > 0 ? max - pos : pos;
      const brake = Math.min(1, 0.1 + room / 160);
      pos = Math.max(0, Math.min(max, pos + speed * brake * dt));
      if (pos <= 0) dir = 1;
      if (pos >= max) dir = -1;
      // scrollLeft snaps to whole pixels, so the remainder moves the images instead.
      const whole = Math.round(pos);
      rail.scrollLeft = whole;
      rail.style.setProperty('--frac', `${whole - pos}px`);
    }
    paint();
    if (visible) requestAnimationFrame(frame);
  }

  new IntersectionObserver(([entry]) => {
    const wasVisible = visible;
    visible = entry.isIntersecting;
    if (visible && !wasVisible) {
      last = performance.now();
      requestAnimationFrame(frame);
    }
  }).observe(rail);

  if (mouse && !calm) {
    rail.addEventListener('mousemove', (event) => {
      const box = rail.getBoundingClientRect();
      hover = ((event.clientX - box.left) / box.width) * 2 - 1;
    });
    rail.addEventListener('mouseleave', () => { hover = null; });
  }

  // Wheel, swipe and arrow keys take over from the animation for a moment.
  const hold = () => { heldUntil = performance.now() + 2500; speed = 0; };
  ['wheel', 'touchstart', 'keydown'].forEach((type) => rail.addEventListener(type, hold, { passive: true }));
  rail.addEventListener('scroll', () => {
    if (Math.abs(rail.scrollLeft - pos) > 2) {
      pos = rail.scrollLeft;
      rail.style.setProperty('--frac', '0px');
    }
    paint();
  }, { passive: true });
  addEventListener('resize', paint);
  paint();
});
