// Live post template: the viewer edits the copy, the canvas redraws, PNG downloads locally.
// Everything stays in the browser. Output always carries the concept label.
(() => {
  const canvas = document.getElementById('gen-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const form = document.getElementById('gen-form');
  const FORMATS = { post: [1080, 1350], square: [1080, 1080], story: [1080, 1920] };
  const THEMES = {
    orange: { bg: '#FC5E22', fg: '#101B2B', hi: '#FFFFFF' },
    blue: { bg: '#006FF7', fg: '#FFFFFF', hi: '#FFCCF7' },
    navy: { bg: '#1F2F45', fg: '#FFFFFF', hi: '#FC5E22' },
    pink: { bg: '#FF78E6', fg: '#101B2B', hi: '#101B2B' },
  };
  const FONT = '800 SIZEpx Bricolage, system-ui, sans-serif';

  // Tight tracking matches the static posts. Browsers without letterSpacing just ignore it.
  function setFont(size) {
    ctx.font = FONT.replace('SIZE', size);
    ctx.letterSpacing = `${-size * 0.04}px`;
  }

  function lines(text, width) {
    const out = [];
    for (const para of text.split('\n')) {
      let line = '';
      for (const word of para.split(/\s+/).filter(Boolean)) {
        const next = line ? `${line} ${word}` : word;
        if (ctx.measureText(next).width > width && line) { out.push(line); line = word; } else line = next;
      }
      out.push(line);
    }
    return out;
  }

  // Largest size where the headline fits both the width and its share of the height.
  function fit(text, width, height) {
    for (let size = 320; size >= 44; size -= 4) {
      setFont(size);
      const wrapped = lines(text, width);
      const widest = Math.max(...wrapped.map((l) => ctx.measureText(l).width));
      if (widest <= width && wrapped.length * size * 0.98 <= height) return { size, wrapped };
    }
    setFont(44);
    return { size: 44, wrapped: lines(text, width) };
  }

  function bracket(x, y, w, h, color) {
    const arm = 44;
    ctx.strokeStyle = color;
    ctx.lineWidth = 10;
    [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([px, py, sx, sy]) => {
      ctx.beginPath();
      ctx.moveTo(px + arm * sx, py);
      ctx.lineTo(px, py);
      ctx.lineTo(px, py + arm * sy);
      ctx.stroke();
    });
  }

  function draw() {
    const data = new FormData(form);
    const [W, H] = FORMATS[data.get('format')];
    const theme = THEMES[data.get('theme')];
    canvas.width = W;
    canvas.height = H;
    const pad = 72;
    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, W, H);
    ctx.textBaseline = 'top';
    let y = pad;
    const stat = String(data.get('stat') || '').trim();
    if (stat) {
      let statSize = 150;
      setFont(statSize);
      const room = W - pad * 2 - 40;
      const raw = ctx.measureText(stat).width;
      if (raw > room) { statSize = Math.floor(statSize * room / raw); setFont(statSize); }
      ctx.fillStyle = theme.hi;
      ctx.fillText(stat, pad + 20, y + 95 - statSize / 2);
      bracket(pad, y, ctx.measureText(stat).width + 40, 190, theme.fg);
      y += 240;
    }
    const sub = String(data.get('sub') || '').trim();
    const subSize = 42;
    ctx.letterSpacing = '-0.8px';
    ctx.font = `500 ${subSize}px Bricolage, system-ui, sans-serif`;
    const subLines = sub ? lines(sub, W - pad * 2) : [];
    const footTop = H - 120;
    const subTop = footTop - 40 - subLines.length * subSize * 1.18;
    const head = String(data.get('head') || ' ').trim() || ' ';
    const { size, wrapped } = fit(head, W - pad * 2, subTop - y - 30);
    setFont(size);
    ctx.fillStyle = theme.fg;
    wrapped.forEach((line, i) => ctx.fillText(line, pad, y + i * size * 0.98));
    ctx.letterSpacing = '-0.8px';
    ctx.font = `500 ${subSize}px Bricolage, system-ui, sans-serif`;
    subLines.forEach((line, i) => ctx.fillText(line, pad, subTop + i * subSize * 1.18));
    setFont(46);
    ctx.fillText('digitoo', pad, footTop + 20);
    ctx.letterSpacing = '0.8px';
    ctx.font = '500 19px Plex, monospace';
    ctx.textAlign = 'right';
    ctx.fillText('NEOFICIÁLNÍ KONCEPT', W - pad, footTop + 40);
    ctx.textAlign = 'left';
  }

  form.addEventListener('input', draw);
  form.addEventListener('submit', (event) => event.preventDefault());
  document.getElementById('gen-save').addEventListener('click', () => {
    const link = document.createElement('a');
    link.download = 'koncept-prispevek.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  });
  Promise.all([
    document.fonts.load('800 80px Bricolage', 'ěščřžýáíé'),
    document.fonts.load('500 40px Bricolage', 'ěščřžýáíé'),
    document.fonts.load('500 19px Plex', 'ÁÍ'),
  ]).finally(draw);
})();
