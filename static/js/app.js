/**
 * Portal MMQEP — catálogo de categorías/subcategorías definido por el servidor (#mmq-catalogo-portal).
 * Compatibilidad: si existe window.MMQ_CATS (nombre de categoría → lista de strings), también funciona en pantallas legacy.
 */

function portalCatalogParsed() {
  var el = document.getElementById("mmq-catalogo-portal");
  if (!el) return null;
  try {
    var raw = JSON.parse(el.textContent || "null");
    return Array.isArray(raw) ? raw : null;
  } catch (e) {
    return null;
  }
}

function refillSubopciones(cat, subSelect, preselect) {
  while (subSelect.options.length > 0) subSelect.remove(0);

  var ph = document.createElement("option");
  ph.value = "";
  ph.textContent = cat ? "— Elija subcategoría —" : "— Primero elija categoría —";
  subSelect.appendChild(ph);

  var data = portalCatalogParsed();
  if (data && cat) {
    var block = null;
    for (var i = 0; i < data.length; i++) {
      if (String(data[i].id) === String(cat)) {
        block = data[i];
        break;
      }
    }
    if (block && block.subs && block.subs.length) {
      block.subs.forEach(function (s) {
        var opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.nombre;
        subSelect.appendChild(opt);
      });
      subSelect.disabled = false;
      if (preselect) subSelect.value = String(preselect);
      return;
    }
  }

  if (cat && window.MMQ_CATS && window.MMQ_CATS[cat]) {
    window.MMQ_CATS[cat].forEach(function (s) {
      var opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      subSelect.appendChild(opt);
    });
    subSelect.disabled = false;
    if (preselect) subSelect.value = preselect;
    return;
  }

  subSelect.disabled = true;
}

/**
 * Portal público: anónimos + categorías/subcategorías (por id cuando hay JSON de catálogo)
 */
window.MMQ_denunciasInit = function () {
  var anonChk = document.getElementById("anon");
  var datosFld = document.getElementById("datos-ident");
  var selCat = document.getElementById("categoria");
  var selSub = document.getElementById("subcategoria");
  var btnEnviar = document.getElementById("btn-enviar-registro");
  var formDn = document.getElementById("form-denuncia");

  function updateEnviarHabilitacion() {
    if (!btnEnviar || !formDn) return;

    var desc = formDn.querySelector('textarea[name="descripcion"]');
    var txtOk = desc && desc.value.trim().length >= 30;

    var acceptV = formDn.querySelector('input[name="acepto_veracidad"]');
    var acceptD = formDn.querySelector('input[name="acepto_datos"]');
    var declarOk =
      acceptV && acceptV.checked && acceptD && acceptD.checked;

    var catOk = selCat && String(selCat.value).length > 0;
    var subOk =
      selSub &&
      !selSub.disabled &&
      String(selSub.value).length > 0 &&
      selSub.options.length > 1;

    var fechaIn = formDn.querySelector('input[name="fecha_hecho"]');
    var fechaOk = fechaIn && String(fechaIn.value).trim().length > 0;

    var anon = anonChk && anonChk.checked;
    var datosOk = true;
    if (!anon && datosFld) {
      var nomIn = datosFld.querySelector('input[name="nombres"]');
      var idIn = datosFld.querySelector('input[name="identificacion"]');
      var telIn = datosFld.querySelector('input[name="telefono"]');
      var mailIn = datosFld.querySelector('input[name="correo"]');
      var nomV = nomIn ? nomIn.value.trim() : "";
      var telV = telIn ? telIn.value.replace(/[\s-]/g, "") : "";
      var mailV = mailIn ? mailIn.value.trim() : "";
      var mailParts = mailV.split("@");
      var mailOk =
        mailV.length > 5 &&
        mailParts.length === 2 &&
        mailParts[1].indexOf(".") !== -1;
      datosOk =
        nomIn &&
        idIn &&
        telIn &&
        mailIn &&
        nomV.length >= 3 &&
        nomV.indexOf(" ") !== -1 &&
        idIn.value.trim().length >= 1 &&
        telV.length >= 7 &&
        mailOk;
    }

    var ready = txtOk && declarOk && catOk && subOk && fechaOk && datosOk;
    btnEnviar.disabled = !ready;
    if (ready) {
      btnEnviar.removeAttribute("title");
    } else {
      btnEnviar.setAttribute(
        "title",
        "Complete fecha del hecho, categoría y subcategoría, descripción (mínimo 30 caracteres), datos completos del denunciante si no es anónimo, y marque ambas declaraciones."
      );
    }
  }

  function syncAnonimo() {
    if (!anonChk || !datosFld) return;
    datosFld.hidden = anonChk.checked;
    datosFld.querySelectorAll("input").forEach(function (inp) {
      var need =
        !anonChk.checked &&
        (inp.name === "nombres" ||
          inp.name === "identificacion" ||
          inp.name === "telefono" ||
          inp.name === "correo");
      inp.required = need;
      if (anonChk.checked) inp.value = "";
    });
    updateEnviarHabilitacion();
  }

  if (anonChk && datosFld) {
    anonChk.addEventListener("change", syncAnonimo);
    syncAnonimo();
  } else if (btnEnviar) {
    updateEnviarHabilitacion();
  }

  if (selCat && selSub) {
    var saved = selSub.dataset.preselect || selSub.value || "";

    refillSubopciones(selCat.value, selSub, "");

    selCat.addEventListener("change", function () {
      refillSubopciones(selCat.value, selSub, "");
      updateEnviarHabilitacion();
    });

    selSub.addEventListener("change", updateEnviarHabilitacion);

    if (selCat.value) {
      refillSubopciones(selCat.value, selSub, "");
      if (saved) selSub.value = String(saved);
    }

    updateEnviarHabilitacion();
  }

  if (formDn && btnEnviar) {
    var descTa = formDn.querySelector('textarea[name="descripcion"]');
    if (descTa) {
      descTa.addEventListener("input", updateEnviarHabilitacion);
      descTa.addEventListener("change", updateEnviarHabilitacion);
    }
    ["acepto_veracidad", "acepto_datos"].forEach(function (nm) {
      var cx = formDn.querySelector('input[name="' + nm + '"]');
      if (cx) {
        cx.addEventListener("change", updateEnviarHabilitacion);
      }
    });
    if (datosFld) {
      datosFld.querySelectorAll("input").forEach(function (inp) {
        inp.addEventListener("input", updateEnviarHabilitacion);
        inp.addEventListener("change", updateEnviarHabilitacion);
      });
    }
    var fh = formDn.querySelector('input[name="fecha_hecho"]');
    var hh = formDn.querySelector('input[name="hora_hecho"]');
    if (fh) {
      fh.addEventListener("change", updateEnviarHabilitacion);
      fh.addEventListener("input", updateEnviarHabilitacion);
    }
    if (hh) {
      hh.addEventListener("change", updateEnviarHabilitacion);
    }

    formDn.addEventListener("submit", function () {
      if (anonChk && anonChk.checked && datosFld) {
        datosFld.querySelectorAll("input").forEach(function (inp) {
          inp.value = "";
        });
      }
    });
  }

  updateEnviarHabilitacion();
};

document.addEventListener("DOMContentLoaded", function () {
  var btn = document.querySelector(".js-menu-toggle");
  var side = document.querySelector(".admin-sidebar");
  if (btn && side) {
    btn.addEventListener("click", function () {
      side.classList.toggle("sidebar-open");
    });
  }
});
