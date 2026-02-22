let editingId = null;
let lastProducts = [];

function setError(id, msg) {
  document.getElementById(id).textContent = msg || '';
}

function getFormPayload() {
  const name = document.getElementById('name').value.trim();
  const sku = document.getElementById('sku').value.trim();
  const category = document.getElementById('category').value.trim();
  const supplier = document.getElementById('supplier').value.trim();

  const quantity = Number(document.getElementById('quantity').value);
  const min_stock = Number(document.getElementById('min_stock').value);
  const cost = Number(document.getElementById('cost').value);
  const price = Number(document.getElementById('price').value);

  if (!name) throw new Error('Nome é obrigatório');
  if (!sku) throw new Error('SKU é obrigatório');
  if (!Number.isFinite(quantity) || quantity < 0) throw new Error('Quantidade inválida');
  if (!Number.isFinite(min_stock) || min_stock < 0) throw new Error('Estoque mínimo inválido');
  if (!Number.isFinite(cost) || cost < 0) throw new Error('Custo inválido');
  if (!Number.isFinite(price) || price < 0) throw new Error('Preço inválido');

  return {
    name,
    sku,
    category,
    supplier,
    quantity,
    min_stock,
    cost: cost.toFixed(2),
    price: price.toFixed(2),
  };
}

function fillForm(p) {
  document.getElementById('name').value = p.name || '';
  document.getElementById('sku').value = p.sku || '';
  document.getElementById('category').value = p.category || '';
  document.getElementById('supplier').value = p.supplier || '';
  document.getElementById('quantity').value = p.quantity ?? 0;
  document.getElementById('min_stock').value = p.min_stock ?? 0;
  document.getElementById('cost').value = p.cost ?? 0;
  document.getElementById('price').value = p.price ?? 0;
}

function clearForm() {
  editingId = null;
  fillForm({ quantity: 0, min_stock: 0, cost: 0, price: 0 });
  document.getElementById('editing').style.display = 'none';
  setError('formError', '');
}

async function loadHealth() {
  const el = document.getElementById('health');
  try {
    const r = await fetch('/health');
    const data = await r.json();
    el.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    el.textContent = String(e);
  }
}

function currentQuery() {
  const search = document.getElementById('search').value.trim();
  const category = document.getElementById('filterCategory').value.trim();
  const supplier = document.getElementById('filterSupplier').value.trim();
  const order_by = document.getElementById('orderBy').value;
  const order_dir = document.getElementById('orderDir').value;
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (category) params.set('category', category);
  if (supplier) params.set('supplier', supplier);
  params.set('order_by', order_by);
  params.set('order_dir', order_dir);

  return params;
}

async function loadProducts() {
  setError('listError', '');
  const tbody = document.getElementById('products');
  tbody.innerHTML = '';

  try {
    const params = currentQuery();
    const r = await fetch(`/api/products?${params.toString()}`);
    if (!r.ok) {
      const msg = await r.text();
      throw new Error(msg);
    }
    const products = await r.json();
    lastProducts = products;
    refreshMovementProductSelect();

    const onlyLow = document.getElementById('onlyLowStock')?.checked;

    for (const p of products) {
      const low = Boolean(p.low_stock);
      if (onlyLow && !low) continue;

      const tr = document.createElement('tr');
      if (low) tr.classList.add('low-stock');

      const badge = low
        ? '<span class="badge badge-low">Estoque baixo</span>'
        : '<span class="badge badge-ok">OK</span>';

      tr.innerHTML = `
        <td>${escapeHtml(p.name)}</td>
        <td><code>${escapeHtml(p.sku)}</code></td>
        <td>${escapeHtml(p.category || '')}</td>
        <td>${escapeHtml(p.supplier || '')}</td>
        <td>${p.quantity}</td>
        <td>${p.min_stock}</td>
        <td>${badge}</td>
        <td>${p.cost}</td>
        <td>${p.price}</td>
        <td>
          <button data-action="edit">Editar</button>
          <button data-action="delete" style="margin-left:0.25rem">Excluir</button>
        </td>
      `;

      tr.querySelector('[data-action="edit"]').addEventListener('click', () => {
        editingId = p.id;
        fillForm(p);
        document.getElementById('editing').style.display = 'inline-block';
        setError('formError', '');
      });

      tr.querySelector('[data-action="delete"]').addEventListener('click', async () => {
        if (!confirm(`Excluir produto ${p.name}?`)) return;
        const del = await fetch(`/api/products/${p.id}`, { method: 'DELETE' });
        if (!del.ok && del.status !== 204) {
          setError('listError', await del.text());
          return;
        }
        await loadProducts();
        if (editingId === p.id) clearForm();
      });

      tbody.appendChild(tr);
    }
  } catch (e) {
    setError('listError', String(e));
  }
}

async function saveProduct() {
  setError('formError', '');
  let payload;
  try {
    payload = getFormPayload();
  } catch (e) {
    setError('formError', String(e.message || e));
    return;
  }

  const url = editingId ? `/api/products/${editingId}` : '/api/products';
  const method = editingId ? 'PUT' : 'POST';

  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!r.ok) {
    let msg = '';
    try {
      const data = await r.json();
      msg = data.detail ? JSON.stringify(data.detail) : JSON.stringify(data);
    } catch {
      msg = await r.text();
    }
    setError('formError', msg || 'Erro ao salvar');
    return;
  }

  clearForm();
  await loadProducts();
  await loadMovements();
}

function refreshMovementProductSelect() {
  const sel = document.getElementById('movementProduct');
  if (!sel) return;

  const current = sel.value;
  sel.innerHTML = '';

  for (const p of lastProducts) {
    const opt = document.createElement('option');
    opt.value = String(p.id);
    opt.textContent = `${p.name} (${p.sku}) — qtd ${p.quantity}`;
    sel.appendChild(opt);
  }

  if (current && [...sel.options].some((o) => o.value === current)) {
    sel.value = current;
  }
}

function toInputDatetimeValue(d) {
  // datetime-local expects YYYY-MM-DDTHH:mm
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function getMovementPayload() {
  const type = document.getElementById('movementType').value;
  const qty = Number(document.getElementById('movementQty').value);
  const at = document.getElementById('movementAt').value;
  const note = document.getElementById('movementNote').value.trim();

  if (!Number.isFinite(qty) || qty < 1) throw new Error('Quantidade inválida');

  // Build ISO string if user set datetime-local
  const occurred_at = at ? new Date(at).toISOString() : null;

  return {
    type,
    quantity: qty,
    occurred_at,
    note,
  };
}

async function loadMovements() {
  setError('movementError', '');
  const sel = document.getElementById('movementProduct');
  const tbody = document.getElementById('movementHistory');
  if (!sel || !tbody) return;

  tbody.innerHTML = '';
  const productId = sel.value;
  if (!productId) return;

  try {
    const r = await fetch(`/api/products/${productId}/movements`);
    if (!r.ok) throw new Error(await r.text());
    const movements = await r.json();

    for (const m of movements) {
      const tr = document.createElement('tr');
      const when = new Date(m.occurred_at).toLocaleString();
      tr.innerHTML = `
        <td>${escapeHtml(when)}</td>
        <td>${m.type === 'entry' ? 'Entrada' : 'Saída'}</td>
        <td>${m.quantity}</td>
        <td>${escapeHtml(m.note || '')}</td>
      `;
      tbody.appendChild(tr);
    }
  } catch (e) {
    setError('movementError', String(e));
  }
}

async function loadLowStock() {
  const tbody = document.getElementById('lowStockTbody');
  if (!tbody) return;

  tbody.innerHTML = '';
  try {
    const r = await fetch('/api/low-stock?order_by=quantity&order_dir=asc');
    if (!r.ok) throw new Error(await r.text());
    const products = await r.json();

    if (products.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="muted">Nenhum item com estoque baixo.</td>';
      tbody.appendChild(tr);
      return;
    }

    for (const p of products) {
      const tr = document.createElement('tr');
      tr.classList.add('low-stock');
      tr.innerHTML = `
        <td>${escapeHtml(p.name)}</td>
        <td><code>${escapeHtml(p.sku)}</code></td>
        <td>${p.quantity}</td>
        <td>${p.min_stock}</td>
        <td><span class="badge badge-low">Estoque baixo</span></td>
      `;
      tbody.appendChild(tr);
    }
  } catch (e) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="5" class="error">${escapeHtml(String(e))}</td>`;
    tbody.appendChild(tr);
  }
}

async function saveMovement() {
  setError('movementError', '');
  const sel = document.getElementById('movementProduct');
  if (!sel || !sel.value) {
    setError('movementError', 'Selecione um produto');
    return;
  }

  let payload;
  try {
    payload = getMovementPayload();
  } catch (e) {
    setError('movementError', String(e.message || e));
    return;
  }

  const r = await fetch(`/api/products/${sel.value}/movements`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!r.ok) {
    let msg = '';
    try {
      const data = await r.json();
      msg = data.detail ? JSON.stringify(data.detail) : JSON.stringify(data);
    } catch {
      msg = await r.text();
    }
    setError('movementError', msg || 'Erro ao registrar');
    return;
  }

  // refresh quantities + history
  await loadProducts();
  await loadMovements();
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

document.getElementById('save').addEventListener('click', saveProduct);
document.getElementById('cancel').addEventListener('click', clearForm);
document.getElementById('refresh').addEventListener('click', loadProducts);
document.getElementById('onlyLowStock')?.addEventListener('change', loadProducts);

document.getElementById('lowStockRefresh')?.addEventListener('click', loadLowStock);

document.getElementById('movementSave')?.addEventListener('click', saveMovement);
document.getElementById('movementRefresh')?.addEventListener('click', loadMovements);
document.getElementById('movementProduct')?.addEventListener('change', loadMovements);

for (const id of ['search', 'filterCategory', 'filterSupplier', 'orderBy', 'orderDir', 'onlyLowStock']) {
  document.getElementById(id).addEventListener('change', loadProducts);
}
document.getElementById('search').addEventListener('input', debounce(loadProducts, 250));

function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

loadHealth();
loadProducts().then(() => {
  const at = document.getElementById('movementAt');
  if (at && !at.value) at.value = toInputDatetimeValue(new Date());
  loadMovements();
});
clearForm();
