/* Optional visual effects. The app remains fully usable without this file. */
(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: no-preference)');
  const pointer = window.matchMedia('(pointer: fine) and (hover: hover)');
  const enabled = () => motion.matches && pointer.matches;
  const initializedCards = new WeakSet();
  let stopCursor = null;

  function initGlassCards() {
    if (!enabled()) return;
    document.querySelectorAll('.glass-card').forEach(card => {
      if (initializedCards.has(card)) return;
      initializedCards.add(card);
      const spotlight = document.createElement('span');
      spotlight.className = 'glass-spotlight';
      spotlight.setAttribute('aria-hidden', 'true');
      card.append(spotlight);
      let nextX = -140, nextY = -140, frame = 0;
      card.addEventListener('pointermove', event => {
        const rect = card.getBoundingClientRect();
        nextX = event.clientX - rect.left - 140;
        nextY = event.clientY - rect.top - 140;
        if (!frame) frame = requestAnimationFrame(() => {
          spotlight.style.transform = `translate3d(${nextX}px, ${nextY}px, 0)`;
          frame = 0;
        });
      }, {passive: true});
    });
  }

  function createCustomCursor() {
    const dot = document.createElement('span');
    const ring = document.createElement('span');
    dot.className = 'cursor-dot'; ring.className = 'cursor-ring';
    dot.setAttribute('aria-hidden', 'true'); ring.setAttribute('aria-hidden', 'true');
    document.body.append(dot, ring);
    document.body.classList.add('has-custom-cursor');
    let targetX = -100, targetY = -100, ringX = -100, ringY = -100;
    let visible = false, hovering = false, pressed = false, magnet = null, frame = 0;

    function onMove(event) {
      targetX = event.clientX; targetY = event.clientY; visible = true;
      const hit = event.target.closest?.('button, a, input, select, .glass-card');
      hovering = Boolean(hit); magnet = hit ? hit.getBoundingClientRect() : null;
      ring.classList.toggle('is-hovering', hovering);
      dot.style.opacity = '1'; ring.style.opacity = '1';
      if (!frame) frame = requestAnimationFrame(tick);
    }
    function onLeave() {
      visible = false; dot.style.opacity = '0'; ring.style.opacity = '0';
      cancelAnimationFrame(frame); frame = 0;
    }
    function onDown() { pressed = true; ring.classList.add('is-pressed'); }
    function onUp() { pressed = false; ring.classList.remove('is-pressed'); }
    function tick() {
      frame = 0;
      if (visible) {
        const magneticX = magnet ? targetX * .84 + (magnet.left + magnet.width / 2) * .16 : targetX;
        const magneticY = magnet ? targetY * .84 + (magnet.top + magnet.height / 2) * .16 : targetY;
        ringX += (magneticX - ringX) * .22;
        ringY += (magneticY - ringY) * .22;
        const scale = pressed ? .72 : hovering ? 1.55 : 1;
        dot.style.transform = `translate3d(${targetX - 2.5}px, ${targetY - 2.5}px, 0)`;
        ring.style.transform = `translate3d(${ringX - 15}px, ${ringY - 15}px, 0) scale(${scale})`;
        frame = requestAnimationFrame(tick);
      }
    }
    document.addEventListener('pointermove', onMove, {passive: true});
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('pointerup', onUp);
    document.documentElement.addEventListener('pointerleave', onLeave);
    window.addEventListener('blur', onLeave);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('pointerup', onUp);
      document.documentElement.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('blur', onLeave);
      document.body.classList.remove('has-custom-cursor');
      dot.remove(); ring.remove();
    };
  }

  function syncEffects() {
    if (enabled()) {
      if (!stopCursor) stopCursor = createCustomCursor();
      initGlassCards();
    } else if (stopCursor) {
      stopCursor(); stopCursor = null;
    }
  }
  motion.addEventListener('change', syncEffects);
  pointer.addEventListener('change', syncEffects);
  window.CampusEffects = {initGlassCards};
  syncEffects();
})();
