/**
 * FilamentHub 3D - Modern Vanilla JS SPA Application
 * High-Contrast Dark Tech UI/UX, Multi-Quantity, Lifecycle & Vision AI
 * Tailored for iPhone 14 Pro (393 x 852 px, iOS Safari) & Desktop
 */

class FilamentHubApp {
  constructor() {
    this.user = null;
    this.spools = [];
    this.tares = [];
    this.catalogPresets = [];
    this.activeFilterStatus = 'all'; // 'all' | 'opened' | 'new'
    this.materialFilter = '';
    this.brandFilter = '';
    this.searchQuery = '';
    this.sortBy = 'in_use_desc';
    this.a4Queue = JSON.parse(localStorage.getItem('filamenthub_a4_queue') || '[]');

    // Settings state
    this.settings = {
      gemini_configured: false,
      gemini_api_key_masked: '',
      gemini_model: 'gemini-3.5-flash-lite'
    };

    // Modal & Action states
    this.currentEditingSpool = null;
    this.currentWeighSpool = null;
    this.currentLabelSpool = null;
    this.labelTape = 24;
    this.labelCodeType = 'barcode';
    this.activeEyedropperHex = '#10b981';

    // Missing fields wizard state
    this.missingFields = [];
    this.missingSelections = {};

    // Scanner & Camera state
    this.html5QrScanner = null;
    this.isCameraScanning = false;
    this.liveCameraStream = null;
    this.aiImageBase64 = null;

    document.addEventListener('DOMContentLoaded', () => this.init());
  }

  // =========================================================================
  // 1. INITIALIZATION & AUTH
  // =========================================================================
  async init() {
    this.initThemeListener();
    this.updateA4QueueBadge();
    this.updateSettingsUi();
    this.setupEventListeners();
    this.initSwipeGestures();
    this.updateQuickSortUi();
    await this.checkAuth();
    await this.loadSettings();
    await this.loadCatalogPresets();
  }

  initThemeListener() {
    try {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const applyTheme = (matches) => {
        if (matches) {
          document.documentElement.classList.add('dark');
          const meta = document.querySelector('meta[name="theme-color"]');
          if (meta) meta.setAttribute('content', '#0f172a');
        } else {
          document.documentElement.classList.remove('dark');
          const meta = document.querySelector('meta[name="theme-color"]');
          if (meta) meta.setAttribute('content', '#ffffff');
        }
      };
      applyTheme(mq.matches);
      if (mq.addEventListener) {
        mq.addEventListener('change', (e) => applyTheme(e.matches));
      } else if (mq.addListener) {
        mq.addListener((e) => applyTheme(e.matches));
      }
    } catch (e) {
      console.warn('Errore listener prefers-color-scheme:', e);
    }
  }

  setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        if (clearSearchBtn) {
          clearSearchBtn.classList.toggle('hidden', this.searchQuery.length === 0);
        }
        this.renderSpoolViews();
      });
    }
    if (clearSearchBtn) {
      clearSearchBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        this.searchQuery = '';
        clearSearchBtn.classList.add('hidden');
        this.renderSpoolViews();
      });
    }

    // Global Paste Listener (Ctrl+V) for AI Label Photo (only when Gemini API key is configured)
    window.addEventListener('paste', async (e) => {
      if (!this.settings?.gemini_configured) return;
      const spoolModal = document.getElementById('spoolModal');
      if (!spoolModal || spoolModal.classList.contains('hidden')) return;
      if (this.currentEditingSpool) return;

      if (e.clipboardData && e.clipboardData.items) {
        for (let i = 0; i < e.clipboardData.items.length; i++) {
          const item = e.clipboardData.items[i];
          if (item.type && item.type.startsWith('image/')) {
            const blob = item.getAsFile();
            if (blob) {
              await this.loadImageBlobToCanvas(blob);
              this.showToast('Immagine incollata! Avvio analisi con Gemini...', 'info');
              await this.analyzeImageWithGemini();
              e.preventDefault();
              break;
            }
          }
        }
      }
    });

    // Canvas click for Eyedropper
    const canvas = document.getElementById('aiCanvas');
    if (canvas) {
      canvas.addEventListener('click', (e) => this.handleCanvasEyedropper(e));
      canvas.addEventListener('touchstart', (e) => {
        if (e.touches.length > 0) {
          const touch = e.touches[0];
          const mouseEvent = new MouseEvent('click', {
            clientX: touch.clientX,
            clientY: touch.clientY
          });
          canvas.dispatchEvent(mouseEvent);
        }
      }, { passive: true });
    }

    // Click outside listener for catalog search combobox
    document.addEventListener('click', (e) => {
      const wrapper = document.getElementById('catalogSearchWrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        this.closeCatalogDropdown();
      }
    });
  }

  async checkAuth() {
    try {
      const res = await fetch('/api/auth/me');
      if (res.ok) {
        this.user = await res.json();
        this.onAuthenticated();
      } else {
        this.showLoginModal();
      }
    } catch (err) {
      console.warn('Auth check error:', err);
      this.showLoginModal();
    }
  }

  onAuthenticated() {
    this.hideLoginModal();
    this.updateUserHeader();
    this.loadTares();
    this.loadSpools();
    this.loadSettings();
  }

  updateUserHeader() {
    if (!this.user) return;
    const nameLabel = document.getElementById('mobileUserFullName');
    const roleBadge = document.getElementById('mobileUserRole');
    const avatar = document.getElementById('mobileUserAvatar');
    const adminBtn = document.getElementById('mobileAdminMenuBtn');

    if (nameLabel) nameLabel.textContent = this.user.username;
    if (roleBadge) roleBadge.textContent = `Ruolo: ${this.user.role}`;
    if (avatar) avatar.textContent = this.user.username.charAt(0).toUpperCase();

    if (adminBtn) {
      adminBtn.classList.toggle('hidden', this.user.role !== 'admin');
    }
  }

  showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  async handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorAlert = document.getElementById('loginErrorAlert');
    const rateLimitAlert = document.getElementById('loginRateLimitAlert');
    const submitBtn = document.getElementById('loginSubmitBtn');

    if (errorAlert) errorAlert.classList.add('hidden');
    if (rateLimitAlert) rateLimitAlert.classList.add('hidden');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Accesso in corso...';
    }

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (res.ok) {
        this.user = await res.json();
        this.showToast(`Benvenuto, ${this.user.username}!`, 'success');
        this.onAuthenticated();
      } else if (res.status === 429) {
        if (rateLimitAlert) rateLimitAlert.classList.remove('hidden');
      } else {
        const data = await res.json().catch(() => ({}));
        if (errorAlert) {
          errorAlert.textContent = data.detail || 'Credenziali non valide.';
          errorAlert.classList.remove('hidden');
        }
      }
    } catch (err) {
      if (errorAlert) {
        errorAlert.textContent = 'Errore di connessione al server.';
        errorAlert.classList.remove('hidden');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>Accedi al Sistema</span>';
      }
    }
  }

  async logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      console.warn(e);
    }
    this.user = null;
    this.spools = [];
    this.showLoginModal();
    this.showToast('Disconnessione effettuata', 'info');
  }

  openMobileMenuSheet(e) {
    if (e) e.stopPropagation();
    const sheet = document.getElementById('mobileMenuSheet');
    if (!sheet) return;

    if (this.user) {
      const avatar = document.getElementById('mobileUserAvatar');
      const name = document.getElementById('mobileUserFullName');
      const role = document.getElementById('mobileUserRole');
      const adminBtn = document.getElementById('mobileAdminMenuBtn');

      if (avatar) avatar.textContent = this.user.username.charAt(0).toUpperCase();
      if (name) name.textContent = this.user.username;
      if (role) role.textContent = `Ruolo: ${this.user.role}`;
      if (adminBtn) adminBtn.classList.toggle('hidden', this.user.role !== 'admin');
    }

    sheet.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    lucide.createIcons();
  }

  closeMobileMenuSheet() {
    const sheet = document.getElementById('mobileMenuSheet');
    if (sheet) sheet.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  // =========================================================================
  // 2. SETTINGS & GEMINI CONFIGURATION
  // =========================================================================
  async loadSettings() {
    try {
      const res = await fetch('/api/admin/settings');
      if (res.ok) {
        const data = await res.json();
        this.settings = { ...this.settings, ...data };
      }
    } catch (err) {
      console.warn('Impossibile caricare impostazioni da backend:', err);
    } finally {
      this.updateSettingsUi();
    }
  }

  updateSettingsUi() {
    const isConfigured = Boolean(this.settings && this.settings.gemini_configured);

    // 1. Enable / Disable all AI Photo buttons & file inputs
    const aiBtnIds = ['topbarAiPhotoBtn', 'modalAiCameraBtn', 'modalAiGalleryBtn', 'geminiAnalyzeBtn'];
    aiBtnIds.forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.disabled = !isConfigured;
        btn.title = isConfigured
          ? 'Scatta o carica foto etichetta per compilazione AI'
          : 'Funzione disattivata: specifica prima una API Key Gemini valida nelle Impostazioni';
      }
    });

    const camInput = document.getElementById('nativeCameraPhotoInput');
    if (camInput) camInput.disabled = !isConfigured;

    const galleryInput = document.getElementById('spoolPhotoInput');
    if (galleryInput) galleryInput.disabled = !isConfigured;

    // 2. Hint banner inside New Spool modal
    const disabledHint = document.getElementById('spoolModalAiDisabledHint');
    if (disabledHint) {
      disabledHint.classList.toggle('hidden', isConfigured);
    }

    // 3. Mobile menu badge & bottom nav dot
    const menuBadge = document.getElementById('menuGeminiBadge');
    if (menuBadge) {
      if (isConfigured) {
        menuBadge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800';
        menuBadge.textContent = 'Attiva';
      } else {
        menuBadge.className = 'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800';
        menuBadge.textContent = 'Non attiva';
      }
    }

    const navDot = document.getElementById('navMenuDot');
    if (navDot) {
      navDot.classList.remove('hidden');
      navDot.className = isConfigured
        ? 'absolute top-1 right-1/4 w-2 h-2 rounded-full bg-emerald-500'
        : 'absolute top-1 right-1/4 w-2 h-2 rounded-full bg-amber-500 animate-pulse';
    }

    const dot = document.getElementById('geminiStatusDot');
    if (dot) {
      if (isConfigured) {
        dot.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400';
        dot.title = 'Gemini AI Configurato e Attivo';
      } else {
        dot.className = 'w-2 h-2 rounded-full bg-amber-500 animate-pulse';
        dot.title = 'Gemini AI Non Configurato (Clicca per inserire la chiave)';
      }
    }
  }

  triggerCameraAiPhoto() {
    if (!this.settings?.gemini_configured) {
      this.showToast('Inserisci prima una API Key Gemini valida nelle Impostazioni.', 'warning');
      return;
    }
    const input = document.getElementById('nativeCameraPhotoInput');
    if (input && !input.disabled) {
      input.click();
    }
  }

  triggerGalleryAiPhoto() {
    if (!this.settings?.gemini_configured) {
      this.showToast('Inserisci prima una API Key Gemini valida nelle Impostazioni.', 'warning');
      return;
    }
    const input = document.getElementById('spoolPhotoInput');
    if (input && !input.disabled) {
      input.click();
    }
  }

  openSettingsModal() {
    const badge = document.getElementById('settingsGeminiBadge');
    const keyInput = document.getElementById('settingsGeminiApiKey');
    const modelSelect = document.getElementById('settingsGeminiModel');
    const clearBtn = document.getElementById('settingsClearKeyBtn');

    if (badge) {
      if (this.settings.gemini_configured) {
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800';
        badge.textContent = `Attiva (${this.settings.gemini_api_key_masked || 'Configurata'})`;
      } else {
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800';
        badge.textContent = 'Non configurata';
      }
    }

    if (clearBtn) {
      clearBtn.classList.toggle('hidden', !this.settings.gemini_configured);
    }

    if (keyInput) keyInput.value = '';
    if (modelSelect && this.settings.gemini_model) {
      modelSelect.value = this.settings.gemini_model;
    }

    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  async handleSaveSettings(e) {
    e.preventDefault();
    const keyInput = document.getElementById('settingsGeminiApiKey')?.value.trim();
    const model = document.getElementById('settingsGeminiModel')?.value || 'gemini-3.5-flash-lite';
    const saveBtn = document.getElementById('settingsSaveBtn');

    if (keyInput && (!keyInput.startsWith('AIza') || keyInput.length < 30)) {
      this.showToast("Chiave API non valida: deve iniziare con 'AIza' ed essere completa.", 'error');
      return;
    }

    const payload = {
      gemini_model: model
    };
    if (keyInput) {
      payload.gemini_api_key = keyInput;
    }

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Verifica in corso...';
    }

    try {
      const res = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const updated = await res.json();
        this.settings = { ...this.settings, ...updated };
        this.updateSettingsUi();
        this.closeSettingsModal();
        this.showToast('Impostazioni salvate con successo!', 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Chiave API Gemini non valida'), 'error');
      }
    } catch (err) {
      this.showToast(this.formatError(err, 'Errore durante il salvataggio delle impostazioni'), 'error');
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Salva Impostazioni';
      }
    }
  }

  async handleClearGeminiKey() {
    try {
      const res = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini_api_key: '__clear__' })
      });
      if (res.ok) {
        const updated = await res.json();
        this.settings = { ...this.settings, ...updated };
        this.updateSettingsUi();
        this.openSettingsModal();
        this.showToast('Chiave API Gemini rimossa. Funzioni Foto AI disattivate.', 'info');
      }
    } catch (err) {
      this.showToast('Errore durante la rimozione della chiave API', 'error');
    }
  }

  // =========================================================================
  // 3. BRAND LOGOS & PRESET DATABASE
  // =========================================================================
  renderBrandLogo(brandName, size = 'md') {
    const brand = (brandName || '').trim().toLowerCase();
    const pxSize = size === 'sm' ? 18 : size === 'lg' ? 32 : 24;

    // Bambu Lab (#00AE42)
    if (brand.includes('bambu')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#00AE42" fill-opacity="0.18"/>
          <rect x="9.5" y="6.5" width="5" height="8.5" rx="1.5" fill="#00AE42"/>
          <rect x="9.5" y="17" width="5" height="8.5" rx="1.5" fill="#00AE42"/>
          <rect x="17.5" y="6.5" width="5" height="8.5" rx="1.5" fill="#00AE42"/>
          <rect x="17.5" y="17" width="5" height="8.5" rx="1.5" fill="#00AE42"/>
        </svg>
      `;
    }

    // Elegoo (#0076CE)
    if (brand.includes('elegoo')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#0076CE" fill-opacity="0.18"/>
          <rect x="6.5" y="8" width="19" height="16" rx="4" stroke="#0076CE" stroke-width="2.2"/>
          <circle cx="12" cy="15.5" r="2.2" fill="#0076CE"/>
          <circle cx="20" cy="15.5" r="2.2" fill="#0076CE"/>
          <path d="M13.5 19.5h5" stroke="#0076CE" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      `;
    }

    // Anycubic (#3B82F6)
    if (brand.includes('anycubic')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#3B82F6" fill-opacity="0.18"/>
          <path d="M16 6L25 11.2V21.6L16 26.8L7 21.6V11.2L16 6Z" stroke="#3B82F6" stroke-width="2" stroke-linejoin="round"/>
          <path d="M16 6V16.4M25 11.2L16 16.4M7 11.2L16 16.4" stroke="#3B82F6" stroke-width="2" stroke-linejoin="round"/>
          <path d="M16 16.4V26.8" stroke="#3B82F6" stroke-width="2" stroke-linecap="round"/>
        </svg>
      `;
    }

    // Creality (#00B140)
    if (brand.includes('creality')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#00B140" fill-opacity="0.18"/>
          <path d="M16 6.5L25 13.5L16 25.5L7 13.5L16 6.5Z" stroke="#00B140" stroke-width="2" stroke-linejoin="round"/>
          <path d="M16 11.5L21 15.5L16 22L11 15.5L16 11.5Z" fill="#00B140"/>
        </svg>
      `;
    }

    // SUNLU (#FF6600)
    if (brand.includes('sunlu')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#FF6600" fill-opacity="0.18"/>
          <circle cx="16" cy="16" r="6" fill="#FF6600"/>
          <path d="M16 4.5V7.5M16 24.5V27.5M4.5 16H7.5M24.5 16H27.5M7.9 7.9L10 10M22 22L24.1 24.1M7.9 24.1L10 22M22 10L24.1 7.9" stroke="#FF6600" stroke-width="2.2" stroke-linecap="round"/>
        </svg>
      `;
    }

    // eSUN (#0072BC)
    if (brand.includes('esun')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#0072BC" fill-opacity="0.18"/>
          <path d="M22 14.5C21.2 10.5 18 7.5 14 7.5C9.5 7.5 6 11.3 6 16C6 20.7 9.5 24.5 14.5 24.5C18.5 24.5 21.8 21.8 22.4 18H13.5" stroke="#0072BC" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="21" cy="9.5" r="2" fill="#0072BC"/>
        </svg>
      `;
    }

    // Polymaker (#00A99D)
    if (brand.includes('polymaker')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#00A99D" fill-opacity="0.18"/>
          <path d="M16 6L25 11.2V21.6L16 26.8L7 21.6V11.2L16 6Z" stroke="#00A99D" stroke-width="2.2" stroke-linejoin="round"/>
          <circle cx="16" cy="16" r="3.5" fill="#00A99D"/>
          <path d="M16 6V12.5M7 21.6L13 18M25 21.6L19 18" stroke="#00A99D" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      `;
    }

    // Prusament / Prusa (#FA6831)
    if (brand.includes('prusa') || brand.includes('prusament')) {
      return `
        <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
          <rect width="32" height="32" rx="7" fill="#FA6831" fill-opacity="0.18"/>
          <path d="M9 7H17C20.3 7 23 9.7 23 13C23 16.3 20.3 19 17 19H13.5V25H9V7Z" fill="#FA6831"/>
          <rect x="13.5" y="11" width="4.5" height="4" rx="1" fill="#0a0f1d"/>
        </svg>
      `;
    }

    // Generic Fallback (#6366F1)
    return `
      <svg width="${pxSize}" height="${pxSize}" viewBox="0 0 32 32" fill="none" class="shrink-0 inline-block">
        <rect width="32" height="32" rx="7" fill="#6366F1" fill-opacity="0.18"/>
        <circle cx="16" cy="16" r="8.5" stroke="#6366F1" stroke-width="2"/>
        <circle cx="16" cy="16" r="3" fill="#6366F1"/>
      </svg>
    `;
  }

  async loadCatalogPresets() {
    const builtInPresets = [
      // BAMBU LAB (Priority)
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Jade White', color_hex: '#ffffff', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030001' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Black', color_hex: '#0a0a0a', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030018' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Bambu Green', color_hex: '#00ae42', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030025' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Blue', color_hex: '#0055bf', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030032' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Red', color_hex: '#c8102e', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030049' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Orange', color_hex: '#ff671f', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030056' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Yellow', color_hex: '#fed100', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030063' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Basic', color_name: 'Silver', color_hex: '#a2aaad', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.020, flow: 0.98, mvs: 21.0, barcode: '6975337030070' },

      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Charcoal', color_hex: '#1c1d21', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030117' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Ivory White', color_hex: '#f5f5f0', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030124' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Ash Grey', color_hex: '#5c5f66', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030131' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Sakura Pink', color_hex: '#f4b4b8', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030148' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Marine Blue', color_hex: '#1b365d', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030155' },
      { brand: 'Bambu Lab', material: 'PLA', subtype: 'Matte', color_name: 'Latte Brown', color_hex: '#8d6e63', tare: 250, nMin: 190, nMax: 220, bed: 55, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6975337030162' },

      { brand: 'Bambu Lab', material: 'PETG', subtype: 'Basic', color_name: 'Black', color_hex: '#111111', tare: 250, nMin: 230, nMax: 255, bed: 75, k: 0.035, flow: 0.96, mvs: 15.0, barcode: '6975337030200' },
      { brand: 'Bambu Lab', material: 'PETG', subtype: 'Basic', color_name: 'White', color_hex: '#ffffff', tare: 250, nMin: 230, nMax: 255, bed: 75, k: 0.035, flow: 0.96, mvs: 15.0, barcode: '6975337030217' },
      { brand: 'Bambu Lab', material: 'PETG', subtype: 'HF', color_name: 'Emerald Green', color_hex: '#10b981', tare: 250, nMin: 230, nMax: 250, bed: 75, k: 0.032, flow: 0.96, mvs: 18.0, barcode: '6975337030224' },
      { brand: 'Bambu Lab', material: 'PETG', subtype: 'HF', color_name: 'Black', color_hex: '#111111', tare: 250, nMin: 230, nMax: 250, bed: 75, k: 0.032, flow: 0.96, mvs: 18.0, barcode: '6975337030231' },

      { brand: 'Bambu Lab', material: 'PLA-CF', subtype: 'Carbon', color_name: 'Black', color_hex: '#1a1a1a', tare: 250, nMin: 210, nMax: 240, bed: 55, k: 0.025, flow: 0.98, mvs: 16.0, barcode: '6975337030309' },
      { brand: 'Bambu Lab', material: 'PETG-CF', subtype: 'Carbon', color_name: 'Black', color_hex: '#141414', tare: 250, nMin: 240, nMax: 260, bed: 75, k: 0.038, flow: 0.95, mvs: 14.0, barcode: '6975337030316' },
      { brand: 'Bambu Lab', material: 'TPU', subtype: '95A HF', color_name: 'Black', color_hex: '#1f1f1f', tare: 250, nMin: 220, nMax: 240, bed: 35, k: 0.055, flow: 0.97, mvs: 6.0, barcode: '6975337030408' },
      { brand: 'Bambu Lab', material: 'ABS', subtype: 'Standard', color_name: 'Black', color_hex: '#111111', tare: 250, nMin: 240, nMax: 270, bed: 90, k: 0.026, flow: 0.96, mvs: 18.0, barcode: '6975337030507' },
      { brand: 'Bambu Lab', material: 'ASA', subtype: 'Standard', color_name: 'Black', color_hex: '#131313', tare: 250, nMin: 240, nMax: 270, bed: 90, k: 0.028, flow: 0.96, mvs: 16.0, barcode: '6975337030514' },

      // SUNLU (Priority)
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Black', color_hex: '#111111', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451103A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'White', color_hex: '#ffffff', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451101A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Grey', color_hex: '#777777', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451102A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Fuchsia', color_hex: '#d91d84', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451104A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Blue', color_hex: '#0066cc', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451105A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Grass Green', color_hex: '#3bb143', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451106A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: 'Standard', color_name: 'Red', color_hex: '#cc1111', tare: 195, nMin: 205, nMax: 225, bed: 60, k: 0.023, flow: 0.98, mvs: 16.0, barcode: '03451107A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: '2.0 High Speed', color_name: 'Black', color_hex: '#0d0d0d', tare: 195, nMin: 205, nMax: 230, bed: 60, k: 0.021, flow: 0.98, mvs: 22.0, barcode: '03452203A' },
      { brand: 'Sunlu', material: 'PLA+', subtype: '2.0 High Speed', color_name: 'White', color_hex: '#fafafa', tare: 195, nMin: 205, nMax: 230, bed: 60, k: 0.021, flow: 0.98, mvs: 22.0, barcode: '03452201A' },
      { brand: 'Sunlu', material: 'PETG', subtype: 'Standard', color_name: 'Black', color_hex: '#111111', tare: 195, nMin: 230, nMax: 250, bed: 75, k: 0.035, flow: 0.96, mvs: 14.0, barcode: '6971928050016' },
      { brand: 'Sunlu', material: 'PETG', subtype: 'Standard', color_name: 'Solid White', color_hex: '#ffffff', tare: 195, nMin: 230, nMax: 250, bed: 75, k: 0.035, flow: 0.96, mvs: 14.0, barcode: '6971928050023' },
      { brand: 'Sunlu', material: 'TPU', subtype: '95A', color_name: 'Black', color_hex: '#1e1e1e', tare: 195, nMin: 210, nMax: 230, bed: 45, k: 0.060, flow: 0.98, mvs: 5.0, barcode: '6971928050047' },

      // eSUN
      { brand: 'eSUN', material: 'PLA+', subtype: 'Standard', color_name: 'Solid Black', color_hex: '#0a0a0a', tare: 240, nMin: 205, nMax: 225, bed: 60, k: 0.024, flow: 0.97, mvs: 18.0, barcode: '6922572219021' },
      { brand: 'eSUN', material: 'PLA+', subtype: 'Standard', color_name: 'Fire Engine Red', color_hex: '#dc2626', tare: 240, nMin: 205, nMax: 225, bed: 60, k: 0.024, flow: 0.97, mvs: 18.0, barcode: '6922572219151' },
      { brand: 'eSUN', material: 'PETG', subtype: 'Solid', color_name: 'Solid Black', color_hex: '#101010', tare: 240, nMin: 230, nMax: 250, bed: 75, k: 0.034, flow: 0.96, mvs: 15.0, barcode: '6922572219205' },

      // Polymaker
      { brand: 'Polymaker', material: 'PLA', subtype: 'PolyTerra', color_name: 'Charcoal Black', color_hex: '#1a1a1a', tare: 140, nMin: 190, nMax: 230, bed: 50, k: 0.024, flow: 0.97, mvs: 16.0, barcode: '8402542000014' },

      // Elegoo
      { brand: 'Elegoo', material: 'PLA', subtype: 'Rapid PLA+', color_name: 'Black', color_hex: '#111111', tare: 160, nMin: 200, nMax: 230, bed: 60, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6972288001001' },
      { brand: 'Elegoo', material: 'PLA', subtype: 'Rapid PLA+', color_name: 'White', color_hex: '#ffffff', tare: 160, nMin: 200, nMax: 230, bed: 60, k: 0.022, flow: 0.98, mvs: 20.0, barcode: '6972288001018' },

      // Creality
      { brand: 'Creality', material: 'PLA', subtype: 'Hyper PLA', color_name: 'Black', color_hex: '#101010', tare: 200, nMin: 190, nMax: 230, bed: 55, k: 0.020, flow: 0.98, mvs: 22.0, barcode: '6971636000019' }
    ];

    try {
      const res = await fetch('/api/scanner/catalog');
      if (res.ok) {
        const serverPresets = await res.json();
        if (Array.isArray(serverPresets) && serverPresets.length > 0) {
          this.catalogPresets = serverPresets;
        } else {
          this.catalogPresets = builtInPresets;
        }
      } else {
        this.catalogPresets = builtInPresets;
      }
    } catch (e) {
      this.catalogPresets = builtInPresets;
    }
  }

  openCatalogDropdown() {
    const dropdown = document.getElementById('catalogDropdownList');
    if (!dropdown) return;
    const input = document.getElementById('catalogSearchInput');
    this.filterCatalogDropdown(input?.value || '');
  }

  closeCatalogDropdown() {
    const dropdown = document.getElementById('catalogDropdownList');
    if (dropdown) dropdown.classList.add('hidden');
  }

  clearCatalogSearch() {
    const input = document.getElementById('catalogSearchInput');
    const clearBtn = document.getElementById('clearCatalogSearchBtn');
    if (input) {
      input.value = '';
      input.focus();
    }
    if (clearBtn) clearBtn.classList.add('hidden');
    this.filterCatalogDropdown('');
  }

  filterCatalogDropdown(query = '') {
    const dropdown = document.getElementById('catalogDropdownList');
    const clearBtn = document.getElementById('clearCatalogSearchBtn');
    if (!dropdown) return;

    const trimmed = (query || '').trim();
    if (clearBtn) clearBtn.classList.toggle('hidden', trimmed.length === 0);

    const terms = trimmed.toLowerCase().split(/\s+/).filter(Boolean);

    // Map each preset to its original index in this.catalogPresets to prevent ANY index mismatch!
    let matches = this.catalogPresets.map((p, origIdx) => ({ p, origIdx }));

    if (terms.length > 0) {
      matches = matches.filter(({ p }) => {
        const text = `${p.brand} ${p.material} ${p.subtype || ''} ${p.color_name}`.toLowerCase();
        return terms.every(term => text.includes(term));
      });
    }

    // Sort matches: Bambu first, Sunlu second, then alphabetical
    matches.sort((a, b) => {
      const getPrio = (br) => br.includes('Bambu') ? 1 : br.includes('Sunlu') ? 2 : 3;
      const pa = getPrio(a.p.brand);
      const pb = getPrio(b.p.brand);
      if (pa !== pb) return pa - pb;
      return `${a.p.brand} ${a.p.material} ${a.p.color_name}`.localeCompare(`${b.p.brand} ${b.p.material} ${b.p.color_name}`);
    });

    if (matches.length === 0) {
      dropdown.innerHTML = `<div class="p-3 text-center text-xs text-slate-400">Nessun filamento trovato per "${this.escapeHtml(query)}"</div>`;
      dropdown.classList.remove('hidden');
      return;
    }

    dropdown.innerHTML = matches.map(({ p, origIdx }) => {
      const sub = p.subtype ? ` ${this.escapeHtml(p.subtype)}` : '';
      return `
        <div
          class="px-3 py-2.5 hover:bg-indigo-50/20 dark:hover:bg-slate-800/80 cursor-pointer flex items-center justify-between gap-2 transition text-xs select-none"
          onclick="app.selectCatalogPreset(${origIdx})"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-3.5 h-3.5 rounded-full inline-block color-swatch-ring shrink-0 border border-black/10 dark:border-white/20" style="background-color: ${p.color_hex};"></span>
            <span class="font-bold text-slate-900 dark:text-white truncate">
              ${this.escapeHtml(p.brand)} • ${this.escapeHtml(p.material)}${sub}
            </span>
          </div>
          <span class="text-xs text-slate-500 dark:text-slate-400 shrink-0 font-medium">
            ${this.escapeHtml(p.color_name)}
          </span>
        </div>
      `;
    }).join('');

    dropdown.classList.remove('hidden');
  }

  selectCatalogPreset(origIdx) {
    const p = this.catalogPresets[origIdx];
    if (!p) return;

    const input = document.getElementById('catalogSearchInput');
    const sub = p.subtype ? ` ${p.subtype}` : '';
    if (input) {
      input.value = `${p.brand} ${p.material}${sub} - ${p.color_name}`;
    }
    const clearBtn = document.getElementById('clearCatalogSearchBtn');
    if (clearBtn) clearBtn.classList.remove('hidden');
    this.closeCatalogDropdown();

    const data = {
      brand: p.brand,
      material: p.material,
      subtype: p.subtype,
      color_name: p.color_name,
      color_hex: p.color_hex,
      barcode: p.barcode,
      initial_net_weight_g: p.initial_net_weight_g || 1000,
      tare_weight_g: p.tare || p.tare_weight_g || 250,
      nozzle_temp_min: p.nMin || p.nozzle_temp_min,
      nozzle_temp_max: p.nMax || p.nozzle_temp_max,
      bed_temp: p.bed || p.bed_temp,
      k_factor: p.k !== undefined ? p.k : p.k_factor,
      flow_ratio: p.flow !== undefined ? p.flow : p.flow_ratio,
      max_volumetric_speed: p.mvs !== undefined ? p.mvs : p.max_volumetric_speed
    };

    this.applyExtractedSpoolData(data, 'Database Produttori', true);
    this.showToast(`Preset applicato: ${p.brand} ${p.material} ${p.color_name}!`, 'success');
  }

  quickSelectBrand(brandName, defaultTare) {
    const brandInput = document.getElementById('spoolBrand');
    const tareInput = document.getElementById('spoolTare');
    const searchInput = document.getElementById('catalogSearchInput');
    if (brandInput) brandInput.value = brandName;
    if (tareInput) tareInput.value = defaultTare;
    if (searchInput) {
      searchInput.value = `${brandName} `;
      const clearBtn = document.getElementById('clearCatalogSearchBtn');
      if (clearBtn) clearBtn.classList.remove('hidden');
    }
    this.recalculateNetWeight();
    this.openCatalogDropdown();
    this.showToast(`Filtro ${brandName} attivo (Tara: ${defaultTare}g)`, 'info');
  }

  // =========================================================================
  // 4. DATA FETCHING & SYNCHRONIZATION
  // =========================================================================
  async loadSpools() {
    try {
      const res = await fetch('/api/spools');
      if (res.ok) {
        this.spools = await res.json();
        this.updateFilterCounts();
        this.populateBrandFilter();
        this.renderSpoolViews();
      } else if (res.status === 401) {
        this.showLoginModal();
      }
    } catch (err) {
      console.error('Errore caricamento bobine:', err);
      this.showToast('Errore durante il caricamento delle bobine', 'error');
    }
  }

  async loadTares() {
    try {
      const res = await fetch('/api/admin/tares');
      if (res.ok) {
        this.tares = await res.json();
      }
    } catch (err) {
      console.warn('Errore caricamento dizionario tare:', err);
    }
  }

  populateBrandFilter() {
    const select = document.getElementById('brandFilter');
    if (!select) return;
    const brands = Array.from(new Set(this.spools.map(s => s.brand).filter(Boolean))).sort();
    const currentVal = this.brandFilter;
    select.innerHTML = '<option value="">Tutti i Brand</option>' +
      brands.map(b => `<option value="${this.escapeHtml(b)}"${b === currentVal ? ' selected' : ''}>${this.escapeHtml(b)}</option>`).join('');
  }

  // =========================================================================
  // 5. QUICK SORTING (PRODUTTORE, FILAMENTO, SCALA CROMATICA) & HSL HELPERS
  // =========================================================================
  hexToHsl(hex) {
    if (!hex || typeof hex !== 'string') return { h: 0, s: 0, l: 0 };
    let c = hex.replace('#', '').trim();
    if (c.length === 3) c = c.split('').map(x => x + x).join('');
    if (c.length !== 6) return { h: 0, s: 0, l: 0 };
    const r = parseInt(c.substring(0, 2), 16) / 255;
    const g = parseInt(c.substring(2, 4), 16) / 255;
    const b = parseInt(c.substring(4, 6), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0;
    let s = 0;
    const l = (max + min) / 2;

    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h *= 60;
    }
    return { h, s, l };
  }

  hexToSortKey(hex) {
    const { h, s, l } = this.hexToHsl(hex);
    // Acromatic colors: Black, Greys, White (s < 0.12 or very dark l < 0.08 or very light l > 0.94)
    const isAchromatic = s < 0.12 || l < 0.08 || l > 0.94;
    if (isAchromatic) {
      // Group 0: Acromatic (Black -> Grey -> White ordered by lightness)
      return { group: 0, val1: l, val2: s };
    }
    // Group 1: Chromatic (Ordered by Hue angle: 0 Red -> 60 Yellow -> 120 Green -> 180 Cyan -> 240 Blue -> 300 Magenta)
    return { group: 1, val1: h, val2: l };
  }

  setQuickSort(key) {
    if (this.sortBy === key) {
      if (key === 'brand_asc') this.sortBy = 'brand_desc';
      else if (key === 'brand_desc') this.sortBy = 'in_use_desc';
      else if (key === 'material_asc') this.sortBy = 'material_desc';
      else if (key === 'material_desc') this.sortBy = 'in_use_desc';
      else if (key === 'color_chromatic') this.sortBy = 'color_chromatic_desc';
      else if (key === 'color_chromatic_desc') this.sortBy = 'in_use_desc';
      else this.sortBy = 'in_use_desc';
    } else {
      this.sortBy = key;
    }

    this.updateQuickSortUi();
    this.renderSpoolViews();

    const labels = {
      brand_asc: 'Produttore (A-Z)',
      brand_desc: 'Produttore (Z-A)',
      material_asc: 'Filamento (A-Z)',
      material_desc: 'Filamento (Z-A)',
      color_chromatic: 'Scala Cromatica',
      color_chromatic_desc: 'Scala Cromatica (Inversa)',
      in_use_desc: 'Predefinito (In Uso prima)'
    };
    this.showToast(`Ordinato per: ${labels[this.sortBy] || this.sortBy}`, 'info');
  }

  updateQuickSortUi() {
    const brandBtn = document.getElementById('sortBtnBrand');
    const matBtn = document.getElementById('sortBtnMaterial');
    const colorBtn = document.getElementById('sortBtnColor');

    const isBrand = this.sortBy.startsWith('brand');
    const isMat = this.sortBy.startsWith('material');
    const isColor = this.sortBy.startsWith('color_chromatic');

    const setBtnActive = (btn, active) => {
      if (!btn) return;
      if (active) {
        btn.className = 'quick-sort-btn flex flex-col items-center justify-center py-1 px-2 rounded-xl text-indigo-600 dark:text-indigo-400 bg-indigo-50/80 dark:bg-indigo-950/50 font-bold transition flex-1 min-w-0';
      } else {
        btn.className = 'quick-sort-btn flex flex-col items-center justify-center py-1 px-2 rounded-xl text-slate-400 dark:text-slate-400 hover:text-indigo-500 font-semibold transition flex-1 min-w-0';
      }
    };

    setBtnActive(brandBtn, isBrand);
    setBtnActive(matBtn, isMat);
    setBtnActive(colorBtn, isColor);
  }

  navToSpools() {
    this.closeAllModals();
    this.resetDropdownFilters();
    this.setFilterStatus('all');
    this.sortBy = 'in_use_desc';
    this.updateQuickSortUi();
    this.renderSpoolViews();
    const scrollEl = document.getElementById('mainScrollArea');
    if (scrollEl) scrollEl.scrollTo({ top: 0, behavior: 'smooth' });
  }

  closeAllModals() {
    this.closeSpoolDetailModal();
    this.closeSpoolModal();
    this.closeQuickWeighModal();
    this.closeLabelModal();
    this.closeAdminModal();
    this.closeChangePasswordModal();
    this.closeSettingsModal();
    this.closeFiltersSheet();
    this.closeMobileMenuSheet();
    document.body.classList.remove('overflow-hidden');
  }

  syncSearch(val) {
    const searchInput = document.getElementById('searchInput');
    if (searchInput && searchInput.value !== val) searchInput.value = val;
    this.searchQuery = (val || '').trim().toLowerCase();
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.classList.toggle('hidden', !val);
    this.renderSpoolViews();
  }

  openFiltersSheet() {
    const sheet = document.getElementById('filtersSheet');
    if (!sheet) return;

    const matSelect = document.getElementById('materialFilter');
    const brandSelect = document.getElementById('brandFilter');
    const sortSelect = document.getElementById('sortSelector');

    if (matSelect) matSelect.value = this.materialFilter;
    if (brandSelect) brandSelect.value = this.brandFilter;
    if (sortSelect) sortSelect.value = this.sortBy;

    sheet.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    lucide.createIcons();
  }

  closeFiltersSheet() {
    const sheet = document.getElementById('filtersSheet');
    if (sheet) sheet.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  resetDropdownFilters() {
    this.materialFilter = '';
    this.brandFilter = '';
    this.sortBy = 'in_use_desc';

    const matSelect = document.getElementById('materialFilter');
    const brandSelect = document.getElementById('brandFilter');
    const sortSelect = document.getElementById('sortSelector');

    if (matSelect) matSelect.value = '';
    if (brandSelect) brandSelect.value = '';
    if (sortSelect) sortSelect.value = 'in_use_desc';

    this.updateFilterTagsUi();
    this.renderSpoolViews();
    this.showToast('Filtri azzerati', 'info');
  }

  updateFilterTagsUi() {
    const bar = document.getElementById('activeFilterTagsBar');
    const brandTag = document.getElementById('activeBrandTag');
    const brandText = document.getElementById('activeBrandTagText');
    const matTag = document.getElementById('activeMaterialTag');
    const matText = document.getElementById('activeMaterialTagText');
    const activeDot = document.getElementById('activeFiltersDot');

    const hasFilters = !!(this.brandFilter || this.materialFilter);

    if (bar) bar.classList.toggle('hidden', !hasFilters);
    if (activeDot) activeDot.classList.toggle('hidden', !hasFilters);

    if (brandTag && brandText) {
      if (this.brandFilter) {
        brandText.textContent = this.brandFilter;
        brandTag.classList.remove('hidden');
      } else {
        brandTag.classList.add('hidden');
      }
    }

    if (matTag && matText) {
      if (this.materialFilter) {
        matText.textContent = this.materialFilter;
        matTag.classList.remove('hidden');
      } else {
        matTag.classList.add('hidden');
      }
    }
  }

  // =========================================================================
  // 6. DYNAMIC 56px SVG SPOOL RENDERING WITH REMAINING % INSIDE
  // =========================================================================
  renderSpoolSvg(spool, size = 56, showProgressRing = true) {
    const percent = Math.min(100, Math.max(0, Math.round(spool.percent_remaining || 0)));
    const primaryColor = spool.color_hex || '#10b981';
    const secondaryColor = spool.color_hex_secondary;
    const spoolId = spool.id || Math.floor(Math.random() * 10000);
    const gradId = `spoolGrad_${spoolId}`;

    const r = 24;
    const circumference = 2 * Math.PI * r;
    const strokeDashoffset = circumference - (percent / 100) * circumference;

    let ringColor = '#10b981';
    if (percent < 15) ringColor = '#ef4444';
    else if (percent < 35) ringColor = '#f59e0b';

    return `
      <svg width="${size}" height="${size}" viewBox="0 0 56 56" fill="none" class="shrink-0 select-none">
        <defs>
          ${secondaryColor ? `
            <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="${primaryColor}"/>
              <stop offset="100%" stop-color="${secondaryColor}"/>
            </linearGradient>
          ` : `
            <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="${primaryColor}"/>
              <stop offset="100%" stop-color="${primaryColor}"/>
            </linearGradient>
          `}
        </defs>

        <!-- Spool Background -->
        <circle cx="28" cy="28" r="26" fill="#0b0f19" stroke="#1f2937" stroke-width="1.5" />
        <!-- Filament Body -->
        <circle cx="28" cy="28" r="20" fill="url(#${gradId})" opacity="0.85" />
        <!-- Spool Core -->
        <circle cx="28" cy="28" r="14" fill="#0f172a" stroke="#334155" stroke-width="1.5" />

        ${showProgressRing ? `
          <!-- Outer Progress Track -->
          <circle cx="28" cy="28" r="${r}" fill="none" stroke="#1e293b" stroke-width="3" />
          <circle
            cx="28" cy="28" r="${r}"
            fill="none"
            stroke="${ringColor}"
            stroke-width="3"
            stroke-linecap="round"
            stroke-dasharray="${circumference.toFixed(2)}"
            stroke-dashoffset="${strokeDashoffset.toFixed(2)}"
            transform="rotate(-90 28 28)"
            class="transition-all duration-500 ease-out"
          />
        ` : ''}

        <!-- Percentage inside Core -->
        <text cx="28" cy="32" text-anchor="middle" fill="#f8fafc" font-size="10" font-family="ui-monospace, monospace" font-weight="900">${percent}%</text>
      </svg>
    `;
  }

  // =========================================================================
  // 7. SPOOL LIFECYCLE HELPERS
  // =========================================================================
  getSpoolStatus(s) {
    if (!s) return 'new';
    if (s.status === 'opened' || s.status === 'in_use' || s.in_use || (s.opened_at && s.opened_at !== '')) {
      return 'opened';
    }
    return 'new';
  }

  renderStatusBadge(spool) {
    const status = this.getSpoolStatus(spool);
    if (status === 'opened') {
      return `<span class="px-2.5 py-0.5 rounded-lg text-xs font-extrabold badge-status-opened inline-flex items-center">Aperta</span>`;
    }
    return `<span class="px-2.5 py-0.5 rounded-lg text-xs font-extrabold badge-status-new inline-flex items-center">Nuova</span>`;
  }

  async quickSetStatus(spoolId, targetStatus) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;

    try {
      let res = await fetch(`/api/spools/${spoolId}/quick-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: targetStatus, slot_location: '' })
      });

      if (!res.ok) {
        const payload = {
          status: targetStatus,
          in_use: targetStatus === 'opened',
          slot_location: '',
          opened_at: targetStatus === 'opened' ? (spool.opened_at || new Date().toISOString()) : ''
        };
        res = await fetch(`/api/spools/${spoolId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (res.ok) {
        await this.loadSpools();
        this.showToast(targetStatus === 'opened' ? 'Bobina contrassegnata come Aperta' : 'Bobina contrassegnata come Nuova', 'success');
      } else {
        this.showToast('Errore aggiornamento stato', 'error');
      }
    } catch (e) {
      this.showToast('Errore di comunicazione', 'error');
    }
  }

  // =========================================================================
  // 8. MULTI-QUANTITY
  // =========================================================================

  adjustQuantity(delta) {
    const input = document.getElementById('spoolQuantity');
    if (!input) return;
    const cur = parseInt(input.value, 10) || 1;
    input.value = Math.min(50, Math.max(1, cur + delta));
  }

  async cloneSpool(spoolId, quantity = 1) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;

    try {
      let res = await fetch(`/api/spools/${spoolId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity, status: 'new' })
      });

      if (!res.ok) {
        const copyData = {
          brand: spool.brand,
          material: spool.material,
          subtype: spool.subtype || '',
          color_name: spool.color_name,
          color_hex: spool.color_hex,
          barcode: spool.barcode || '',
          initial_net_weight_g: spool.initial_net_weight_g || 1000,
          tare_weight_g: spool.tare_weight_g || 250,
          current_gross_g: (spool.initial_net_weight_g || 1000) + (spool.tare_weight_g || 250),
          low_stock_threshold_g: spool.low_stock_threshold_g || 150,
          price_eur: spool.price_eur || null,
          location_shelf: spool.location_shelf || '',
          in_use: false,
          slot_location: '',
          k_factor: spool.k_factor,
          flow_ratio: spool.flow_ratio,
          max_volumetric_speed: spool.max_volumetric_speed,
          nozzle_temp_min: spool.nozzle_temp_min,
          nozzle_temp_max: spool.nozzle_temp_max,
          bed_temp: spool.bed_temp,
          notes: spool.notes || ''
        };

        res = await fetch('/api/spools', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(copyData)
        });
      }

      if (res.ok) {
        await this.loadSpools();
        this.showToast(`+${quantity} Bobina identica aggiunta in scorta!`, 'success');
      } else {
        this.showToast('Errore durante la duplicazione della bobina', 'error');
      }
    } catch (e) {
      this.showToast('Errore di connessione', 'error');
    }
  }

  cloneCurrentEditingSpool() {
    if (!this.currentEditingSpool) return;
    const id = this.currentEditingSpool.id;
    this.closeSpoolModal();
    this.cloneSpool(id, 1);
  }

  // =========================================================================
  // 9. FILTERING, SORTING & VIEWS
  // =========================================================================
  getFilteredSpools() {
    let result = [...this.spools];

    // Status filter
    if (this.activeFilterStatus === 'opened') {
      result = result.filter(s => this.getSpoolStatus(s) === 'opened');
    } else if (this.activeFilterStatus === 'new') {
      result = result.filter(s => this.getSpoolStatus(s) === 'new');
    }

    // Material filter
    if (this.materialFilter) {
      result = result.filter(s => s.material && s.material.toUpperCase() === this.materialFilter.toUpperCase());
    }

    // Brand filter
    if (this.brandFilter) {
      result = result.filter(s => s.brand === this.brandFilter);
    }

    // Instant Search
    if (this.searchQuery) {
      result = result.filter(s => {
        const text = `${s.uid_code} ${s.brand} ${s.material} ${s.subtype || ''} ${s.color_name || ''} ${s.notes || ''} ${s.barcode || ''}`.toLowerCase();
        return text.includes(this.searchQuery);
      });
    }

    // Sorting
    result.sort((a, b) => {
      switch (this.sortBy) {
        case 'in_use_desc':
          if (a.in_use !== b.in_use) return b.in_use ? 1 : -1;
          return a.uid_code.localeCompare(b.uid_code);
        case 'status_desc': {
          const order = { in_use: 1, opened: 2, new: 3, empty: 4 };
          const sa = order[this.getSpoolStatus(a)] || 5;
          const sb = order[this.getSpoolStatus(b)] || 5;
          if (sa !== sb) return sa - sb;
          return a.uid_code.localeCompare(b.uid_code);
        }
        case 'uid_asc':
          return a.uid_code.localeCompare(b.uid_code);
        case 'net_desc':
          return (b.net_remaining_g || 0) - (a.net_remaining_g || 0);
        case 'net_asc':
          return (a.net_remaining_g || 0) - (b.net_remaining_g || 0);
        case 'brand_asc': {
          const cmp = (a.brand || '').localeCompare(b.brand || '');
          if (cmp !== 0) return cmp;
          const mcmp = (a.material || '').localeCompare(b.material || '');
          if (mcmp !== 0) return mcmp;
          return (a.color_name || '').localeCompare(b.color_name || '');
        }
        case 'brand_desc': {
          const cmp = (b.brand || '').localeCompare(a.brand || '');
          if (cmp !== 0) return cmp;
          const mcmp = (b.material || '').localeCompare(a.material || '');
          if (mcmp !== 0) return mcmp;
          return (b.color_name || '').localeCompare(a.color_name || '');
        }
        case 'material_asc': {
          const cmp = (a.material || '').localeCompare(b.material || '');
          if (cmp !== 0) return cmp;
          const scmp = (a.subtype || '').localeCompare(b.subtype || '');
          if (scmp !== 0) return scmp;
          return (a.brand || '').localeCompare(b.brand || '');
        }
        case 'material_desc': {
          const cmp = (b.material || '').localeCompare(a.material || '');
          if (cmp !== 0) return cmp;
          const scmp = (b.subtype || '').localeCompare(a.subtype || '');
          if (scmp !== 0) return scmp;
          return (b.brand || '').localeCompare(a.brand || '');
        }
        case 'color_chromatic': {
          const ka = this.hexToSortKey(a.color_hex);
          const kb = this.hexToSortKey(b.color_hex);
          if (ka.group !== kb.group) return ka.group - kb.group;
          if (Math.abs(ka.val1 - kb.val1) > 0.01) return ka.val1 - kb.val1;
          return ka.val2 - kb.val2;
        }
        case 'color_chromatic_desc': {
          const ka = this.hexToSortKey(a.color_hex);
          const kb = this.hexToSortKey(b.color_hex);
          if (ka.group !== kb.group) return kb.group - ka.group;
          if (Math.abs(ka.val1 - kb.val1) > 0.01) return kb.val1 - ka.val1;
          return kb.val2 - ka.val2;
        }
        default:
          return 0;
      }
    });

    return result;
  }

  updateFilterCounts() {
    const total = this.spools.length;
    const openedCount = this.spools.filter(s => this.getSpoolStatus(s) === 'opened').length;
    const newCount = this.spools.filter(s => this.getSpoolStatus(s) === 'new').length;

    const elTotal = document.getElementById('countTotal');
    const elOpened = document.getElementById('countOpened');
    const elNew = document.getElementById('countNew');

    if (elTotal) elTotal.textContent = total;
    if (elOpened) elOpened.textContent = openedCount;
    if (elNew) elNew.textContent = newCount;
  }

  setFilterStatus(status) {
    this.activeFilterStatus = status;

    const btnAll = document.getElementById('filterStatusAll');
    const btnOpened = document.getElementById('filterStatusOpened');
    const btnNew = document.getElementById('filterStatusNew');

    if (btnAll) btnAll.classList.toggle('active', status === 'all');
    if (btnOpened) btnOpened.classList.toggle('active', status === 'opened');
    if (btnNew) btnNew.classList.toggle('active', status === 'new');

    this.renderSpoolViews();
  }

  setMaterialFilter(mat) {
    this.materialFilter = mat;
    this.updateFilterTagsUi();
    this.renderSpoolViews();
  }

  setBrandFilter(brand) {
    this.brandFilter = brand;
    this.updateFilterTagsUi();
    this.renderSpoolViews();
  }

  setSorting(sortKey) {
    this.sortBy = sortKey;
    this.renderSpoolViews();
  }

  renderSpoolViews() {
    this.renderSpoolSwipeList();
  }

  // =========================================================================
  // 10. VISTA LISTA SWIPE BILATERALE (NATIVE iOS SWIPE-TO-ACTION)
  // =========================================================================
  renderSpoolSwipeList() {
    const container = document.getElementById('spoolListContainer');
    const emptyState = document.getElementById('emptyGridState');
    if (!container) return;

    const filtered = this.getFilteredSpools();
    if (filtered.length === 0) {
      container.innerHTML = '';
      if (emptyState) emptyState.classList.remove('hidden');
      return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    container.innerHTML = filtered.map(spool => {
      const net = Math.round(spool.net_remaining_g || 0);
      const percent = Math.min(100, Math.max(0, Math.round(spool.percent_remaining || 0)));
      const isOpened = this.getSpoolStatus(spool) === 'opened';

      let weightColorClass = 'text-slate-500 dark:text-slate-400';
      if (percent < 15) {
        weightColorClass = 'text-red-500 dark:text-red-400 font-bold';
      } else if (percent < 30) {
        weightColorClass = 'text-amber-500 dark:text-amber-400';
      }

      return `
        <div class="swipe-item-wrapper border ${isOpened ? 'border-emerald-500/60 shadow-md' : 'border-slate-200 dark:border-slate-800'} relative transition duration-200" id="swipe-item-${spool.id}" data-spool-id="${spool.id}">
          
          <!-- Left Swipe Actions Drawer (160px = 2 x 80px): Pesa + Apri/Nuova -->
          <div class="swipe-actions-left">
            <button
              type="button"
              class="swipe-action-btn swipe-action-weigh"
              onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.openQuickWeighModal(${spool.id});"
              title="Aggiorna peso da bilancia"
            >
              <i data-lucide="scale" class="w-5 h-5"></i>
              <span>Pesa</span>
            </button>

            ${isOpened ? `
              <button
                type="button"
                class="swipe-action-btn swipe-action-seal"
                onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.quickSetStatus(${spool.id}, 'new');"
                title="Segna come Nuova"
              >
                <i data-lucide="package" class="w-5 h-5"></i>
                <span>Nuova</span>
              </button>
            ` : `
              <button
                type="button"
                class="swipe-action-btn swipe-action-open"
                onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.quickSetStatus(${spool.id}, 'opened');"
                title="Segna come Aperta"
              >
                <i data-lucide="unlock" class="w-5 h-5"></i>
                <span>Apri</span>
              </button>
            `}
          </div>

          <!-- Right Swipe Actions Drawer (216px = 3 x 72px): Duplica + Modifica + Elimina -->
          <div class="swipe-actions-right">
            <!-- 1. Duplica -->
            <button
              type="button"
              class="swipe-action-btn swipe-action-clone"
              onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.cloneSpool(${spool.id}, 1);"
              title="Duplica questa bobina"
            >
              <i data-lucide="copy-plus" class="w-5 h-5"></i>
              <span>Duplica</span>
            </button>

            <!-- 2. Modifica -->
            <button
              type="button"
              class="swipe-action-btn swipe-action-edit"
              onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.openSpoolModal(${spool.id});"
              title="Modifica parametri e slicer"
            >
              <i data-lucide="edit-3" class="w-5 h-5"></i>
              <span>Modifica</span>
            </button>

            <!-- 3. Elimina -->
            <button
              type="button"
              class="swipe-action-btn swipe-action-delete"
              onclick="event.stopPropagation(); app.closeAllSwipeRows(); app.confirmDeleteSpool(${spool.id});"
              title="Elimina definitivamente la bobina"
            >
              <i data-lucide="trash-2" class="w-5 h-5"></i>
              <span>Elimina</span>
            </button>
          </div>

          <!-- Foreground Swipeable Content Row (100% Solid & Opaque Background) -->
          <div
            class="swipe-content p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none bg-white dark:bg-[#131c31]"
            style="border-left: 6px solid ${spool.color_hex};"
            onclick="app.handleSwipeRowClick(event, ${spool.id})"
          >
            <!-- Left: Swatch colore elegante w-11 h-11 -->
            <div class="relative shrink-0">
              <span
                class="w-11 h-11 rounded-2xl inline-block color-swatch-ring shadow-inner border border-black/10 dark:border-white/15 shrink-0"
                style="background-color: ${spool.color_hex};"
              ></span>
            </div>

            <!-- Center: 3 Clean Full-Width Rows -->
            <div class="flex-1 min-w-0 space-y-0.5">
              <!-- Riga 1: Produttore + codice SP-xxxx discreto -->
              <div class="flex items-center gap-1.5 truncate">
                ${this.renderBrandLogo(spool.brand, 'sm')}
                <span class="text-[13px] sm:text-sm font-extrabold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 truncate">${this.escapeHtml(spool.brand)}</span>
                <span class="text-[11px] font-mono text-slate-400 dark:text-slate-500 font-semibold shrink-0">${spool.uid_code}</span>
              </div>

              <!-- Riga 2: Materiale e Finitura (stessa dimensione, peso e colore) -->
              <div class="text-[17px] font-extrabold text-slate-900 dark:text-white leading-tight truncate">
                ${this.escapeHtml(spool.material)}${spool.subtype ? ' ' + this.escapeHtml(spool.subtype) : ''}
              </div>

              <!-- Riga 3: Nome Colore a larghezza piena -->
              <div class="text-[15px] font-semibold text-slate-600 dark:text-slate-300 truncate">
                ${this.escapeHtml(spool.color_name || 'Standard')}
              </div>
            </div>

            <!-- Right: Pillola Stato (sopra) + Peso Netto discreto (sotto) -->
            <div class="shrink-0 text-right flex flex-col items-end justify-center gap-1">
              <div>
                ${this.renderStatusBadge(spool)}
              </div>
              <div class="text-xs font-semibold font-mono ${weightColorClass} leading-tight">
                ${net}g <span class="text-[10px] text-slate-400 dark:text-slate-500 font-normal">(${percent}%)</span>
              </div>
            </div>

          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  }

  // =========================================================================
  // 11. iOS BILATERAL SWIPE GESTURES & ACTION CONTROLLERS (160px Left / 216px Right)
  // =========================================================================
  initSwipeGestures() {
    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let isSwipingHorizontal = null;
    let activeWrapper = null;
    let activeContent = null;
    let initialTranslate = 0;
    let didSwipe = false;

    const LEFT_ACTION_WIDTH = 160;  // 2 buttons x 80px (Pesa, Apri/Nuova)
    const RIGHT_ACTION_WIDTH = 216; // 3 buttons x 72px (Duplica, Modifica, Elimina)
    const SNAP_THRESHOLD = 50;

    // Delegated touchstart listener
    document.addEventListener('touchstart', (e) => {
      if (e.target.closest('.swipe-actions, .swipe-actions-left, .swipe-actions-right')) return;

      const wrapper = e.target.closest('.swipe-item-wrapper');
      if (!wrapper) {
        this.closeAllSwipeRows();
        return;
      }

      const openWrapper = document.querySelector('.swipe-item-wrapper.swipe-open, .swipe-item-wrapper.swipe-open-left, .swipe-item-wrapper.swipe-open-right');
      if (openWrapper && openWrapper !== wrapper) {
        this.setSwipeRowState(openWrapper, null);
      }

      activeWrapper = wrapper;
      activeContent = wrapper.querySelector('.swipe-content');
      if (!activeContent) return;

      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;
      currentX = startX;
      isSwipingHorizontal = null;
      didSwipe = false;

      const isOpenLeft = wrapper.classList.contains('swipe-open-left');
      const isOpenRight = wrapper.classList.contains('swipe-open-right') || wrapper.classList.contains('swipe-open');
      initialTranslate = isOpenLeft ? LEFT_ACTION_WIDTH : isOpenRight ? -RIGHT_ACTION_WIDTH : 0;
    }, { passive: true });

    // Delegated touchmove listener
    document.addEventListener('touchmove', (e) => {
      if (!activeWrapper || !activeContent) return;

      const touch = e.touches[0];
      currentX = touch.clientX;
      const deltaX = currentX - startX;
      const deltaY = touch.clientY - startY;

      if (isSwipingHorizontal === null) {
        if (Math.abs(deltaX) > 6 && Math.abs(deltaX) > Math.abs(deltaY)) {
          isSwipingHorizontal = true;
          activeContent.classList.add('swiping');
          this.closeAllSwipeRows(activeWrapper);
        } else if (Math.abs(deltaY) > 6) {
          isSwipingHorizontal = false;
        }
      }

      if (isSwipingHorizontal) {
        if (e.cancelable) e.preventDefault();
        didSwipe = true;

        let targetX = initialTranslate + deltaX;

        // Apply resistance beyond bounds [-RIGHT_ACTION_WIDTH, LEFT_ACTION_WIDTH]
        if (targetX > LEFT_ACTION_WIDTH) {
          targetX = LEFT_ACTION_WIDTH + (targetX - LEFT_ACTION_WIDTH) * 0.2;
        } else if (targetX < -RIGHT_ACTION_WIDTH) {
          targetX = -RIGHT_ACTION_WIDTH + (targetX + RIGHT_ACTION_WIDTH) * 0.2;
        }

        if (targetX > 0) {
          activeWrapper.classList.add('is-swiping-right');
          activeWrapper.classList.remove('is-swiping-left');
        } else if (targetX < 0) {
          activeWrapper.classList.add('is-swiping-left');
          activeWrapper.classList.remove('is-swiping-right');
        } else {
          activeWrapper.classList.remove('is-swiping-left', 'is-swiping-right');
        }

        activeContent.style.transform = `translateX(${targetX}px)`;
      }
    }, { passive: false });

    // Delegated touchend listener
    const onTouchEnd = (e) => {
      if (!activeWrapper || !activeContent) return;

      activeContent.classList.remove('swiping');

      if (isSwipingHorizontal) {
        const deltaX = (e.changedTouches ? e.changedTouches[0].clientX : currentX) - startX;

        if (initialTranslate === 0) {
          if (deltaX > SNAP_THRESHOLD) {
            this.setSwipeRowState(activeWrapper, 'left');
          } else if (deltaX < -SNAP_THRESHOLD) {
            this.setSwipeRowState(activeWrapper, 'right');
          } else {
            this.setSwipeRowState(activeWrapper, null);
          }
        } else if (initialTranslate === LEFT_ACTION_WIDTH) {
          // Was open left
          if (deltaX < -40) {
            this.setSwipeRowState(activeWrapper, null);
          } else {
            this.setSwipeRowState(activeWrapper, 'left');
          }
        } else if (initialTranslate === -RIGHT_ACTION_WIDTH) {
          // Was open right
          if (deltaX > 40) {
            this.setSwipeRowState(activeWrapper, null);
          } else {
            this.setSwipeRowState(activeWrapper, 'right');
          }
        }
      }

      if (didSwipe) {
        activeWrapper._preventClick = true;
        setTimeout(() => {
          if (activeWrapper) activeWrapper._preventClick = false;
        }, 150);
      }

      activeWrapper = null;
      activeContent = null;
      isSwipingHorizontal = null;
    };

    document.addEventListener('touchend', onTouchEnd, { passive: true });
    document.addEventListener('touchcancel', onTouchEnd, { passive: true });
  }

  setSwipeRowState(wrapper, state) {
    if (!wrapper) return;
    const content = wrapper.querySelector('.swipe-content');
    wrapper.classList.remove('is-swiping', 'is-swiping-left', 'is-swiping-right');

    if (state === 'left') {
      this.closeAllSwipeRows(wrapper);
      wrapper.classList.remove('swipe-open', 'swipe-open-right');
      wrapper.classList.add('swipe-open-left');
      if (content) content.style.transform = 'translateX(160px)';
    } else if (state === 'right' || state === true) {
      this.closeAllSwipeRows(wrapper);
      wrapper.classList.remove('swipe-open-left');
      wrapper.classList.add('swipe-open', 'swipe-open-right');
      if (content) content.style.transform = 'translateX(-216px)';
    } else {
      wrapper.classList.remove('swipe-open', 'swipe-open-left', 'swipe-open-right');
      if (content) content.style.transform = 'translateX(0px)';
    }
  }

  closeAllSwipeRows(exceptWrapper = null) {
    document.querySelectorAll('.swipe-item-wrapper.swipe-open, .swipe-item-wrapper.swipe-open-left, .swipe-item-wrapper.swipe-open-right, .swipe-item-wrapper.is-swiping, .swipe-item-wrapper.is-swiping-left, .swipe-item-wrapper.is-swiping-right').forEach(w => {
      if (w !== exceptWrapper) {
        this.setSwipeRowState(w, null);
      }
    });
  }

  toggleSwipeRow(spoolId) {
    const wrapper = document.getElementById(`swipe-item-${spoolId}`);
    if (!wrapper) return;
    const isOpen = wrapper.classList.contains('swipe-open') || wrapper.classList.contains('swipe-open-right') || wrapper.classList.contains('swipe-open-left');
    this.setSwipeRowState(wrapper, isOpen ? null : 'right');
  }

  handleSwipeRowClick(event, spoolId) {
    const wrapper = document.getElementById(`swipe-item-${spoolId}`);
    if (wrapper) {
      if (wrapper._preventClick) {
        wrapper._preventClick = false;
        return;
      }
      if (wrapper.classList.contains('swipe-open') || wrapper.classList.contains('swipe-open-left') || wrapper.classList.contains('swipe-open-right')) {
        this.setSwipeRowState(wrapper, null);
        return;
      }
    }
    this.openSpoolDetailModal(spoolId);
  }

  async confirmDeleteSpool(spoolId) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;
    const uid = spool.uid_code;
    const title = `${spool.brand} ${spool.material} (${uid})`;
    if (!confirm(`Sei sicuro di voler eliminare definitivamente la bobina ${title}?`)) return;

    try {
      const res = await fetch(`/api/spools/${spoolId}`, { method: 'DELETE' });
      if (res.ok) {
        await this.loadSpools();
        this.showToast(`Bobina ${uid} eliminata con successo`, 'info');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Impossibile eliminare la bobina'), 'error');
      }
    } catch (e) {
      this.showToast(this.formatError(e, 'Errore di rete'), 'error');
    }
  }

  // =========================================================================
  // 14. QUICK WEIGH (PESA ORA) MODAL LOGIC
  // =========================================================================
  openQuickWeighModal(spoolId) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;
    this.currentWeighSpool = spool;

    document.getElementById('quickWeighTitle').textContent = `Pesa ${spool.brand} ${spool.material}`;
    document.getElementById('quickWeighUid').textContent = `${spool.uid_code} • Lordo attuale: ${Math.round(spool.current_gross_g)}g`;
    document.getElementById('quickWeighTare').textContent = `${Math.round(spool.tare_weight_g)} g`;

    const input = document.getElementById('quickWeighInput');
    input.value = Math.round(spool.current_gross_g);
    this.updateQuickWeighDelta();

    const modal = document.getElementById('quickWeighModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    setTimeout(() => { input.focus(); input.select(); }, 100);
  }

  closeQuickWeighModal() {
    const modal = document.getElementById('quickWeighModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    this.currentWeighSpool = null;
  }

  adjustQuickWeigh(delta) {
    const input = document.getElementById('quickWeighInput');
    const cur = parseFloat(input.value) || 0;
    input.value = Math.max(0, Math.round(cur + delta));
    this.updateQuickWeighDelta();
  }

  updateQuickWeighDelta() {
    if (!this.currentWeighSpool) return;
    const input = document.getElementById('quickWeighInput');
    const newGross = parseFloat(input.value) || 0;
    const tare = this.currentWeighSpool.tare_weight_g || 0;
    const oldGross = this.currentWeighSpool.current_gross_g || 0;

    const newNet = Math.max(0, Math.round(newGross - tare));
    const delta = Math.round(newGross - oldGross);

    document.getElementById('quickWeighNewNet').textContent = `${newNet} g`;
    const deltaEl = document.getElementById('quickWeighDelta');
    if (delta < 0) {
      deltaEl.textContent = `${delta} g consumati`;
      deltaEl.className = 'text-indigo-400 font-bold';
    } else if (delta > 0) {
      deltaEl.textContent = `+${delta} g ricaricati`;
      deltaEl.className = 'text-emerald-400 font-bold';
    } else {
      deltaEl.textContent = '0 g (invariato)';
      deltaEl.className = 'text-slate-400';
    }
  }

  async saveQuickWeigh() {
    if (!this.currentWeighSpool) return;
    const input = document.getElementById('quickWeighInput');
    const gross_weight_g = parseFloat(input.value);

    if (isNaN(gross_weight_g) || gross_weight_g < 0) {
      this.showToast('Inserisci un peso valido.', 'warning');
      return;
    }

    try {
      const res = await fetch(`/api/spools/${this.currentWeighSpool.id}/quick-weigh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gross_weight_g })
      });

      if (res.ok) {
        const updated = await res.json();
        const spoolObj = updated.spool || updated;

        this.closeQuickWeighModal();
        await this.loadSpools();
        this.showToast(`Pesata aggiornata con successo (${spoolObj.net_remaining_g}g netti)`, 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Errore salvataggio pesata'), 'error');
      }
    } catch (e) {
      this.showToast(this.formatError(e, 'Errore di connessione'), 'error');
    }
  }

  // =========================================================================
  // 15. LABEL PRINTING & BROTHER BLUETOOTH / A4 MODAL
  // =========================================================================
  openLabelModal(spoolId) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;
    this.currentLabelSpool = spool;

    document.getElementById('labelSpoolUid').textContent = `${spool.uid_code} • ${spool.brand} ${spool.material}`;
    const nfcLink = document.getElementById('labelNfcLink');
    if (nfcLink) nfcLink.href = `/s/${spool.uid_code}`;

    this.updateLabelPreview();
    const modal = document.getElementById('labelModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  closeLabelModal() {
    const modal = document.getElementById('labelModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    this.currentLabelSpool = null;
  }

  setLabelTape(mm) {
    this.labelTape = mm;
    [12, 18, 24].forEach(val => {
      const btn = document.getElementById(`tape${val}Btn`);
      if (btn) {
        if (val === mm) {
          btn.className = 'flex-1 py-1 rounded-lg text-center font-mono bg-indigo-600 text-white font-bold';
        } else {
          btn.className = 'flex-1 py-1 rounded-lg text-center font-mono text-slate-400';
        }
      }
    });
    this.updateLabelPreview();
  }

  setLabelCodeType(type) {
    this.labelCodeType = type;
    const barcodeBtn = document.getElementById('codeBarcodeBtn');
    const qrBtn = document.getElementById('codeQrBtn');
    if (type === 'barcode') {
      if (barcodeBtn) barcodeBtn.className = 'flex-1 py-1 rounded-lg text-center bg-indigo-600 text-white font-bold';
      if (qrBtn) qrBtn.className = 'flex-1 py-1 rounded-lg text-center text-slate-400';
    } else {
      if (barcodeBtn) barcodeBtn.className = 'flex-1 py-1 rounded-lg text-center text-slate-400';
      if (qrBtn) qrBtn.className = 'flex-1 py-1 rounded-lg text-center bg-indigo-600 text-white font-bold';
    }
    this.updateLabelPreview();
  }

  updateLabelPreview() {
    if (!this.currentLabelSpool) return;
    const img = document.getElementById('labelPreviewImg');
    if (!img) return;
    const url = `/api/labels/brother/${this.currentLabelSpool.uid_code}?tape_mm=${this.labelTape}&code_type=${this.labelCodeType}&_t=${Date.now()}`;
    img.src = url;
  }

  async shareOrDownloadBrotherLabel() {
    if (!this.currentLabelSpool) return;
    const url = `/api/labels/brother/${this.currentLabelSpool.uid_code}?tape_mm=${this.labelTape}&code_type=${this.labelCodeType}`;
    const filename = `${this.currentLabelSpool.uid_code}_brother_${this.labelTape}mm.png`;

    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const file = new File([blob], filename, { type: 'image/png' });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: `Etichetta ${this.currentLabelSpool.uid_code}`,
          text: `Stampa etichetta per ${this.currentLabelSpool.brand} ${this.currentLabelSpool.material}`
        });
        this.showToast('Etichetta condivisa con successo', 'success');
        return;
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.warn('Web Share fallback to download:', err);
    }

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    this.showToast('Etichetta PNG scaricata per Brother P-touch / iPrint&Label', 'info');
  }

  addCurrentSpoolToA4Queue() {
    if (!this.currentLabelSpool) return;
    const uid = this.currentLabelSpool.uid_code;
    this.a4Queue.push(uid);
    localStorage.setItem('filamenthub_a4_queue', JSON.stringify(this.a4Queue));
    this.updateA4QueueBadge();
    this.showToast(`Aggiunta ${uid} alla coda A4 (${this.a4Queue.length} etichette)`, 'success');
  }

  updateA4QueueBadge() {
    const mobileEl = document.getElementById('mobileMenuA4Badge');
    const count = this.a4Queue.length;
    if (mobileEl) {
      mobileEl.textContent = count;
      mobileEl.classList.toggle('hidden', count === 0);
    }
  }

  // =========================================================================
  // 16. FULL SPOOL MODAL (CREATE / EDIT) & AI INTERACTIVE WIZARD
  // =========================================================================
  setModalStatusChoice(choice) {
    const hiddenInput = document.getElementById('spoolInitialStatus');
    if (hiddenInput) hiddenInput.value = choice;

    const btnNew = document.getElementById('statusBtnNew');
    const btnOpened = document.getElementById('statusBtnOpened');

    if (btnNew && btnOpened) {
      if (choice === 'opened') {
        btnOpened.className = 'py-2.5 px-3 rounded-xl border font-bold text-xs flex items-center justify-center gap-1.5 transition bg-emerald-950/80 border-emerald-500 text-emerald-300 shadow-sm';
        btnNew.className = 'py-2.5 px-3 rounded-xl border font-medium text-xs flex items-center justify-center gap-1.5 transition bg-slate-900 border-slate-700 text-slate-400';
      } else {
        btnNew.className = 'py-2.5 px-3 rounded-xl border font-bold text-xs flex items-center justify-center gap-1.5 transition bg-blue-950/80 border-blue-500 text-blue-300 shadow-sm';
        btnOpened.className = 'py-2.5 px-3 rounded-xl border font-medium text-xs flex items-center justify-center gap-1.5 transition bg-slate-900 border-slate-700 text-slate-400';
      }
    }
  }

  openSpoolModal(spoolId) {
    this.currentEditingSpool = spoolId ? this.spools.find(s => s.id === spoolId) : null;
    const isEdit = !!this.currentEditingSpool;

    const titleEl = document.getElementById('spoolModalTitle');
    const subtitleEl = document.getElementById('spoolModalSubtitle');
    if (titleEl) titleEl.textContent = isEdit ? `Modifica Bobina ${this.currentEditingSpool.uid_code}` : 'Nuova Bobina';
    if (subtitleEl) subtitleEl.textContent = isEdit ? 'Aggiorna pesi, temperature e parametri slicer' : 'Registra una nuova bobina nel catalogo';
    
    const delBtn = document.getElementById('spoolDeleteBtn');
    if (delBtn) delBtn.classList.toggle('hidden', !isEdit);

    const aiBar = document.getElementById('spoolModalAiBar');
    if (aiBar) aiBar.classList.toggle('hidden', isEdit);
    this.updateSettingsUi();

    const catalogBox = document.getElementById('spoolModalCatalogBox');
    if (catalogBox) catalogBox.classList.toggle('hidden', isEdit);

    this.closeAiCanvasBox();
    this.closeCatalogDropdown();
    this.hideMissingFieldsDialog();
    const extBanner = document.getElementById('aiExtractionBanner');
    if (extBanner) extBanner.classList.add('hidden');

    this.setSpoolModalTab(1);

    const catalogInput = document.getElementById('catalogSearchInput');
    if (catalogInput) catalogInput.value = '';
    const clearCatalogBtn = document.getElementById('clearCatalogSearchBtn');
    if (clearCatalogBtn) clearCatalogBtn.classList.add('hidden');

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val !== null && val !== undefined ? val : '';
    };

    if (isEdit) {
      const s = this.currentEditingSpool;
      const currentStatus = this.getSpoolStatus(s); // 'opened' or 'new'
      this.setModalStatusChoice(currentStatus);

      setVal('spoolFormId', s.id);
      setVal('spoolBrand', s.brand);
      setVal('spoolMaterial', s.material);
      setVal('spoolSubtype', s.subtype);
      setVal('spoolColorName', s.color_name);
      setVal('spoolColorHex', s.color_hex || '#10b981');
      setVal('spoolColorPicker', s.color_hex || '#10b981');
      setVal('spoolBarcode', s.barcode);
      setVal('spoolNetInitial', s.initial_net_weight_g || 1000);
      setVal('spoolTare', s.tare_weight_g || 250);
      setVal('spoolGross', s.current_gross_g || 1250);
      setVal('spoolLowStockThreshold', s.low_stock_threshold_g || 150);
      setVal('spoolPrice', s.price_eur);
      setVal('spoolLocationShelf', s.location_shelf);

      // Tab 2 fields
      setVal('spoolKFactor', s.k_factor);
      setVal('spoolFlowRatio', s.flow_ratio);
      setVal('spoolMVS', s.max_volumetric_speed);
      setVal('spoolNozzleMin', s.nozzle_temp_min);
      setVal('spoolNozzleMax', s.nozzle_temp_max);
      setVal('spoolBedTemp', s.bed_temp);
      setVal('spoolNotes', s.notes);
    } else {
      const form = document.getElementById('spoolForm');
      if (form) form.reset();

      setVal('spoolFormId', '');
      this.setModalStatusChoice('new');
      setVal('spoolColorHex', '#10b981');
      setVal('spoolColorPicker', '#10b981');
      setVal('spoolNetInitial', 1000);
      setVal('spoolTare', 250);
      setVal('spoolGross', 1250);
      setVal('spoolLowStockThreshold', 150);
    }

    this.recalculateNetWeight();
    const modal = document.getElementById('spoolModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  closeSpoolModal() {
    const modal = document.getElementById('spoolModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    this.closeCatalogDropdown();
    this.currentEditingSpool = null;
  }

  // =========================================================================
  // READ-ONLY TECH SHEET (SCHEDA DETTAGLIO BOBINA)
  // =========================================================================
  openSpoolDetailModal(spoolId) {
    const spool = this.spools.find(s => s.id === spoolId);
    if (!spool) return;

    this.currentDetailSpoolId = spoolId;
    const modal = document.getElementById('spoolDetailModal');
    if (!modal) return;

    const net = Math.round(spool.net_remaining_g || 0);
    const gross = Math.round(spool.current_gross_g || 0);
    const tare = Math.round(spool.tare_weight_g || 0);
    const percent = Math.min(100, Math.max(0, Math.round(spool.percent_remaining || 0)));
    const isOpened = this.getSpoolStatus(spool) === 'opened';

    // Color Swatch
    const swatchEl = document.getElementById('detailSpoolSwatch');
    if (swatchEl) {
      swatchEl.style.backgroundColor = spool.color_hex || '#10b981';
      swatchEl.title = spool.color_hex || '';
    }

    // Title & Status Badge
    const titleEl = document.getElementById('detailSpoolTitle');
    if (titleEl) {
      titleEl.textContent = `${spool.material || 'Filamento'}${spool.subtype ? ' (' + spool.subtype + ')' : ''} - ${spool.color_name || 'Standard'}`;
    }

    const badgeEl = document.getElementById('detailSpoolStatusBadge');
    if (badgeEl) {
      badgeEl.className = isOpened
        ? 'text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-950 text-emerald-400 border border-emerald-800'
        : 'text-[10px] px-2 py-0.5 rounded-full font-bold bg-blue-950 text-blue-400 border border-blue-800';
      badgeEl.textContent = isOpened ? 'In Uso / Aperta' : 'Nuova / Sigillata';
    }

    // Subtitle
    const subEl = document.getElementById('detailSpoolSubtitle');
    if (subEl) {
      subEl.textContent = `${spool.brand || 'Generico'} • ${spool.uid_code || ''}`;
    }

    // Weight & Progress
    const pctEl = document.getElementById('detailSpoolPercent');
    const barEl = document.getElementById('detailSpoolProgressBar');
    if (pctEl) pctEl.textContent = `${percent}%`;
    if (barEl) {
      barEl.style.width = `${percent}%`;
      barEl.className = percent < 15 ? 'bg-red-500 h-2.5 rounded-full transition-all duration-300'
                      : percent < 35 ? 'bg-amber-500 h-2.5 rounded-full transition-all duration-300'
                      : 'bg-emerald-500 h-2.5 rounded-full transition-all duration-300';
    }

    const netEl = document.getElementById('detailSpoolNetG');
    const grossEl = document.getElementById('detailSpoolGrossG');
    const tareEl = document.getElementById('detailSpoolTareG');
    if (netEl) netEl.textContent = `${net}g`;
    if (grossEl) grossEl.textContent = `${gross}g`;
    if (tareEl) tareEl.textContent = `${tare}g`;

    // Temperatures
    const nozzleEl = document.getElementById('detailSpoolNozzleTemp');
    const bedEl = document.getElementById('detailSpoolBedTemp');
    if (nozzleEl) {
      const minN = spool.nozzle_temp_min;
      const maxN = spool.nozzle_temp_max;
      nozzleEl.textContent = minN && maxN ? `${minN} - ${maxN} °C` : minN ? `${minN} °C` : maxN ? `${maxN} °C` : 'Non specificata';
    }
    if (bedEl) {
      bedEl.textContent = spool.bed_temp ? `${spool.bed_temp} °C` : 'Non specificata';
    }

    // Slicer calibration
    const kEl = document.getElementById('detailSpoolKFactor');
    const flowEl = document.getElementById('detailSpoolFlowRatio');
    const mvsEl = document.getElementById('detailSpoolMvs');
    if (kEl) kEl.textContent = spool.k_factor !== null && spool.k_factor !== undefined ? spool.k_factor : '--';
    if (flowEl) flowEl.textContent = spool.flow_ratio !== null && spool.flow_ratio !== undefined ? spool.flow_ratio : '--';
    if (mvsEl) mvsEl.textContent = spool.max_volumetric_speed ? `${spool.max_volumetric_speed} mm³/s` : '--';

    // Logistics & Barcode & Notes
    const locEl = document.getElementById('detailSpoolLocation');
    const priceEl = document.getElementById('detailSpoolPrice');
    if (locEl) {
      const loc = [spool.slot_location, spool.location_shelf].filter(Boolean).join(' - ');
      locEl.textContent = loc || 'Nessuna assegnata';
    }
    if (priceEl) {
      priceEl.textContent = spool.price_eur ? `€ ${Number(spool.price_eur).toFixed(2)}` : '--';
    }

    const barcodeBox = document.getElementById('detailSpoolBarcodeBox');
    const barcodeEl = document.getElementById('detailSpoolBarcode');
    if (barcodeEl) barcodeEl.textContent = spool.barcode || '--';
    if (barcodeBox) barcodeBox.classList.toggle('hidden', !spool.barcode);

    const notesBox = document.getElementById('detailSpoolNotesBox');
    const notesEl = document.getElementById('detailSpoolNotes');
    if (notesEl) notesEl.textContent = spool.notes || '';
    if (notesBox) notesBox.classList.toggle('hidden', !spool.notes || !spool.notes.trim());

    // Action buttons
    const btnWeigh = document.getElementById('detailBtnWeigh');
    const btnLabel = document.getElementById('detailBtnLabel');
    const btnEdit = document.getElementById('detailBtnEdit');

    if (btnWeigh) btnWeigh.onclick = () => { this.closeSpoolDetailModal(); this.openQuickWeighModal(spool.id); };
    if (btnLabel) btnLabel.onclick = () => { this.closeSpoolDetailModal(); this.openLabelModal(spool.id); };
    if (btnEdit) btnEdit.onclick = () => { this.closeSpoolDetailModal(); this.openSpoolModal(spool.id); };

    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
    lucide.createIcons();
  }

  closeSpoolDetailModal() {
    const modal = document.getElementById('spoolDetailModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    this.currentDetailSpoolId = null;
  }

  setSpoolModalTab(tabNum) {
    const tab1Btn = document.getElementById('tabBtn1');
    const tab2Btn = document.getElementById('tabBtn2');
    const tab1Content = document.getElementById('spoolTab1Content');
    const tab2Content = document.getElementById('spoolTab2Content');

    if (tabNum === 1) {
      if (tab1Btn) tab1Btn.className = 'pb-2 border-b-2 border-indigo-500 text-indigo-400 font-bold flex items-center gap-1.5';
      if (tab2Btn) tab2Btn.className = 'pb-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 font-semibold flex items-center gap-1.5';
      if (tab1Content) tab1Content.classList.remove('hidden');
      if (tab2Content) tab2Content.classList.add('hidden');
    } else {
      if (tab1Btn) tab1Btn.className = 'pb-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 font-semibold flex items-center gap-1.5';
      if (tab2Btn) tab2Btn.className = 'pb-2 border-b-2 border-indigo-500 text-indigo-400 font-bold flex items-center gap-1.5';
      if (tab1Content) tab1Content.classList.add('hidden');
      if (tab2Content) tab2Content.classList.remove('hidden');
    }
  }

  recalculateNetWeight() {
    const tare = parseFloat(document.getElementById('spoolTare')?.value) || 0;
    const gross = parseFloat(document.getElementById('spoolGross')?.value) || 0;
    const initial = parseFloat(document.getElementById('spoolNetInitial')?.value) || 1000;
    const net = Math.max(0, Math.round(gross - tare));
    const percent = initial > 0 ? Math.min(100, Math.max(0, Math.round((net / initial) * 100))) : 0;

    const badge = document.getElementById('spoolNetCalculatedBadge');
    if (badge) {
      badge.innerHTML = `<span class="text-sm font-bold text-emerald-300 font-mono">${net} g netti</span><span class="text-xs text-emerald-400 font-mono">${percent}% residuo</span>`;
    }
  }

  handleBrandSelect(brandName) {
    const matchedTare = this.tares.find(t => t.brand_name.toLowerCase() === brandName.toLowerCase());
    if (matchedTare && matchedTare.tare_weight_g) {
      const tareInput = document.getElementById('spoolTare');
      if (tareInput) tareInput.value = matchedTare.tare_weight_g;
      this.recalculateNetWeight();
      this.showToast(`Tara impostata per ${matchedTare.brand_name}: ${matchedTare.tare_weight_g}g`, 'info');
    }
  }

  // =========================================================================
  // UNIFIED EXTRACTION & MISSING FIELDS PROMPT WIZARD
  // =========================================================================
  applyExtractedSpoolData(data, sourceLabel = 'AI Vision', isFromCatalog = false) {
    if (!data) return;

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null && String(val).trim() !== '') {
        el.value = val;
      }
    };

    if (data.brand) {
      setVal('spoolBrand', data.brand);
    }
    if (data.material) setVal('spoolMaterial', data.material);
    if (data.subtype) setVal('spoolSubtype', data.subtype);
    if (data.color_name) setVal('spoolColorName', data.color_name);
    if (data.color_hex) {
      setVal('spoolColorHex', data.color_hex);
      setVal('spoolColorPicker', data.color_hex);
      this.activeEyedropperHex = data.color_hex;
      const swatch = document.getElementById('eyedropperMiniSwatch');
      const hexText = document.getElementById('eyedropperHex');
      if (swatch) swatch.style.background = data.color_hex;
      if (hexText) hexText.textContent = data.color_hex.toUpperCase();
    }
    if (data.barcode) setVal('spoolBarcode', data.barcode);

    const net = data.initial_net_weight_g || 1000;
    const tare = data.tare_weight_g || 250;
    setVal('spoolNetInitial', net);
    setVal('spoolTare', tare);
    setVal('spoolGross', net + tare);

    if (data.nozzle_temp_min) setVal('spoolNozzleMin', data.nozzle_temp_min);
    if (data.nozzle_temp_max) setVal('spoolNozzleMax', data.nozzle_temp_max);
    if (data.bed_temp) setVal('spoolBedTemp', data.bed_temp);
    if (data.k_factor !== null && data.k_factor !== undefined) setVal('spoolKFactor', data.k_factor);
    if (data.flow_ratio !== null && data.flow_ratio !== undefined) setVal('spoolFlowRatio', data.flow_ratio);
    if (data.max_volumetric_speed) setVal('spoolMVS', data.max_volumetric_speed);

    this.recalculateNetWeight();

    // Show extraction banner
    const banner = document.getElementById('aiExtractionBanner');
    const titleEl = document.getElementById('aiExtractionTitle');
    const summaryEl = document.getElementById('aiExtractionSummary');
    if (banner && summaryEl) {
      const brand = data.brand || 'Filamento';
      const mat = data.material || '';
      const col = data.color_name ? ` • ${data.color_name}` : '';
      const code = data.barcode ? ` • Barcode: ${data.barcode}` : '';
      const tareStr = data.tare_weight_g ? ` • Tara: ${Math.round(data.tare_weight_g)}g` : '';
      if (titleEl) titleEl.textContent = `✨ Riconosciuto da ${sourceLabel}`;
      summaryEl.textContent = `${brand} ${mat}${col}${code}${tareStr}`;
      banner.classList.remove('hidden');
    }

    // Check missing fields
    const missing = Array.isArray(data.missing_fields) ? [...data.missing_fields] : [];
    if (!document.getElementById('spoolBrand')?.value?.trim() && !missing.includes('brand')) missing.push('brand');
    if (!document.getElementById('spoolMaterial')?.value?.trim() && !missing.includes('material')) missing.push('material');
    if (!document.getElementById('spoolColorName')?.value?.trim() && !missing.includes('color_name')) missing.push('color_name');

    if (missing.length > 0) {
      this.promptMissingFields(missing);
    } else {
      this.hideMissingFieldsDialog();
    }
  }

  promptMissingFields(missingList) {
    this.missingFields = missingList;
    this.missingSelections = {};

    const dialog = document.getElementById('aiMissingFieldsDialog');
    const container = document.getElementById('missingFieldsContainer');
    if (!dialog || !container) return;

    let html = '';

    if (missingList.includes('brand')) {
      html += `
        <div class="space-y-1">
          <label class="block text-[11px] font-semibold text-amber-300">Marca / Produttore:</label>
          <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-nowrap py-0.5">
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'Bambu Lab', 250)" class="missing-chip-btn shrink-0">🌿 Bambu Lab</button>
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'Sunlu', 195)" class="missing-chip-btn shrink-0">☀️ Sunlu</button>
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'eSUN', 240)" class="missing-chip-btn shrink-0">eSUN</button>
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'Polymaker', 140)" class="missing-chip-btn shrink-0">Polymaker</button>
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'Elegoo', 160)" class="missing-chip-btn shrink-0">Elegoo</button>
            <button type="button" onclick="app.pickMissingFieldValue('brand', 'Creality', 200)" class="missing-chip-btn shrink-0">Creality</button>
          </div>
          <input type="text" id="missingInputBrand" placeholder="Oppure scrivi marca..." class="w-full px-2.5 py-1.5 bg-[#0b0f19] border border-amber-800/80 rounded-lg text-white text-xs mt-1">
        </div>
      `;
    }

    if (missingList.includes('material')) {
      html += `
        <div class="space-y-1 pt-1">
          <label class="block text-[11px] font-semibold text-amber-300">Materiale:</label>
          <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-nowrap py-0.5">
            <button type="button" onclick="app.pickMissingFieldValue('material', 'PLA')" class="missing-chip-btn shrink-0">PLA</button>
            <button type="button" onclick="app.pickMissingFieldValue('material', 'PLA+')" class="missing-chip-btn shrink-0">PLA+</button>
            <button type="button" onclick="app.pickMissingFieldValue('material', 'PETG')" class="missing-chip-btn shrink-0">PETG</button>
            <button type="button" onclick="app.pickMissingFieldValue('material', 'ABS')" class="missing-chip-btn shrink-0">ABS</button>
            <button type="button" onclick="app.pickMissingFieldValue('material', 'ASA')" class="missing-chip-btn shrink-0">ASA</button>
            <button type="button" onclick="app.pickMissingFieldValue('material', 'TPU')" class="missing-chip-btn shrink-0">TPU</button>
          </div>
          <input type="text" id="missingInputMaterial" placeholder="Oppure scrivi materiale..." class="w-full px-2.5 py-1.5 bg-[#0b0f19] border border-amber-800/80 rounded-lg text-white text-xs mt-1">
        </div>
      `;
    }

    if (missingList.includes('color_name')) {
      html += `
        <div class="space-y-1 pt-1">
          <label class="block text-[11px] font-semibold text-amber-300">Nome Colore:</label>
          <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-nowrap py-0.5">
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Black', '#111111')" class="missing-chip-btn shrink-0">⚫ Black</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'White', '#ffffff')" class="missing-chip-btn shrink-0">⚪ White</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Grey', '#64748b')" class="missing-chip-btn shrink-0">🔘 Grey</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Blue', '#2563eb')" class="missing-chip-btn shrink-0">🔵 Blue</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Red', '#dc2626')" class="missing-chip-btn shrink-0">🔴 Red</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Green', '#16a34a')" class="missing-chip-btn shrink-0">🟢 Green</button>
            <button type="button" onclick="app.pickMissingFieldValue('color_name', 'Orange', '#ea580c')" class="missing-chip-btn shrink-0">🟠 Orange</button>
          </div>
          <input type="text" id="missingInputColorName" placeholder="es. Charcoal Black, Jade White..." class="w-full px-2.5 py-1.5 bg-[#0b0f19] border border-amber-800/80 rounded-lg text-white text-xs mt-1">
        </div>
      `;
    }

    container.innerHTML = html;
    dialog.classList.remove('hidden');

    const form = document.getElementById('spoolForm');
    if (form) form.scrollTo({ top: 0, behavior: 'smooth' });
  }

  pickMissingFieldValue(field, val, extra = null) {
    this.missingSelections[field] = { val, extra };
    const inputMap = {
      brand: 'missingInputBrand',
      material: 'missingInputMaterial',
      color_name: 'missingInputColorName'
    };
    const input = document.getElementById(inputMap[field]);
    if (input) input.value = val;
    this.showToast(`Selezionato: ${val}`, 'info');
  }

  applyMissingFieldsPrompt() {
    const brandInput = document.getElementById('missingInputBrand')?.value?.trim();
    const matInput = document.getElementById('missingInputMaterial')?.value?.trim();
    const colInput = document.getElementById('missingInputColorName')?.value?.trim();

    if (brandInput) {
      document.getElementById('spoolBrand').value = brandInput;
      const tare = this.missingSelections.brand?.extra || (brandInput.toLowerCase().includes('sunlu') ? 195 : 250);
      document.getElementById('spoolTare').value = tare;
    }

    if (matInput) {
      document.getElementById('spoolMaterial').value = matInput.toUpperCase();
    }

    if (colInput) {
      document.getElementById('spoolColorName').value = colInput;
      const hex = this.missingSelections.color_name?.extra;
      if (hex) {
        document.getElementById('spoolColorHex').value = hex;
        document.getElementById('spoolColorPicker').value = hex;
      }
    }

    this.recalculateNetWeight();
    this.hideMissingFieldsDialog();
    this.showToast('✨ Dati mancanti applicati con successo!', 'success');
  }

  skipMissingFieldsPrompt() {
    this.hideMissingFieldsDialog();
    const colorInput = document.getElementById('spoolColorName');
    if (colorInput && !colorInput.value.trim()) {
      colorInput.value = 'Standard';
    }
    this.showToast('Informazioni mancanti saltate. Puoi procedere al salvataggio.', 'info');
  }

  hideMissingFieldsDialog() {
    const dialog = document.getElementById('aiMissingFieldsDialog');
    if (dialog) dialog.classList.add('hidden');
    this.missingFields = [];
    this.missingSelections = {};
  }

  async handleSaveSpool(event) {
    event.preventDefault();
    const id = document.getElementById('spoolFormId')?.value;
    const isEdit = !!id;

    // Ensure color name is never empty if user skipped missing fields
    const colorInput = document.getElementById('spoolColorName');
    if (colorInput && !colorInput.value.trim()) {
      colorInput.value = 'Standard';
    }

    const chosenStatus = document.getElementById('spoolInitialStatus')?.value || 'new';
    const isOpened = chosenStatus === 'opened';

    const getStr = (id) => {
      const el = document.getElementById(id);
      return el ? (el.value.trim() || null) : null;
    };

    const spoolData = {
      brand: getStr('spoolBrand') || 'Generico',
      material: (getStr('spoolMaterial') || 'PLA').toUpperCase(),
      subtype: getStr('spoolSubtype') || '',
      color_name: getStr('spoolColorName') || 'Standard',
      color_hex: getStr('spoolColorHex') || '#10b981',
      barcode: getStr('spoolBarcode') || '',
      initial_net_weight_g: parseFloat(document.getElementById('spoolNetInitial')?.value) || 1000.0,
      tare_weight_g: parseFloat(document.getElementById('spoolTare')?.value) || 250.0,
      current_gross_g: parseFloat(document.getElementById('spoolGross')?.value) || 1250.0,
      low_stock_threshold_g: parseFloat(document.getElementById('spoolLowStockThreshold')?.value) || 150.0,
      price_eur: parseFloat(document.getElementById('spoolPrice')?.value) || 0.0,
      location_shelf: getStr('spoolLocationShelf') || '',
      status: chosenStatus,
      in_use: isOpened,
      slot_location: '',
      opened_at: isOpened ? (this.currentEditingSpool?.opened_at || new Date().toISOString()) : '',

      // Calibrazione & Slicer con valori numerici di default sicuri
      k_factor: parseFloat(document.getElementById('spoolKFactor')?.value) || 0.020,
      flow_ratio: parseFloat(document.getElementById('spoolFlowRatio')?.value) || 0.98,
      max_volumetric_speed: parseFloat(document.getElementById('spoolMVS')?.value) || 15.0,
      nozzle_temp_min: parseInt(document.getElementById('spoolNozzleMin')?.value, 10) || 200,
      nozzle_temp_max: parseInt(document.getElementById('spoolNozzleMax')?.value, 10) || 220,
      bed_temp: parseInt(document.getElementById('spoolBedTemp')?.value, 10) || 60,
      notes: getStr('spoolNotes') || ''
    };

    try {
      const url = isEdit ? `/api/spools/${id}` : '/api/spools';
      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spoolData)
      });

      if (res.ok) {
        this.closeSpoolModal();
        await this.loadSpools();
        this.showToast(isEdit ? 'Bobina aggiornata con successo!' : 'Bobina creata con successo!', 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Errore salvataggio bobina'), 'error');
      }
    } catch (e) {
      this.showToast(this.formatError(e, 'Errore di comunicazione con il server'), 'error');
    }
  }

  async handleDeleteCurrentSpool() {
    if (!this.currentEditingSpool) return;
    const spoolId = this.currentEditingSpool.id;
    this.closeSpoolModal();
    await this.confirmDeleteSpool(spoolId);
  }

  // =========================================================================
  // 17. AI VISION (GEMINI 3.5 FLASH LITE PHOTO CAPTURE)
  // =========================================================================
  async handleNativeCameraPhoto(event) {
    if (!this.settings?.gemini_configured) {
      if (event.target) event.target.value = '';
      this.showToast('Inserisci prima una API Key Gemini valida nelle Impostazioni.', 'warning');
      return;
    }
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    this.showToast('Foto acquisita! Avvio analisi con Gemini Flash...', 'info');
    await this.loadImageBlobToCanvas(file);
    const modal = document.getElementById('spoolModal');
    if (modal && modal.classList.contains('hidden')) {
      this.openSpoolModal(null);
    }
    await this.analyzeImageWithGemini();
    event.target.value = '';
  }

  async handleAiPhotoUpload(event) {
    if (!this.settings?.gemini_configured) {
      if (event.target) event.target.value = '';
      this.showToast('Inserisci prima una API Key Gemini valida nelle Impostazioni.', 'warning');
      return;
    }
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    this.showToast('Foto caricata! Avvio analisi con Gemini Flash...', 'info');
    await this.loadImageBlobToCanvas(file);
    const modal = document.getElementById('spoolModal');
    if (modal && modal.classList.contains('hidden')) {
      this.openSpoolModal(null);
    }
    await this.analyzeImageWithGemini();
    event.target.value = '';
  }

  loadImageBlobToCanvas(blob) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.getElementById('aiCanvas');
          const box = document.getElementById('aiCanvasBox');
          if (!canvas) { resolve(); return; }

          const maxDim = 1024;
          let w = img.width;
          let h = img.height;
          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }

          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, w, h);

          this.aiImageBase64 = canvas.toDataURL('image/jpeg', 0.88);
          if (box) box.classList.remove('hidden');
          resolve();
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(blob);
    });
  }

  closeAiCanvasBox() {
    const box = document.getElementById('aiCanvasBox');
    if (box) box.classList.add('hidden');
    this.aiImageBase64 = null;
  }

  toggleCanvasExpand() {
    const canvas = document.getElementById('aiCanvas');
    const text = document.getElementById('canvasExpandText');
    if (!canvas) return;

    const isExpanded = canvas.classList.contains('max-h-64');
    if (isExpanded) {
      canvas.className = 'h-20 w-auto max-w-[120px] object-contain cursor-crosshair';
      if (text) text.textContent = 'Ingrandisci Colore';
    } else {
      canvas.className = 'max-h-64 w-full object-contain cursor-crosshair';
      if (text) text.textContent = 'Riduci';
      this.showToast('Tocca col dito un punto della bobina per campionare il colore!', 'info');
    }
  }

  handleCanvasEyedropper(event) {
    const canvas = document.getElementById('aiCanvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX - rect.left) * (canvas.width / rect.width));
    const y = Math.floor((event.clientY - rect.top) * (canvas.height / rect.height));

    const ctx = canvas.getContext('2d');
    const pixel = ctx.getImageData(x, y, 1, 1).data;
    const hex = '#' + ((1 << 24) + (pixel[0] << 16) + (pixel[1] << 8) + pixel[2]).toString(16).slice(1);

    this.activeEyedropperHex = hex;
    const swatch = document.getElementById('eyedropperMiniSwatch');
    const hexText = document.getElementById('eyedropperHex');
    if (swatch) swatch.style.background = hex;
    if (hexText) hexText.textContent = hex.toUpperCase();
    this.applyEyedropperColor();
  }

  applyEyedropperColor() {
    const hexInput = document.getElementById('spoolColorHex');
    const pickerInput = document.getElementById('spoolColorPicker');
    if (hexInput) hexInput.value = this.activeEyedropperHex;
    if (pickerInput) pickerInput.value = this.activeEyedropperHex;
    this.showToast(`Colore impostato: ${this.activeEyedropperHex}`, 'info');
  }

  async analyzeImageWithGemini() {
    if (!this.settings?.gemini_configured) {
      this.showToast('API Gemini non configurata! Specifica una chiave valida nelle Impostazioni.', 'warning');
      return;
    }

    if (!this.aiImageBase64) {
      const canvas = document.getElementById('aiCanvas');
      if (canvas && canvas.width > 0) {
        this.aiImageBase64 = canvas.toDataURL('image/jpeg', 0.88);
      }
    }

    if (!this.aiImageBase64) {
      this.showToast('Nessuna immagine fornita. Scatta o carica una foto.', 'warning');
      return;
    }

    const btn = document.getElementById('geminiAnalyzeBtn');
    const statusText = document.getElementById('geminiStatusText');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="inline-block animate-spin mr-1.5">⟳</span> Analisi...';
    }
    if (statusText) statusText.textContent = 'Elaborazione Vision AI in corso...';

    try {
      const res = await fetch('/api/scanner/vision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: this.aiImageBase64,
          mime_type: 'image/jpeg'
        })
      });

      if (res.ok) {
        const data = await res.json();

        if (data.configured === false) {
          this.settings.gemini_configured = false;
          this.updateSettingsUi();
          this.showToast('API Gemini non configurata! Inserisci la tua chiave gratuita.', 'warning');
          this.openSettingsModal();
          return;
        }

        this.applyExtractedSpoolData(data, 'Gemini Vision AI');
        if (statusText) statusText.textContent = '✅ Dati estratti da Gemini Flash';
        this.showToast('Dati estratti con successo da Gemini Flash!', 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        if (res.status === 400 && String(err.detail).includes('GEMINI_API_KEY')) {
          this.settings.gemini_configured = false;
          this.updateSettingsUi();
          this.showToast('Chiave Gemini mancante o non valida! Clicca su Impostazioni.', 'warning');
          this.openSettingsModal();
        } else {
          this.showToast(this.formatError(err, 'Impossibile estrarre i dati dall\'etichetta'), 'warning');
        }
      }
    } catch (e) {
      this.showToast(this.formatError(e, 'Errore di comunicazione con il servizio Vision AI'), 'error');
    } finally {
      if (btn) {
        btn.disabled = !this.settings?.gemini_configured;
        btn.innerHTML = '<i data-lucide="cpu" class="w-3 h-3"></i><span>Rianalizza AI</span>';
        lucide.createIcons();
      }
    }
  }

  // =========================================================================
  // 18. ADMIN PANEL LOGIC
  // =========================================================================
  openAdminModal() {
    if (!this.user || this.user.role !== 'admin') {
      this.showToast('Accesso riservato agli amministratori', 'warning');
      return;
    }
    this.setAdminTab('users');
    const modal = document.getElementById('adminModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  closeAdminModal() {
    const modal = document.getElementById('adminModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  setAdminTab(tab) {
    const tabs = ['users', 'tokens', 'tares'];
    tabs.forEach(t => {
      const btn = document.getElementById(`adminTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
      const content = document.getElementById(`adminTab${t.charAt(0).toUpperCase() + t.slice(1)}Content`);
      if (btn && content) {
        if (t === tab) {
          btn.className = 'pb-2 border-b-2 border-indigo-500 text-indigo-400 font-bold';
          content.classList.remove('hidden');
        } else {
          btn.className = 'pb-2 border-b-2 border-transparent text-slate-400 font-semibold';
          content.classList.add('hidden');
        }
      }
    });

    if (tab === 'users') this.loadAdminUsers();
    else if (tab === 'tokens') this.loadAdminTokens();
    else if (tab === 'tares') this.loadAdminTares();
  }

  async loadAdminUsers() {
    try {
      const res = await fetch('/api/admin/users');
      if (res.ok) {
        const users = await res.json();
        const tbody = document.getElementById('adminUsersTableBody');
        if (!tbody) return;
        tbody.innerHTML = users.map(u => `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="p-2.5 font-bold text-slate-200">${this.escapeHtml(u.username)}</td>
            <td class="p-2.5">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${u.role === 'admin' ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' : 'bg-slate-800 text-slate-300'}">
                ${u.role}
              </span>
            </td>
            <td class="p-2.5 text-right">
              ${u.username !== this.user.username ? `
                <button onclick="app.deleteUser(${u.id})" class="text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950/40">Elimina</button>
              ` : '<span class="text-slate-500 text-[10px]">Tu</span>'}
            </td>
          </tr>
        `).join('');
      }
    } catch (e) {
      console.warn(e);
    }
  }

  async handleCreateUser(e) {
    e.preventDefault();
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newUserPassword').value;

    try {
      const res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role: 'editor' })
      });
      if (res.ok) {
        document.getElementById('newUsername').value = '';
        document.getElementById('newUserPassword').value = '';
        this.loadAdminUsers();
        this.showToast(`Utente ${username} creato!`, 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Errore creazione utente'), 'error');
      }
    } catch (err) {
      this.showToast(this.formatError(err, 'Errore di comunicazione'), 'error');
    }
  }

  async deleteUser(id) {
    if (!confirm('Sei sicuro di voler eliminare questo utente?')) return;
    try {
      const res = await fetch(`/api/admin/users/${id}`, { method: 'DELETE' });
      if (res.ok) {
        this.loadAdminUsers();
        this.showToast('Utente eliminato', 'info');
      }
    } catch (e) {
      this.showToast('Errore', 'error');
    }
  }

  async loadAdminTokens() {
    try {
      const res = await fetch('/api/admin/tokens');
      if (res.ok) {
        const tokens = await res.json();
        const tbody = document.getElementById('adminTokensTableBody');
        if (!tbody) return;
        tbody.innerHTML = tokens.map(t => `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="p-2.5 font-bold text-slate-200">${this.escapeHtml(t.name)}</td>
            <td class="p-2.5 font-mono text-emerald-400">${t.token_prefix}••••••••</td>
            <td class="p-2.5 text-right">
              <button onclick="app.revokeToken(${t.id})" class="text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950/40">Revoca</button>
            </td>
          </tr>
        `).join('');
      }
    } catch (e) {
      console.warn(e);
    }
  }

  async handleCreateToken(e) {
    e.preventDefault();
    const name = document.getElementById('newTokenName').value.trim();
    try {
      const res = await fetch('/api/admin/tokens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (res.ok) {
        const data = await res.json();
        document.getElementById('newTokenName').value = '';

        const alertBox = document.getElementById('newSecretAlert');
        const secretVal = document.getElementById('newSecretValue');

        if (secretVal) secretVal.value = data.raw_token;
        if (alertBox) alertBox.classList.remove('hidden');
        this.loadAdminTokens();
        this.showToast('Nuovo token API generato!', 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Errore generazione token'), 'error');
      }
    } catch (err) {
      this.showToast(this.formatError(err, 'Errore di comunicazione'), 'error');
    }
  }

  async revokeToken(id) {
    if (!confirm('Sei sicuro di voler revocare questo token? Client esterni smetteranno di funzionare.')) return;
    try {
      const res = await fetch(`/api/admin/tokens/${id}`, { method: 'DELETE' });
      if (res.ok) {
        this.loadAdminTokens();
        this.showToast('Token revocato', 'info');
      }
    } catch (e) {
      this.showToast('Errore', 'error');
    }
  }

  async loadAdminTares() {
    try {
      const res = await fetch('/api/admin/tares');
      if (res.ok) {
        this.tares = await res.json();
        const tbody = document.getElementById('adminTaresTableBody');
        if (!tbody) return;
        tbody.innerHTML = this.tares.map(t => `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="p-2.5 font-bold text-slate-200">${this.escapeHtml(t.brand_name)}</td>
            <td class="p-2.5 font-bold text-emerald-400">${Math.round(t.tare_weight_g)} g</td>
            <td class="p-2.5 text-right">
              <button onclick="app.deleteTare(${t.id})" class="text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950/40">Elimina</button>
            </td>
          </tr>
        `).join('');
      }
    } catch (e) {
      console.warn(e);
    }
  }

  async handleCreateTare(e) {
    e.preventDefault();
    const brand_name = document.getElementById('newTareBrand').value.trim();
    const tare_weight_g = parseFloat(document.getElementById('newTareWeight').value);

    try {
      const res = await fetch('/api/admin/tares', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_name, spool_material: 'Standard', tare_weight_g })
      });
      if (res.ok) {
        document.getElementById('newTareBrand').value = '';
        document.getElementById('newTareWeight').value = '';
        this.loadAdminTares();
        this.showToast(`Tara salvata per ${brand_name}`, 'success');
      }
    } catch (e) {
      this.showToast('Errore', 'error');
    }
  }

  async deleteTare(id) {
    if (!confirm('Eliminare questa voce di tara?')) return;
    try {
      const res = await fetch(`/api/admin/tares/${id}`, { method: 'DELETE' });
      if (res.ok) {
        this.loadAdminTares();
        this.showToast('Tara eliminata', 'info');
      }
    } catch (e) {
      this.showToast('Errore', 'error');
    }
  }

  // =========================================================================
  // 19. CHANGE PASSWORD
  // =========================================================================
  openChangePasswordModal() {
    document.getElementById('changePassCurrent').value = '';
    document.getElementById('changePassNew').value = '';
    document.getElementById('changePassConfirm').value = '';
    const modal = document.getElementById('changePasswordModal');
    if (modal) modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }

  closeChangePasswordModal() {
    const modal = document.getElementById('changePasswordModal');
    if (modal) modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  async handleChangePassword(e) {
    e.preventDefault();
    const current_password = document.getElementById('changePassCurrent').value;
    const new_password = document.getElementById('changePassNew').value;
    const confirm = document.getElementById('changePassConfirm').value;

    if (new_password !== confirm) {
      this.showToast('Le due nuove password non coincidono', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password, new_password })
      });

      if (res.ok) {
        this.closeChangePasswordModal();
        this.showToast('Password aggiornata con successo!', 'success');
      } else {
        const err = await res.json().catch(() => ({}));
        this.showToast(this.formatError(err, 'Errore durante il cambio password'), 'error');
      }
    } catch (e) {
      this.showToast(this.formatError(e, 'Errore di comunicazione'), 'error');
    }
  }

  // =========================================================================
  // 20. TOAST NOTIFICATIONS & UTILS
  // =========================================================================
  formatError(err, fallback = 'Errore imprevisto') {
    if (!err) return fallback;
    if (typeof err === 'string') return err;
    if (Array.isArray(err)) {
      return err.map(e => (typeof e === 'object' && e ? (e.msg || e.message || JSON.stringify(e)) : String(e))).join(', ');
    }
    if (err.detail) {
      if (typeof err.detail === 'string') return err.detail;
      if (Array.isArray(err.detail)) {
        return err.detail.map(e => (typeof e === 'object' && e ? (e.msg || e.message || JSON.stringify(e)) : String(e))).join(', ');
      }
      if (typeof err.detail === 'object') {
        try {
          return Object.entries(err.detail).map(([k, v]) => `${k}: ${v}`).join(', ') || JSON.stringify(err.detail);
        } catch {
          return JSON.stringify(err.detail);
        }
      }
      return String(err.detail);
    }
    if (err.message) return String(err.message);
    try {
      return JSON.stringify(err);
    } catch {
      return fallback;
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    if (typeof message !== 'string') {
      message = this.formatError(message);
    }

    const toast = document.createElement('div');
    const colors = {
      success: 'bg-emerald-950/95 border-emerald-800 text-emerald-200',
      error: 'bg-red-950/95 border-red-800 text-red-200',
      warning: 'bg-amber-950/95 border-amber-800 text-amber-200',
      info: 'bg-slate-900/95 border-slate-700 text-slate-200'
    };

    const icons = {
      success: 'check-circle-2',
      error: 'alert-triangle',
      warning: 'alert-circle',
      info: 'info'
    };

    toast.className = `p-3 rounded-xl border shadow-2xl backdrop-blur-md flex items-center gap-2.5 text-xs font-semibold pointer-events-auto transition transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `
      <i data-lucide="${icons[type] || 'info'}" class="w-4 h-4 shrink-0"></i>
      <span>${this.escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
      toast.classList.add('opacity-0', '-translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Global Application Instance
window.app = new FilamentHubApp();
