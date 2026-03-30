const promoStats = document.getElementById('promoStats');
const promoSnapshotNotice = document.getElementById('promoSnapshotNotice');
const promoHighlightsGrid = document.getElementById('promoHighlightsGrid');
const epicFreeGrid = document.getElementById('epicFreeGrid');
const steamFreeGrid = document.getElementById('steamFreeGrid');
const epicUpcomingGrid = document.getElementById('epicUpcomingGrid');
const steamDealsGrid = document.getElementById('steamDealsGrid');
const epicDealsGrid = document.getElementById('epicDealsGrid');

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value);
}

function formatDate(value) {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function buildTimingLabel(item) {
  if (item.ends_at) {
    return `Vai ate ${formatDate(item.ends_at)}`;
  }

  if (item.starts_at) {
    return `Comeca em ${formatDate(item.starts_at)}`;
  }

  return '';
}

function dealFlag(item) {
  if (item.final_price === 'Gratis') {
    return 'Gratis agora';
  }

  if (item.starts_at) {
    return 'Em breve';
  }

  if ((item.discount_percent || 0) >= 90) {
    return 'Desconto monstro';
  }

  if ((item.discount_percent || 0) >= 80) {
    return 'Desconto forte';
  }

  return 'Vale olhar';
}

function buildEmptyCard(title, text) {
  return `
    <article class="card">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(text)}</p>
    </article>
  `;
}

function buildStoreButton(item) {
  const label = item.platform === 'steam' ? 'Abrir na Steam' : 'Abrir na Epic';
  const className = item.platform === 'steam' ? 'button-primary' : 'button-secondary';
  return `<a class="${className}" href="${item.url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

function buildPromoCard(item) {
  const image = item.image_url || 'assets/og-image.png';
  const platformLabel = item.platform === 'steam' ? 'Steam' : 'Epic Games Store';
  const safeName = escapeHtml(item.name);
  const priceBlock = item.original_price || item.final_price
    ? `
      <div class="promo-prices">
        ${item.original_price ? `<span class="promo-original">${escapeHtml(item.original_price)}</span>` : ''}
        ${item.final_price ? `<strong class="promo-final">${escapeHtml(item.final_price)}</strong>` : ''}
      </div>
    `
    : '';

  const timingLabel = buildTimingLabel(item);
  const timing = timingLabel ? `<p class="promo-meta">${escapeHtml(timingLabel)}</p>` : '';
  const promoFlag = `<span class="promo-flag">${escapeHtml(dealFlag(item))}</span>`;
  const note = item.note ? `<p class="promo-note">${escapeHtml(item.note)}</p>` : '';

  return `
    <article class="card catalog-card promo-card fade-in">
      <div class="catalog-media">
        <img src="${escapeHtml(image)}" alt="Capa do jogo ${safeName}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='assets/og-image.png';">
      </div>
      <div class="catalog-body">
        <div class="promo-topline">
          <span class="tag">${platformLabel}</span>
          ${item.discount_percent ? `<span class="promo-discount">-${item.discount_percent}%</span>` : ''}
        </div>
        <div class="promo-flag-row">${promoFlag}</div>
        <h3 class="catalog-title promo-title" title="${safeName}">${safeName}</h3>
        ${priceBlock}
        ${timing}
        ${note}
        <div class="catalog-actions">
          ${item.url ? buildStoreButton(item) : ''}
        </div>
      </div>
    </article>
  `;
}

function renderList(target, items, emptyTitle, emptyText) {
  if (!items || !items.length) {
    target.innerHTML = buildEmptyCard(emptyTitle, emptyText);
    return;
  }

  target.innerHTML = items.map(buildPromoCard).join('');
}

function sortDeals(items) {
  return [...items].sort((a, b) => {
    const discountDelta = (b.discount_percent || 0) - (a.discount_percent || 0);
    if (discountDelta !== 0) {
      return discountDelta;
    }
    return (a.name || '').localeCompare(b.name || '', 'pt-BR');
  });
}

function renderHighlights(payload) {
  const highlights = [];
  const currentEpic = payload.current_free?.epic || [];
  const currentSteam = payload.current_free?.steam || [];
  const topSteamDeals = sortDeals(payload.high_discounts?.steam || []).slice(0, 2);
  const topEpicDeals = sortDeals(payload.high_discounts?.epic || []).slice(0, 2);

  highlights.push(...currentEpic.slice(0, 2));
  highlights.push(...currentSteam.slice(0, 1));
  highlights.push(...topSteamDeals);
  highlights.push(...topEpicDeals);

  const uniqueHighlights = [];
  const seen = new Set();

  highlights.forEach(item => {
    const key = `${item.platform}:${item.url}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueHighlights.push(item);
    }
  });

  renderList(
    promoHighlightsGrid,
    uniqueHighlights.slice(0, 6),
    'Sem destaques no momento',
    'O snapshot nao retornou destaques suficientes para montar esta secao.'
  );
}

function renderSnapshotNotice(payload) {
  const threshold = payload.thresholds?.high_discount_percent || 75;
  promoSnapshotNotice.textContent = `Snapshot da Promo: ${payload.snapshot_date || '--'}. Brindes e ofertas puxados das lojas oficiais. Desconto alto aqui significa ${threshold}% ou mais.`;
}

function renderStats(payload) {
  const threshold = payload.thresholds?.high_discount_percent || 75;
  const stats = payload.stats || {};
  const totalFreeNow = (stats.epic_free_now || 0) + (stats.steam_free_now || 0);

  promoStats.innerHTML = `
    <article class="catalog-stat">
      <strong>${formatNumber(totalFreeNow)}</strong>
      <span>jogos gratis temporarios detectados agora</span>
    </article>
    <article class="catalog-stat">
      <strong>${formatNumber(stats.steam_high_discounts || 0)}</strong>
      <span>ofertas fortes na Steam (${threshold}%+)</span>
    </article>
    <article class="catalog-stat">
      <strong>${formatNumber(stats.epic_high_discounts || 0)}</strong>
      <span>ofertas fortes na Epic (${threshold}%+)</span>
    </article>
    <article class="catalog-stat">
      <strong>${payload.snapshot_date || '--'}</strong>
      <span>data do snapshot publicado</span>
    </article>
  `;
}

fetch('data/promotions/manifest.json')
  .then(response => {
    if (!response.ok) {
      throw new Error('Falha ao carregar a Promo.');
    }
    return response.json();
  })
  .then(payload => {
    renderSnapshotNotice(payload);
    renderHighlights(payload);
    renderStats(payload);
    renderList(
      epicFreeGrid,
      payload.current_free?.epic || [],
      'Nenhum brinde agora',
      'Nenhum jogo gratis temporario da Epic foi detectado neste snapshot.'
    );
    renderList(
      steamFreeGrid,
      payload.current_free?.steam || [],
      'Nenhuma promo gratuita agora',
      'Nenhum jogo com 100% de desconto temporario foi encontrado na Steam neste snapshot.'
    );
    renderList(
      epicUpcomingGrid,
      payload.upcoming_free?.epic || [],
      'Nenhum proximo brinde listado',
      'A Epic nao mostrou outro brinde futuro neste snapshot.'
    );
    renderList(
      steamDealsGrid,
      sortDeals(payload.high_discounts?.steam || []),
      'Nenhum desconto forte encontrado',
      'Nao encontramos descontos altos suficientes na Steam neste snapshot.'
    );
    renderList(
      epicDealsGrid,
      sortDeals(payload.high_discounts?.epic || []),
      'Nenhum desconto forte encontrado',
      'Nao encontramos descontos altos suficientes na Epic neste snapshot.'
    );
  })
  .catch(() => {
    const fallback = buildEmptyCard(
      'Falha ao carregar',
      'Verifique se o arquivo data/promotions/manifest.json esta publicado junto do site.'
    );
    epicFreeGrid.innerHTML = fallback;
    steamFreeGrid.innerHTML = fallback;
    epicUpcomingGrid.innerHTML = fallback;
    steamDealsGrid.innerHTML = fallback;
    epicDealsGrid.innerHTML = fallback;
    promoHighlightsGrid.innerHTML = fallback;
    promoSnapshotNotice.textContent = 'Falha ao carregar o snapshot da Promo.';
  });
