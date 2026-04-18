const POR_PAGINA = 20;
let todosOsPedidos = [];
let paginaAtual = 1;
let refreshTimer = null;
let statusTimer = null;

// ── INICIALIZAÇÃO ──
document.addEventListener('DOMContentLoaded', () => {
  carregarTudo();
  configurarFiltros();
  iniciarAutoRefresh();
  iniciarMonitorStatus();
});

function configurarFiltros() {
  document.getElementById('busca').addEventListener('input', () => {
    paginaAtual = 1;
    renderizarTabela();
  });
  document.getElementById('filtro-filial').addEventListener('change', () => {
    paginaAtual = 1;
    renderizarTabela();
  });
}

function iniciarAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(carregarTudo, 30 * 1000);
}

function iniciarMonitorStatus() {
  atualizarStatus();
  clearInterval(statusTimer);
  statusTimer = setInterval(atualizarStatus, 8000);
}

async function atualizarStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const filiais = Object.values(data);

    const dot = document.getElementById('status-dot');
    const texto = document.getElementById('status-texto');

    const coletando = filiais.some(f => f.coletando);
    const erro = filiais.some(f => f.estado === 'erro');

    dot.style.background = erro ? '#FF4D4D' : coletando ? '#FFD100' : '#22C55E';
    dot.style.animation = coletando ? 'pulse 0.8s infinite' : 'pulse 2s infinite';

    if (erro) {
      texto.textContent = 'Erro na coleta';
    } else if (coletando) {
      const ativas = filiais.filter(f => f.coletando).map(f => f.estado).join(' | ');
      texto.textContent = ativas;
    } else {
      const pipeline = data.pipeline || {};
      const ultima = pipeline.ultima_atualizacao || '—';
      texto.textContent = `Última coleta: ${ultima}`;
    }

    if (coletando) {
      await carregarPedidos();
      await carregarStats();
    }
  } catch (e) {
    // silencioso
  }
}

// ── CARREGAMENTO ──
async function carregarTudo() {
  atualizarTimestamp();
  await Promise.all([carregarStats(), carregarPedidos()]);
}

async function carregarStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.total;
    document.getElementById('stat-valor').textContent = formatarMoeda(data.valor_total);

    const filiais = data.por_filial || {};
    document.getElementById('stat-rigarr').textContent = filiais['Rigarr'] ?? 0;
    document.getElementById('stat-castas').textContent = filiais['Castas'] ?? 0;
  } catch (e) {
    console.error('Erro ao carregar stats:', e);
  }
}

async function carregarPedidos() {
  mostrarLoading(true);
  try {
    const res = await fetch('/api/pedidos');
    todosOsPedidos = await res.json();
    paginaAtual = 1;
    renderizarTabela();
  } catch (e) {
    console.error('Erro ao carregar pedidos:', e);
    mostrarErro();
  } finally {
    mostrarLoading(false);
  }
}

// ── FILTROS E RENDERIZAÇÃO ──
function pedidosFiltrados() {
  const busca = document.getElementById('busca').value.toLowerCase().trim();
  const filial = document.getElementById('filtro-filial').value;

  return todosOsPedidos.filter(p => {
    const matchFilial = !filial || p.filial === filial;
    const matchBusca = !busca || [
      p['Numero Pedido'], p['Nome Comercial'], p['Documento'],
      p['Centro de Distribuição'], p['Responsavel'], p['Cod Cliente']
    ].some(v => (v || '').toLowerCase().includes(busca));
    return matchFilial && matchBusca;
  });
}

function renderizarTabela() {
  const filtrados = pedidosFiltrados();
  const totalFiltrados = filtrados.length;
  const inicio = (paginaAtual - 1) * POR_PAGINA;
  const pagina = filtrados.slice(inicio, inicio + POR_PAGINA);

  const tbody = document.getElementById('tbody');

  if (totalFiltrados === 0) {
    tbody.innerHTML = `
      <tr><td colspan="8">
        <div class="empty-state">
          <div class="icon">📦</div>
          <p>Nenhum pedido encontrado</p>
        </div>
      </td></tr>`;
    renderizarPaginacao(0, 0);
    return;
  }

  tbody.innerHTML = pagina.map(p => `
    <tr onclick="abrirModal('${p['Numero Pedido']}')">
      <td>
        <span class="pedido-num">${p['Numero Pedido']}</span>
        <div class="td-muted">${formatarData(p['Data Pedido'])}</div>
      </td>
      <td>
        <div>${esc(p['Nome Comercial']) || '—'}</div>
        <div class="td-muted">${formatarFilial(p.filial)}${p['Cod Cliente'] ? ` &nbsp;<span style="font-family:monospace;font-size:11px">${esc(p['Cod Cliente'])}</span>` : ''}</div>
      </td>
      <td class="td-muted">${formatarDoc(p['Documento'])}</td>
      <td class="td-muted" style="font-size:12px">${esc(p['Centro de Distribuição']) || '—'}</td>
      <td class="td-muted">${formatarData(p['Data Entrega'])}</td>
      <td><span class="badge ${badgePagamento(p['Forma de Pagamento'])}">${formatarPagamento(p['Forma de Pagamento'])}</span></td>
      <td class="valor">${formatarTotal(p['Total Pedido'])}</td>
      <td><button class="btn-detail" onclick="event.stopPropagation(); abrirModal('${p['Numero Pedido']}')">Ver</button></td>
    </tr>
  `).join('');

  renderizarPaginacao(totalFiltrados, inicio);
}

function renderizarPaginacao(total, inicio) {
  const pag = document.getElementById('pagination');
  if (total === 0) { pag.innerHTML = ''; return; }

  const totalPags = Math.ceil(total / POR_PAGINA);
  const fim = Math.min(inicio + POR_PAGINA, total);

  let html = `<span>${inicio + 1}–${fim} de ${total}</span>`;
  html += `<button class="page-btn" onclick="irPagina(${paginaAtual - 1})" ${paginaAtual === 1 ? 'disabled' : ''}>‹</button>`;

  const janela = paginasVisiveis(paginaAtual, totalPags);
  janela.forEach(p => {
    if (p === '…') {
      html += `<span style="color:var(--text-muted)">…</span>`;
    } else {
      html += `<button class="page-btn ${p === paginaAtual ? 'active' : ''}" onclick="irPagina(${p})">${p}</button>`;
    }
  });

  html += `<button class="page-btn" onclick="irPagina(${paginaAtual + 1})" ${paginaAtual === totalPags ? 'disabled' : ''}>›</button>`;
  pag.innerHTML = html;
}

function paginasVisiveis(atual, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pags = new Set([1, total, atual, atual - 1, atual + 1].filter(p => p >= 1 && p <= total));
  const sorted = [...pags].sort((a, b) => a - b);
  const result = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) result.push('…');
    result.push(p);
    prev = p;
  }
  return result;
}

function irPagina(n) {
  const totalPags = Math.ceil(pedidosFiltrados().length / POR_PAGINA);
  paginaAtual = Math.max(1, Math.min(n, totalPags));
  renderizarTabela();
  document.querySelector('.table-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── MODAL ──
async function abrirModal(numero) {
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal-body').innerHTML = `<div class="loading"><div class="spinner"></div>Carregando...</div>`;

  try {
    const res = await fetch(`/api/pedidos/${numero}`);
    const p = await res.json();

    document.getElementById('modal-titulo').innerHTML =
      `Pedido <span>#${p['Numero Pedido']}</span>`;

    document.getElementById('modal-body').innerHTML = `
      <div class="modal-section">
        <h3>Informações do Pedido</h3>
        <div class="info-grid">
          ${campo('Status', badgeStatus(p['Status']))}
          ${campo('Filial', formatarFilial(p.filial))}
          ${campo('Centro de Distribuição', p['Centro de Distribuição'])}
          ${campo('Responsável', p['Responsavel'])}
          ${campo('Data do Pedido', formatarData(p['Data Pedido']))}
          ${campo('Data de Entrega', formatarData(p['Data Entrega']))}
          ${campo('Forma de Pagamento', p['Forma de Pagamento'])}
          ${campo('Total', `<strong style="color:var(--yellow)">${formatarTotal(p['Total Pedido'])}</strong>`)}
        </div>
      </div>

      <div class="modal-section">
        <h3>Cliente</h3>
        <div class="info-grid">
          ${campo('Nome Comercial', p['Nome Comercial'])}
          ${campo('Documento', formatarDoc(p['Documento']))}
          ${campo('Inscrição Estadual', p['IE'])}
          ${campo('Cod Cliente', p['Cod Cliente'])}
          ${campo('ID do Negócio', p['ID do negócio'])}
          ${campo('ID da Conta', p['ID da conta do cliente'])}
        </div>
      </div>

      <div class="modal-section">
        <h3>Contato</h3>
        <div class="info-grid">
          ${campo('Telefone 1', p['Telefone 1'])}
          ${campo('Telefone 2', p['Telefone 2'])}
          ${campo('Email 1', p['Email 1'])}
          ${campo('Email 2', p['Email 2'])}
        </div>
      </div>

      <div class="modal-section">
        <h3>Endereço de Entrega</h3>
        <div class="info-grid">
          ${campo('Endereço', p['Endereço de Entrega'])}
          ${campo('Cidade/UF', p['Cidade/UF'])}
          ${campo('CEP', p['CEP'])}
        </div>
      </div>

      <div class="modal-section">
        <h3>Itens do Pedido (${(p.itens || []).length} produto${(p.itens || []).length !== 1 ? 's' : ''})</h3>
        ${renderizarItens(p.itens)}
      </div>
    `;
  } catch (e) {
    document.getElementById('modal-body').innerHTML =
      `<p style="color:var(--danger); padding:24px">Erro ao carregar pedido.</p>`;
  }
}

function fecharModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) fecharModal();
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') fecharModal();
});

function renderizarItens(itens) {
  if (!itens || itens.length === 0) return '<p style="color:var(--text-muted);font-size:13px">Sem itens cadastrados.</p>';
  return `
    <div style="overflow-x:auto">
      <table class="items-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Produto</th>
            <th style="text-align:right">Qtd Pedida</th>
            <th style="text-align:right">Qtd Preparar</th>
            <th style="text-align:right">Preço</th>
          </tr>
        </thead>
        <tbody>
          ${itens.map(i => `
            <tr>
              <td style="font-family:monospace;font-size:12px;color:var(--text-muted)">${esc(i['SKU'])}</td>
              <td>${esc(i['Nome do Produto'])}</td>
              <td style="text-align:right">${esc(i['Quantidade Pedida'])}</td>
              <td style="text-align:right">${esc(i['Quantidade Preparar'])}</td>
              <td style="text-align:right;font-weight:600">${esc(i['Preço'])}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

// ── HELPERS UI ──
function campo(label, value) {
  return `<div class="info-item">
    <label>${label}</label>
    <span>${value || '—'}</span>
  </div>`;
}

function mostrarLoading(show) {
  document.getElementById('loading').style.display = show ? 'block' : 'none';
  document.getElementById('table-container').style.display = show ? 'none' : 'block';
}

function mostrarErro() {
  document.getElementById('tbody').innerHTML =
    `<tr><td colspan="8"><div class="empty-state"><div class="icon">⚠️</div><p>Erro ao carregar os pedidos.</p></div></td></tr>`;
}

function atualizarTimestamp() {
  const el = document.getElementById('ultimo-update');
  if (el) el.textContent = new Date().toLocaleTimeString('pt-BR');
}

// ── FORMATAÇÃO ──
function formatarData(d) {
  if (!d) return '—';
  const str = d.split(' ')[0];
  const [y, m, dia] = str.split('-');
  if (dia) return `${dia}/${m}/${y}`;
  const parts = str.split('/');
  return parts.length === 3 ? str : d;
}

function formatarMoeda(v) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0);
}

function formatarTotal(val) {
  if (!val) return '—';
  const num = parseFloat(val.replace('$', '').replace(/\./g, '').replace(',', '.'));
  if (isNaN(num)) return val;
  return formatarMoeda(num);
}

function formatarDoc(doc) {
  if (!doc) return '—';
  return doc.replace('CNPJ: ', '').replace('CPF: ', '');
}

function formatarPagamento(p) {
  if (!p) return '—';
  if (p.toLowerCase().includes('pix')) return 'PIX';
  if (p.toLowerCase().includes('dinheiro')) return 'Dinheiro';
  if (p.toLowerCase().includes('cartão') || p.toLowerCase().includes('cartao')) return 'Cartão';
  if (p.toLowerCase().includes('boleto')) return 'Boleto';
  return p.split(' ')[0];
}

function formatarFilial(f) {
  const cls = f === 'Rigarr' ? 'filial-rigarr' : 'filial-castas';
  return `<span class="filial-tag ${cls}">${f}</span>`;
}

function badgePagamento(p) {
  if (!p) return 'badge-gray';
  const lower = p.toLowerCase();
  if (lower.includes('pix')) return 'badge-green';
  if (lower.includes('dinheiro')) return 'badge-blue';
  if (lower.includes('cartão') || lower.includes('cartao')) return 'badge-yellow';
  return 'badge-gray';
}

function badgeStatus(s) {
  if (!s) return '<span class="badge badge-gray">—</span>';
  const lower = s.toLowerCase();
  let cls = 'badge-yellow';
  if (lower.includes('preparado') || lower.includes('entregue')) cls = 'badge-green';
  else if (lower.includes('cancelad') || lower.includes('recusad')) cls = 'badge-red';
  return `<span class="badge ${cls}">${esc(s)}</span>`;
}

function esc(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
