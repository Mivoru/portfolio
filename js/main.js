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
