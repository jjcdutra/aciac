/* Associação Comercial — JS leve: menu, máscaras, copy PIX, consulta AJAX */
(function () {
  "use strict";

  /* ===== Menu hambúrguer ===== */
  var toggle = document.getElementById("navToggle");
  var menu = document.getElementById("menuPrincipal");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ===== Máscaras CPF/CNPJ e telefone ===== */
  function maskDocumento(v) {
    v = v.replace(/\D/g, "");
    if (v.length <= 11) {
      return v.replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    }
    return v.replace(/(\d{2})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1/$2")
      .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
  }

  function maskTelefone(v) {
    v = v.replace(/\D/g, "");
    if (v.length <= 11) {
      return v.replace(/(\d{2})(\d)/, "($1) $2")
        .replace(/(\d{5})(\d)/, "$1-$2");
    }
    return v;
  }

  document.querySelectorAll('[data-mask="documento"]').forEach(function (el) {
    el.addEventListener("input", function () {
      var pos = el.selectionStart;
      var antes = el.value.length;
      el.value = maskDocumento(el.value);
      var delta = el.value.length - antes;
      if (pos !== null && pos + delta >= 0) {
        try { el.setSelectionRange(pos + delta, pos + delta); } catch (e) {}
      }
    });
  });

  document.querySelectorAll('[data-mask="telefone"]').forEach(function (el) {
    el.addEventListener("input", function () {
      el.value = maskTelefone(el.value);
    });
  });

  /* ===== Copiar PIX copia-e-cola ===== */
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var alvo = document.querySelector(btn.getAttribute("data-copy"));
      if (!alvo) return;
      var texto = alvo.textContent.trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(texto).then(function () {
          feedback(btn, "Copiado!");
        });
      } else {
        var ta = document.createElement("textarea");
        ta.value = texto;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        feedback(btn, "Copiado!");
      }
    });
  });

  function feedback(btn, texto) {
    var original = btn.textContent;
    btn.textContent = texto;
    btn.disabled = true;
    setTimeout(function () {
      btn.textContent = original;
      btn.disabled = false;
    }, 1800);
  }

  /* ===== Auto-dismiss de alertas ===== */
  document.querySelectorAll(".alert").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.5s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 500);
    }, 6000);
  });
})();
