import htmx from 'htmx.org';
import './style.css';

window.htmx = htmx;

// Boosted navigation swaps the body only, so the head has to be carried across by hand.
// htmx 4 fires after:swap as soon as the new body is in place and after:process once it
// has initialised it; syncing on both keeps the description and canonical in step with
// the title, including on history restores, which go through the same swap.
function syncHead() {
  const main = document.querySelector('main[data-description]');
  if (!main) return;
  document.querySelector('meta[name="description"]').content = main.dataset.description;
  document.querySelector('link[rel="canonical"]').href = main.dataset.canonical;
}

document.addEventListener('htmx:after:swap', syncHead);
document.addEventListener('htmx:after:process', syncHead);
syncHead();
