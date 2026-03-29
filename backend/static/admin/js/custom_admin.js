document.addEventListener('DOMContentLoaded', function () {

  // ── 1. Casser les onglets en 2 lignes après le 4ème ──────────────────────
  var tabs = document.querySelector('.change-form .nav-tabs, #content .nav-tabs')
  if (tabs) {
    var items = tabs.querySelectorAll(':scope > li')
    if (items.length > 4) {
      tabs.style.flexWrap = 'wrap'
      var br = document.createElement('li')
      br.setAttribute('aria-hidden', 'true')
      br.style.cssText = 'flex-basis:100%;height:0;padding:0;margin:0;list-style:none;border:none;'
      items[3].insertAdjacentElement('afterend', br)
    }
  }

  // ── 2. Supprimer le bloc d'actions Jazzmin en bas ────────────────────────
  var jazzyActions = document.getElementById('jazzy-actions')
  if (jazzyActions) jazzyActions.style.display = 'none'

  // ── 4. Remplacer les checkboxes "Supprimer ?" par des boutons ─────────────
  function upgradeDeleteCheckboxes () {
    document.querySelectorAll('.delete input[type="checkbox"], td.delete input[type="checkbox"]').forEach(function (cb) {
      if (cb.dataset.upgraded) return
      cb.dataset.upgraded = '1'

      var btn = document.createElement('button')
      btn.type = 'button'
      btn.textContent = 'Supprimer'
      btn.style.cssText = [
        'background:#ef4444',
        'color:#fff',
        'border:none',
        'border-radius:6px',
        'padding:4px 10px',
        'font-size:0.75rem',
        'font-weight:600',
        'cursor:pointer',
        'white-space:nowrap',
        'transition:background .15s',
      ].join(';')

      btn.addEventListener('mouseover',  function () { btn.style.background = '#b91c1c' })
      btn.addEventListener('mouseout',   function () { btn.style.background = cb.checked ? '#b91c1c' : '#ef4444' })

      btn.addEventListener('click', function () {
        cb.checked = !cb.checked
        var row = cb.closest('tr')
        if (cb.checked) {
          btn.textContent = 'Annuler'
          btn.style.background = '#6b7280'
          if (row) row.style.opacity = '0.4'
        } else {
          btn.textContent = 'Supprimer'
          btn.style.background = '#ef4444'
          if (row) row.style.opacity = '1'
        }
      })

      // Masquer la checkbox et son label, insérer le bouton
      cb.style.display = 'none'
      var label = cb.closest('td, .delete')
      if (label) {
        label.insertBefore(btn, cb)
      } else {
        cb.parentNode.insertBefore(btn, cb)
      }
    })
  }

  upgradeDeleteCheckboxes()

  // Relancer après ajout dynamique d'une ligne inline ("Ajouter un objet…")
  document.addEventListener('click', function (e) {
    if (e.target && (e.target.classList.contains('add-row') || e.target.closest('.add-row'))) {
      setTimeout(upgradeDeleteCheckboxes, 200)
    }
  })

  // ── 3. Remplacer le titre h1 par le nom de l'utilisateur en cours ─────────
  var h1 = document.querySelector('h1')
  if (h1) {
    var usernameInput  = document.querySelector('#id_username')
    var firstNameInput = document.querySelector('#id_first_name')
    var lastNameInput  = document.querySelector('#id_last_name')

    var displayName = ''
    if (firstNameInput && firstNameInput.value.trim()) {
      displayName = firstNameInput.value.trim()
      if (lastNameInput && lastNameInput.value.trim()) displayName += ' ' + lastNameInput.value.trim()
    } else if (usernameInput && usernameInput.value.trim()) {
      displayName = usernameInput.value.trim()
    }

    if (displayName) {
      h1.textContent = displayName
    }
    h1.style.cssText = 'color:#111 !important;font-weight:700;font-size:1.6rem;letter-spacing:-0.02em;'
  }

  // ── 4. Supprimer le doublon "Users" dans le breadcrumb ───────────────────
  var crumbs = document.querySelectorAll('.breadcrumb .breadcrumb-item, ol.breadcrumb li')
  // Cherche deux items consécutifs avec le même texte
  for (var i = 0; i < crumbs.length - 1; i++) {
    var a = crumbs[i].textContent.trim()
    var b = crumbs[i + 1].textContent.trim()
    if (a && b && a === b) {
      crumbs[i].style.display = 'none'
      // Aussi masquer le séparateur si présent
      var sep = crumbs[i].querySelector('.breadcrumb-separator')
      if (sep) sep.style.display = 'none'
    }
  }

})
