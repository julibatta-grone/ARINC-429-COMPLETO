const instrumentRows = document.querySelector("#instrument-rows");
const sendRows = document.querySelector("#send-rows");
const instrumentSelect = document.querySelector("#send-instrument");
const instrumentCount = document.querySelector("#instrument-count");
const notice = document.querySelector("#notice");
const dialog = document.querySelector("#instrument-dialog");
const instrumentForm = document.querySelector("#instrument-form");
const sendForm = document.querySelector("#send-form");

let instruments = [];
let sends = [];

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // La respuesta de error no siempre incluye JSON.
    }
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(", ") : message);
  }
  return response.status === 204 ? null : response.json();
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
  window.clearTimeout(showNotice.timeout);
  showNotice.timeout = window.setTimeout(() => { notice.hidden = true; }, 6500);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function formatNumber(value) {
  return new Intl.NumberFormat("es-AR", { maximumFractionDigits: 8 }).format(value);
}

function statusLabel(status) {
  return ({
    generated: "Generada",
    rejected_range: "Fuera de rango",
    rejected_encoding: "No representable",
    pending_configuration: "Pendiente",
  })[status] ?? status;
}

function renderInstruments() {
  instrumentCount.textContent = instruments.length;
  if (instruments.length === 0) {
    instrumentRows.innerHTML = '<tr><td class="empty-cell" colspan="6">Todavía no hay instrumentos. Agregá el primero para comenzar.</td></tr>';
  } else {
    instrumentRows.innerHTML = instruments.map((instrument) => `
      <tr>
        <td class="instrument-name">${escapeHtml(instrument.name)}</td>
        <td class="mono">${escapeHtml(instrument.arinc_label)}</td>
        <td>${formatNumber(instrument.min_value)} – ${formatNumber(instrument.max_value)}</td>
        <td><span class="badge">${escapeHtml(instrument.encoding_type)}</span></td>
        <td><span class="badge ${instrument.arinc_config ? "generated" : ""}">${instrument.arinc_config ? "Definida" : "Pendiente"}</span></td>
        <td><div class="row-actions">
          <button class="text-button" type="button" data-edit="${instrument.id}">Editar</button>
          <button class="text-button danger" type="button" data-delete-instrument="${instrument.id}">Eliminar</button>
        </div></td>
      </tr>
    `).join("");
  }

  const currentValue = instrumentSelect.value;
  instrumentSelect.innerHTML = '<option value="">Seleccioná un instrumento</option>' +
    instruments.map((instrument) =>
      `<option value="${instrument.id}">${escapeHtml(instrument.name)} (${escapeHtml(instrument.arinc_label)})</option>`,
    ).join("");
  if (instruments.some((instrument) => String(instrument.id) === currentValue)) {
    instrumentSelect.value = currentValue;
  }
}

function renderSends() {
  if (sends.length === 0) {
    sendRows.innerHTML = '<tr><td class="empty-cell" colspan="6">Los envíos validados aparecerán acá.</td></tr>';
    return;
  }
  sendRows.innerHTML = sends.map((send) => {
    const date = new Date(`${send.sent_at.replace(" ", "T")}Z`);
    const dateLabel = Number.isNaN(date.getTime()) ? send.sent_at : date.toLocaleString("es-AR");
    const word = send.generated_word
      ? `<span class="mono word" title="${send.generated_word}">${send.generated_word}</span>`
      : `<span class="muted" title="${escapeHtml(send.details ?? "")}">—</span>`;
    return `
      <tr>
        <td>${escapeHtml(dateLabel)}</td>
        <td class="instrument-name">${escapeHtml(send.instrument_name)}</td>
        <td>${formatNumber(send.value)}</td>
        <td><span class="badge ${escapeHtml(send.validation_status)}" title="${escapeHtml(send.details ?? "")}">${escapeHtml(statusLabel(send.validation_status))}</span></td>
        <td>${word}</td>
        <td><div class="row-actions">
          <button class="text-button" type="button" data-edit-send="${send.id}">Editar</button>
          <button class="text-button danger" type="button" data-delete-send="${send.id}">Eliminar</button>
        </div></td>
      </tr>
    `;
  }).join("");
}

async function loadData() {
  try {
    [instruments, sends] = await Promise.all([
      request("/api/instruments"),
      request("/api/sends"),
    ]);
    renderInstruments();
    renderSends();
  } catch (error) {
    showNotice(`No se pudieron cargar los datos: ${error.message}`, true);
    instrumentRows.innerHTML = '<tr><td class="empty-cell" colspan="6">No se pudo cargar la información.</td></tr>';
    sendRows.innerHTML = '<tr><td class="empty-cell" colspan="6">No se pudo cargar la información.</td></tr>';
  }
}

function openInstrumentForm(instrument = null) {
  instrumentForm.reset();
  document.querySelector("#instrument-id").value = instrument?.id ?? "";
  document.querySelector("#dialog-title").textContent = instrument ? "Editar instrumento" : "Nuevo instrumento";
  document.querySelector("#instrument-name").value = instrument?.name ?? "";
  document.querySelector("#instrument-label").value = instrument?.arinc_label ?? "";
  document.querySelector("#encoding-type").value = instrument?.encoding_type ?? "BNR";
  document.querySelector("#min-value").value = instrument?.min_value ?? "";
  document.querySelector("#max-value").value = instrument?.max_value ?? "";
  document.querySelector("#arinc-config").value = instrument?.arinc_config
    ? JSON.stringify(instrument.arinc_config, null, 2)
    : "";
  dialog.showModal();
}

document.querySelector("#new-instrument").addEventListener("click", () => openInstrumentForm());
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());

instrumentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(instrumentForm);
  const configText = formData.get("arinc_config").trim();
  let arincConfig = null;
  if (configText) {
    try {
      arincConfig = JSON.parse(configText);
      if (!arincConfig || Array.isArray(arincConfig) || typeof arincConfig !== "object") {
        throw new Error("La configuración debe ser un objeto JSON.");
      }
    } catch (error) {
      showNotice(`Configuración ARINC inválida: ${error.message}`, true);
      return;
    }
  }

  const id = formData.get("id");
  const payload = {
    name: formData.get("name"),
    arinc_label: formData.get("arinc_label"),
    min_value: Number(formData.get("min_value")),
    max_value: Number(formData.get("max_value")),
    encoding_type: formData.get("encoding_type"),
    arinc_config: arincConfig,
  };
  try {
    await request(id ? `/api/instruments/${id}` : "/api/instruments", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    dialog.close();
    showNotice(id ? "Instrumento actualizado." : "Instrumento creado.");
    await loadData();
  } catch (error) {
    showNotice(`No se pudo guardar el instrumento: ${error.message}`, true);
  }
});

sendForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(sendForm);
  try {
    const send = await request("/api/sends", {
      method: "POST",
      body: JSON.stringify({
        instrument_id: Number(formData.get("instrument_id")),
        value: Number(formData.get("value")),
      }),
    });
    sends.unshift(send);
    renderSends();
    const messages = {
      generated: "Valor validado y palabra ARINC de 32 bits generada.",
      rejected_range: `Envío rechazado: ${send.details}`,
      rejected_encoding: `No se pudo generar la palabra: ${send.details}`,
      pending_configuration: `Envío guardado como pendiente: ${send.details}`,
    };
    showNotice(messages[send.validation_status] ?? "Envío registrado.", send.validation_status.startsWith("rejected"));
  } catch (error) {
    showNotice(`No se pudo registrar el envío: ${error.message}`, true);
  }
});

instrumentRows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete-instrument]");
  if (editButton) {
    const instrument = instruments.find((item) => item.id === Number(editButton.dataset.edit));
    if (instrument) openInstrumentForm(instrument);
  }
  if (deleteButton) {
    const id = deleteButton.dataset.deleteInstrument;
    if (!window.confirm("¿Eliminar este instrumento? No se puede eliminar si ya tiene envíos asociados.")) return;
    try {
      await request(`/api/instruments/${id}`, { method: "DELETE" });
      showNotice("Instrumento eliminado.");
      await loadData();
    } catch (error) {
      showNotice(`No se pudo eliminar: ${error.message}`, true);
    }
  }
});

sendRows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-send]");
  const deleteButton = event.target.closest("[data-delete-send]");
  if (editButton) {
    const send = sends.find((item) => item.id === Number(editButton.dataset.editSend));
    if (!send) return;
    const value = window.prompt("Nuevo valor a transmitir:", String(send.value));
    if (value === null) return;
    const parsedValue = Number(value);
    if (value.trim() === "" || !Number.isFinite(parsedValue)) {
      showNotice("Ingresá un valor numérico finito.", true);
      return;
    }
    try {
      const updatedSend = await request(`/api/sends/${send.id}`, {
        method: "PUT",
        body: JSON.stringify({
          instrument_id: send.instrument_id,
          value: parsedValue,
        }),
      });
      sends = sends.map((item) => item.id === updatedSend.id ? updatedSend : item);
      renderSends();
      showNotice("Envío actualizado y validado nuevamente.");
    } catch (error) {
      showNotice(`No se pudo actualizar el envío: ${error.message}`, true);
    }
    return;
  }
  if (!deleteButton || !window.confirm("¿Eliminar este envío del historial?")) return;
  try {
    await request(`/api/sends/${deleteButton.dataset.deleteSend}`, { method: "DELETE" });
    sends = sends.filter((send) => send.id !== Number(deleteButton.dataset.deleteSend));
    renderSends();
    showNotice("Envío eliminado del historial.");
  } catch (error) {
    showNotice(`No se pudo eliminar el envío: ${error.message}`, true);
  }
});

loadData();
