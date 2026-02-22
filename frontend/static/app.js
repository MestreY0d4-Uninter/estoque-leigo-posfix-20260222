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

async function loadNotes() {
  const ul = document.getElementById('notes');
  ul.innerHTML = '';
  const r = await fetch('/api/notes');
  const notes = await r.json();
  for (const n of notes) {
    const li = document.createElement('li');
    li.textContent = `#${n.id} - ${n.content}`;
    ul.appendChild(li);
  }
}

async function saveNote() {
  const input = document.getElementById('note');
  const content = input.value.trim();
  if (!content) return;

  await fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  input.value = '';
  await loadNotes();
}

document.getElementById('save').addEventListener('click', saveNote);

loadHealth();
loadNotes();
