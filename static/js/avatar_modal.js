// Avatar modal handlers + selection UX
(function(){
  function qs(sel, root){ return (root||document).querySelector(sel); }
  function qsa(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }

  var modal = qs('#avatarModal');
  var form  = qs('#avatarForm');
  var fileInput = qs('#avatarFile');

  function setOpen(isOpen){
    if(!modal) return;
    if(isOpen){
      modal.removeAttribute('hidden');
      modal.setAttribute('aria-hidden','false');
      document.body.style.overflow = 'hidden';
    }else{
      modal.setAttribute('hidden','');
      modal.setAttribute('aria-hidden','true');
      document.body.style.overflow = '';
    }
  }

  window.openAvatarModal  = function(){ setOpen(true);  };
  window.closeAvatarModal = function(){ setOpen(false); };

  // Openers (mobile + desktop buttons if present)
  var mbtn = qs('#editAvatarBtnMobile');
  var dbtn = qs('#editAvatarBtnDesktop');
  [mbtn, dbtn].filter(Boolean).forEach(function(btn){
    btn.addEventListener('click', function(e){ e.preventDefault(); setOpen(true); });
  });

  // Close buttons + outside click + ESC
  qsa('[data-close]', modal).forEach(function(el){ el.addEventListener('click', function(){ setOpen(false); }) });
  if(modal){
    modal.addEventListener('click', function(e){ if(e.target === modal){ setOpen(false); }});
  }
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape' && modal && !modal.hasAttribute('hidden')) setOpen(false);
  });

  // Highlight selected preset + ensure radio is checked
  function clearHighlights(){
    qsa('.avatar-option').forEach(function(opt){ opt.classList.remove('selected'); });
  }
  window.selectPreset = function(imgEl){
    clearHighlights();
    var opt = imgEl.closest('.avatar-option');
    if(opt){ opt.classList.add('selected'); }
    if(fileInput){ fileInput.value = ''; }
    var radio = opt && opt.querySelector('input[type=radio][name=preset]');
    if(radio){ radio.checked = true; }
  };

  // When user chooses file -> unselect preset radios
  if(fileInput){
    fileInput.addEventListener('change', function(){
      clearHighlights();
      qsa('input[name=preset]').forEach(function(r){ r.checked = false; });
    });
  }

  // Click images to select preset
  qsa('.avatar-option img').forEach(function(img){
    img.addEventListener('click', function(){ window.selectPreset(img); });
  });
})();
