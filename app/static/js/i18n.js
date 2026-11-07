/**
 * FilamentHub 3D - Internationalization (i18n) Engine
 * Supported Languages:
 *   - it: Italiano (Default)
 *   - en: English
 *   - fr: Français
 *   - es: Español
 */

(function (window) {
  'use strict';

  const translations = {
    // =========================================================================
    // ITALIANO (IT) - Default
    // =========================================================================
    it: {
      lang_name: 'Italiano',
      lang_flag: '🇮🇹',

      // Navigation & Topbar
      'nav.spools': 'Bobine',
      'nav.shopping': 'Acquisti',
      'nav.sort': 'Ordina',
      'nav.menu': 'Menu',
      'topbar.subtitle_spools': 'Spool Database • v1.7',
      'topbar.subtitle_shopping': 'Lista Acquisti Filamenti • v1.7',
      'topbar.ai_photo': 'Foto AI',
      'topbar.new_spool': 'Nuova',
      'topbar.add_shopping': 'Aggiungi',
      'topbar.search_placeholder': 'Cerca marca, materiale, colore...',
      'topbar.search_shopping_placeholder': 'Cerca per brand, materiale, colore...',
      'topbar.filters': 'Filtri',
      'topbar.tab_all': 'Tutte',
      'topbar.tab_opened': '🟢 Aperte',
      'topbar.tab_new': '📦 Nuove',
      'topbar.shopping_tab_pending': 'Da Comprare',
      'topbar.shopping_tab_bought': 'Ordinati',
      'topbar.shopping_tab_all': 'Tutti',
      'topbar.budget_tot': 'Tot:',
      'topbar.active_filters': 'Filtri attivi:',
      'topbar.reset_filters': 'Reimposta',

      // Spool List & Cards
      'spool.in_use': 'IN USO',
      'spool.opened': 'APERTA',
      'spool.new': 'NUOVA',
      'spool.empty': 'ESAURITA',
      'spool.net': 'Netto',
      'spool.gross': 'Lordo',
      'spool.tare': 'Tara',
      'spool.weigh': 'Pesa',
      'spool.open': 'Apri',
      'spool.duplicate': 'Duplica',
      'spool.delete': 'Elimina',
      'spool.edit': 'Modifica',
      'spool.print_label': 'Stampa Etichetta',
      'spool.no_spools_title': 'Nessuna bobina trovata',
      'spool.no_spools_desc': 'Modifica i filtri o aggiungi una nuova bobina.',
      'spool.add_spool_btn': 'Aggiungi Bobina',

      // Shopping List & Wishlist
      'shopping.to_buy': 'DA COMPRARE',
      'shopping.ordered': 'ORDINATO',
      'shopping.received_btn': 'Ricevuto',
      'shopping.received_title': 'Bobina Ricevuta: aggiungi all\'inventario',
      'shopping.store': 'Store',
      'shopping.open_store': 'Apri Negozio',
      'shopping.tot_price': 'Tot:',
      'shopping.empty_title': 'Nessun filamento nella lista acquisti',
      'shopping.empty_desc': 'Aggiungi i filamenti che prevedi di ordinare per monitorare colori, quantità, prezzi e link store.',
      'shopping.add_btn': 'Aggiungi Filamento',
      'shopping.modal_add_title': 'Nuovo Filamento da Acquistare',
      'shopping.modal_edit_title': 'Modifica Filamento da Acquistare',
      'shopping.brand_label': 'Brand / Produttore *',
      'shopping.material_label': 'Materiale *',
      'shopping.subtype_label': 'Finitura / Sottotipo',
      'shopping.color_name_label': 'Nome Colore *',
      'shopping.color_hex_label': 'Colore (HEX)',
      'shopping.quantity_label': 'Quantità',
      'shopping.weight_label': 'Peso (g)',
      'shopping.price_label': 'Prezzo (€)',
      'shopping.store_url_label': 'Link Negozio / Offerta (opzionale)',
      'shopping.notes_label': 'Note (opzionale)',
      'shopping.cancel': 'Annulla',
      'shopping.save': 'Salva nella Lista',
      'shopping.convert_confirm': 'Confermi di aver ricevuto la bobina "{name}"?\n\nVerrà generato un nuovo codice univoco SP-xxxx e la bobina verrà inserita nel tuo inventario attivo.\n\nClicca OK per convertire e rimuovere dalla lista acquisti, oppure Annulla per non procedere.',

      // AI Vision Progress HUD
      'hud.title': 'Analisi Neurale Etichetta',
      'hud.elapsed': 'Tempo trascorso:',
      'hud.disclaimer': 'L\'IA sta estraendo brand, materiale, finitura, colore esatto e barcode. L\'elaborazione neurale richiede tipicamente da 3 a 8 secondi.',
      'hud.cancel_btn': 'Annulla operazione',
      'hud.step_connect': 'Invio foto ad alta risoluzione a Google Gemini Vision...',
      'hud.step_brand': 'Riconoscimento neurale di brand e tipo materiale...',
      'hud.step_color': 'Campionamento cromatico ed estrazione finitura...',
      'hud.step_barcode': 'Decodifica barcode/QR ed estrazione parametri slicer...',
      'hud.step_finalize': 'Finalizzazione scheda tecnica e validazione pesi...',
      'hud.step_long': 'Elaborazione neurale avanzata in corso, quasi pronto...',

      // Settings Modal
      'settings.title': 'Vision AI e preferenze',
      'settings.subtitle': 'Chiave API personale e preferenze',
      'settings.lang_hint': 'Lingua per il tuo profilo',
      'menu.language_title': 'Lingua Interfaccia',
      'menu.language_subtitle': 'Seleziona la lingua preferita',
      'settings.gemini_title': 'Google Gemini Vision API (Personale)',
      'settings.gemini_desc': 'Abilita l\'estrazione automatica di brand, materiale, colore e barcode dalle foto delle etichette per il tuo account.',
      'settings.configured': 'Configurata',
      'settings.not_configured': 'Non configurata',
      'settings.api_key_label': 'Chiave API Google Gemini',
      'settings.api_key_placeholder': 'Incolla chiave API...',
      'settings.guide_title': 'Come ottenere la chiave gratuita:',
      'settings.guide_step1': 'Accedi a Google AI Studio con il tuo account Google.',
      'settings.guide_step2': 'Clicca su "Create API key".',
      'settings.guide_step3': 'Copia la chiave generata e incollala qui sopra.',
      'settings.guide_footer': 'Il piano gratuito offre fino a 15 richieste al minuto, ampiamente sufficiente per la scansione delle bobine.',
      'settings.model_label': 'Modello Gemini',
      'settings.lang_label': 'Lingua Interfaccia',
      'settings.remove_key': 'Rimuovi chiave',
      'settings.cancel': 'Annulla',
      'settings.save': 'Salva Impostazioni',
      'settings.saving': 'Salvataggio...',

      // Login Modal
      'login.title': 'FilamentHub 3D',
      'login.subtitle': 'Accedi al tuo archivio personale di filamenti',
      'login.username_label': 'Nome Utente',
      'login.username_placeholder': 'Inserisci username...',
      'login.password_label': 'Password',
      'login.password_placeholder': '••••••••',
      'login.submit_btn': 'Accedi all\'inventario',
      'login.submitting': 'Accesso in corso...',
      'login.private_note': 'Sistema privato multi-utente. Gli account vengono creati dall\'amministratore.',
      'login.select_lang': 'Lingua:',

      // Mobile Menu Sheet
      'menu.title': 'Menu Principale',
      'menu.close': 'Chiudi',
      'menu.personal_profile': 'Profilo Personale',
      'menu.admin_panel': 'Pannello Amministrazione',
      'menu.laser_a4': 'Foglio Stampa A4 Laser',
      'menu.tare_db': 'Database Tare Produttori',
      'menu.settings': 'Impostazioni & Vision AI',
      'menu.shopping_list': 'Lista Acquisti Filamenti',
      'menu.logout': 'Disconnetti',
      'menu.app_version': 'Versione FilamentHub:',

      // Toasts & Messages
      'toast.login_success': 'Accesso effettuato con successo!',
      'toast.logout_success': 'Sessione terminata.',
      'toast.spool_created': 'Bobina aggiunta con successo all\'inventario!',
      'toast.spool_updated': 'Bobina aggiornata con successo!',
      'toast.spool_deleted': 'Bobina rimossa dall\'inventario.',
      'toast.spool_duplicated': 'Bobina duplicata con nuovo codice SP!',
      'toast.weighed_success': 'Nuovo peso registrato con successo!',
      'toast.shopping_saved': 'Filamento salvato nella lista acquisti!',
      'toast.shopping_deleted': 'Filamento rimosso dalla lista acquisti.',
      'toast.settings_saved': 'Impostazioni salvate con successo!',
      'toast.lang_changed': 'Lingua aggiornata in {lang}!',
      'toast.ai_cancelled': 'Analisi Vision AI annullata.',
      'toast.ai_success': 'Dati etichetta estratti con successo da Gemini Flash!',
      'toast.ai_not_configured': 'API Gemini non configurata! Inserisci la tua chiave nelle Impostazioni.',
      'toast.network_error': 'Errore di connessione al server.'
    },

    // =========================================================================
    // ENGLISH (EN)
    // =========================================================================
    en: {
      lang_name: 'English',
      lang_flag: '🇬🇧',

      // Navigation & Topbar
      'nav.spools': 'Spools',
      'nav.shopping': 'Shopping',
      'nav.sort': 'Sort',
      'nav.menu': 'Menu',
      'topbar.subtitle_spools': 'Spool Database • v1.7',
      'topbar.subtitle_shopping': 'Filament Shopping List • v1.7',
      'topbar.ai_photo': 'AI Photo',
      'topbar.new_spool': 'New',
      'topbar.add_shopping': 'Add Item',
      'topbar.search_placeholder': 'Search brand, material, color...',
      'topbar.search_shopping_placeholder': 'Search brand, material, color...',
      'topbar.filters': 'Filters',
      'topbar.tab_all': 'All',
      'topbar.tab_opened': '🟢 Opened',
      'topbar.tab_new': '📦 New',
      'topbar.shopping_tab_pending': 'To Buy',
      'topbar.shopping_tab_bought': 'Ordered',
      'topbar.shopping_tab_all': 'All',
      'topbar.budget_tot': 'Total:',
      'topbar.active_filters': 'Active filters:',
      'topbar.reset_filters': 'Reset',

      // Spool List & Cards
      'spool.in_use': 'IN USE',
      'spool.opened': 'OPENED',
      'spool.new': 'NEW',
      'spool.empty': 'EMPTY',
      'spool.net': 'Net',
      'spool.gross': 'Gross',
      'spool.tare': 'Tare',
      'spool.weigh': 'Weigh',
      'spool.open': 'Open',
      'spool.duplicate': 'Duplicate',
      'spool.delete': 'Delete',
      'spool.edit': 'Edit',
      'spool.print_label': 'Print Label',
      'spool.no_spools_title': 'No spools found',
      'spool.no_spools_desc': 'Modify your filters or add a new spool.',
      'spool.add_spool_btn': 'Add Spool',

      // Shopping List & Wishlist
      'shopping.to_buy': 'TO BUY',
      'shopping.ordered': 'ORDERED',
      'shopping.received_btn': 'Received',
      'shopping.received_title': 'Spool received: add to active inventory',
      'shopping.store': 'Store',
      'shopping.open_store': 'Open Store',
      'shopping.tot_price': 'Total:',
      'shopping.empty_title': 'No filaments in shopping list',
      'shopping.empty_desc': 'Add filaments you plan to buy to track colors, quantities, prices, and store links.',
      'shopping.add_btn': 'Add Filament',
      'shopping.modal_add_title': 'New Filament to Buy',
      'shopping.modal_edit_title': 'Edit Wishlist Filament',
      'shopping.brand_label': 'Brand / Manufacturer *',
      'shopping.material_label': 'Material *',
      'shopping.subtype_label': 'Finish / Subtype',
      'shopping.color_name_label': 'Color Name *',
      'shopping.color_hex_label': 'Color (HEX)',
      'shopping.quantity_label': 'Quantity',
      'shopping.weight_label': 'Weight (g)',
      'shopping.price_label': 'Price (€)',
      'shopping.store_url_label': 'Store / Offer Link (optional)',
      'shopping.notes_label': 'Notes (optional)',
      'shopping.cancel': 'Cancel',
      'shopping.save': 'Save to List',
      'shopping.convert_confirm': 'Confirm that you received spool "{name}"?\n\nA unique SP-xxxx code will be generated and added to your active inventory.\n\nClick OK to convert and remove from wishlist, or Cancel to abort.',

      // AI Vision Progress HUD
      'hud.title': 'Neural Label Analysis',
      'hud.elapsed': 'Elapsed time:',
      'hud.disclaimer': 'AI is extracting brand, material, finish, exact color and barcode. Neural analysis typically takes 3 to 8 seconds.',
      'hud.cancel_btn': 'Cancel operation',
      'hud.step_connect': 'Sending high-resolution photo to Google Gemini Vision...',
      'hud.step_brand': 'Neural recognition of brand and material type...',
      'hud.step_color': 'Color sampling and finish detection...',
      'hud.step_barcode': 'Decoding barcode/QR and slicer parameters...',
      'hud.step_finalize': 'Finalizing technical specs and validating weights...',
      'hud.step_long': 'Advanced neural processing in progress, almost ready...',

      // Settings Modal
      'settings.title': 'Vision AI & Preferences',
      'settings.subtitle': 'Personal API key and preferences',
      'settings.lang_hint': 'Language for your profile',
      'menu.language_title': 'Interface Language',
      'menu.language_subtitle': 'Select your preferred language',
      'settings.gemini_title': 'Google Gemini Vision API (Personal)',
      'settings.gemini_desc': 'Enables automatic extraction of brand, material, color, and barcode from spool label photos for your account.',
      'settings.configured': 'Configured',
      'settings.not_configured': 'Not configured',
      'settings.api_key_label': 'Google Gemini API Key',
      'settings.api_key_placeholder': 'Paste API key...',
      'settings.guide_title': 'How to get a free API key:',
      'settings.guide_step1': 'Sign in to Google AI Studio with your Google account.',
      'settings.guide_step2': 'Click on "Create API key".',
      'settings.guide_step3': 'Copy the generated key and paste it above.',
      'settings.guide_footer': 'The free tier offers up to 15 requests per minute, plenty for spool scanning.',
      'settings.model_label': 'Gemini Model',
      'settings.lang_label': 'Interface Language',
      'settings.remove_key': 'Remove key',
      'settings.cancel': 'Cancel',
      'settings.save': 'Save Settings',
      'settings.saving': 'Saving...',

      // Login Modal
      'login.title': 'FilamentHub 3D',
      'login.subtitle': 'Sign in to your private filament archive',
      'login.username_label': 'Username',
      'login.username_placeholder': 'Enter username...',
      'login.password_label': 'Password',
      'login.password_placeholder': '••••••••',
      'login.submit_btn': 'Sign In to Inventory',
      'login.submitting': 'Signing in...',
      'login.private_note': 'Private multi-user system. Accounts are created by administrators.',
      'login.select_lang': 'Language:',

      // Mobile Menu Sheet
      'menu.title': 'Main Menu',
      'menu.close': 'Close',
      'menu.personal_profile': 'Personal Profile',
      'menu.admin_panel': 'Administration Panel',
      'menu.laser_a4': 'A4 Laser Sheet Generator',
      'menu.tare_db': 'Brand Tare Weights DB',
      'menu.settings': 'Settings & Vision AI',
      'menu.shopping_list': 'Filament Shopping List',
      'menu.logout': 'Sign Out',
      'menu.app_version': 'FilamentHub Version:',

      // Toasts & Messages
      'toast.login_success': 'Signed in successfully!',
      'toast.logout_success': 'Session terminated.',
      'toast.spool_created': 'Spool successfully added to inventory!',
      'toast.spool_updated': 'Spool updated successfully!',
      'toast.spool_deleted': 'Spool removed from inventory.',
      'toast.spool_duplicated': 'Spool duplicated with new SP code!',
      'toast.weighed_success': 'New weight recorded successfully!',
      'toast.shopping_saved': 'Filament saved to shopping list!',
      'toast.shopping_deleted': 'Filament removed from shopping list.',
      'toast.settings_saved': 'Settings saved successfully!',
      'toast.lang_changed': 'Language switched to {lang}!',
      'toast.ai_cancelled': 'Vision AI analysis cancelled.',
      'toast.ai_success': 'Label data successfully extracted by Gemini Flash!',
      'toast.ai_not_configured': 'Gemini API not configured! Please enter your key in Settings.',
      'toast.network_error': 'Network connection error.'
    },

    // =========================================================================
    // FRANÇAIS (FR)
    // =========================================================================
    fr: {
      lang_name: 'Français',
      lang_flag: '🇫🇷',

      // Navigation & Topbar
      'nav.spools': 'Bobines',
      'nav.shopping': 'Achats',
      'nav.sort': 'Trier',
      'nav.menu': 'Menu',
      'topbar.subtitle_spools': 'Base Bobines • v1.7',
      'topbar.subtitle_shopping': 'Liste d\'Achats Filaments • v1.7',
      'topbar.ai_photo': 'Photo IA',
      'topbar.new_spool': 'Nouvelle',
      'topbar.add_shopping': 'Ajouter',
      'topbar.search_placeholder': 'Rechercher marque, matière, couleur...',
      'topbar.search_shopping_placeholder': 'Rechercher marque, matière, couleur...',
      'topbar.filters': 'Filtres',
      'topbar.tab_all': 'Toutes',
      'topbar.tab_opened': '🟢 Ouvertes',
      'topbar.tab_new': '📦 Neuves',
      'topbar.shopping_tab_pending': 'À Acheter',
      'topbar.shopping_tab_bought': 'Commandés',
      'topbar.shopping_tab_all': 'Tous',
      'topbar.budget_tot': 'Total :',
      'topbar.active_filters': 'Filtres actifs :',
      'topbar.reset_filters': 'Réinitialiser',

      // Spool List & Cards
      'spool.in_use': 'EN COURS',
      'spool.opened': 'OUVERTE',
      'spool.new': 'NEUVE',
      'spool.empty': 'ÉPUISÉE',
      'spool.net': 'Net',
      'spool.gross': 'Brut',
      'spool.tare': 'Tare',
      'spool.weigh': 'Peser',
      'spool.open': 'Ouvrir',
      'spool.duplicate': 'Dupliquer',
      'spool.delete': 'Supprimer',
      'spool.edit': 'Modifier',
      'spool.print_label': 'Imprimer Étiquette',
      'spool.no_spools_title': 'Aucune bobine trouvée',
      'spool.no_spools_desc': 'Modifiez vos filtres ou ajoutez une nouvelle bobine.',
      'spool.add_spool_btn': 'Ajouter Bobine',

      // Shopping List & Wishlist
      'shopping.to_buy': 'À ACHETER',
      'shopping.ordered': 'COMMANDÉ',
      'shopping.received_btn': 'Reçu',
      'shopping.received_title': 'Bobine reçue : ajouter à l\'inventaire actif',
      'shopping.store': 'Boutique',
      'shopping.open_store': 'Ouvrir Boutique',
      'shopping.tot_price': 'Total :',
      'shopping.empty_title': 'Aucun filament dans la liste d\'achats',
      'shopping.empty_desc': 'Ajoutez les filaments que vous prévoyez de commander pour suivre couleurs, quantités, prix et boutiques.',
      'shopping.add_btn': 'Ajouter Filament',
      'shopping.modal_add_title': 'Nouveau Filament à Acheter',
      'shopping.modal_edit_title': 'Modifier le Filament',
      'shopping.brand_label': 'Marque / Fabricant *',
      'shopping.material_label': 'Matériau *',
      'shopping.subtype_label': 'Finition / Sous-type',
      'shopping.color_name_label': 'Nom Couleur *',
      'shopping.color_hex_label': 'Couleur (HEX)',
      'shopping.quantity_label': 'Quantité',
      'shopping.weight_label': 'Poids (g)',
      'shopping.price_label': 'Prix (€)',
      'shopping.store_url_label': 'Lien Boutique / Offre (facultatif)',
      'shopping.notes_label': 'Remarques (facultatif)',
      'shopping.cancel': 'Annuler',
      'shopping.save': 'Enregistrer',
      'shopping.convert_confirm': 'Confirmez-vous la réception de la bobine "{name}" ?\n\nUn code unique SP-xxxx sera généré et ajouté à votre inventaire.\n\nCliquez sur OK pour convertir et retirer de la liste, ou Annuler pour abandonner.',

      // AI Vision Progress HUD
      'hud.title': 'Analyse Neuronale d\'Étiquette',
      'hud.elapsed': 'Temps écoulé :',
      'hud.disclaimer': 'L\'IA extrait marque, matière, finition, couleur exacte et code-barres. Le traitement prend généralement 3 à 8 secondes.',
      'hud.cancel_btn': 'Annuler l\'opération',
      'hud.step_connect': 'Envoi de la photo haute résolution à Google Gemini Vision...',
      'hud.step_brand': 'Reconnaissance neuronale de la marque et du matériau...',
      'hud.step_color': 'Échantillonnage chromatique et détection de finition...',
      'hud.step_barcode': 'Décodage code-barres/QR et paramètres slicer...',
      'hud.step_finalize': 'Finalisation de la fiche technique et validation...',
      'hud.step_long': 'Traitement neuronal avancé en cours, presque prêt...',

      // Settings Modal
      'settings.title': 'Vision IA et préférences',
      'settings.subtitle': 'Clé API personnelle et préférences',
      'settings.lang_hint': 'Langue pour votre profil',
      'menu.language_title': 'Langue de l\'interface',
      'menu.language_subtitle': 'Sélectionnez votre langue préférée',
      'settings.gemini_title': 'Google Gemini Vision API (Personnel)',
      'settings.gemini_desc': 'Active l\'extraction automatique de marque, matière, couleur et code-barres à partir des photos d\'étiquettes pour votre compte.',
      'settings.configured': 'Configurée',
      'settings.not_configured': 'Non configurée',
      'settings.api_key_label': 'Clé API Google Gemini',
      'settings.api_key_placeholder': 'Coller la clé API...',
      'settings.guide_title': 'Comment obtenir la clé gratuite :',
      'settings.guide_step1': 'Connectez-vous à Google AI Studio avec votre compte Google.',
      'settings.guide_step2': 'Cliquez sur "Create API key".',
      'settings.guide_step3': 'Copiez la clé générée et collez-la ci-dessus.',
      'settings.guide_footer': 'Le forfait gratuit offre jusqu\'à 15 requêtes/min, amplement suffisant pour scanner les bobines.',
      'settings.model_label': 'Modèle Gemini',
      'settings.lang_label': 'Langue de l\'interface',
      'settings.remove_key': 'Supprimer la clé',
      'settings.cancel': 'Annuler',
      'settings.save': 'Enregistrer',
      'settings.saving': 'Enregistrement...',

      // Login Modal
      'login.title': 'FilamentHub 3D',
      'login.subtitle': 'Connectez-vous à votre inventaire privé',
      'login.username_label': 'Nom d\'utilisateur',
      'login.username_placeholder': 'Entrez le nom d\'utilisateur...',
      'login.password_label': 'Mot de passe',
      'login.password_placeholder': '••••••••',
      'login.submit_btn': 'Se connecter à l\'inventaire',
      'login.submitting': 'Connexion...',
      'login.private_note': 'Système privé multi-utilisateur. Les comptes sont créés par les administrateurs.',
      'login.select_lang': 'Langue :',

      // Mobile Menu Sheet
      'menu.title': 'Menu Principal',
      'menu.close': 'Fermer',
      'menu.personal_profile': 'Profil Personnel',
      'menu.admin_panel': 'Panneau d\'Administration',
      'menu.laser_a4': 'Planche Laser A4',
      'menu.tare_db': 'Base de Tares Fabricants',
      'menu.settings': 'Paramètres & Vision IA',
      'menu.shopping_list': 'Liste d\'Achats Filaments',
      'menu.logout': 'Déconnexion',
      'menu.app_version': 'Version FilamentHub :',

      // Toasts & Messages
      'toast.login_success': 'Connexion réussie !',
      'toast.logout_success': 'Session terminée.',
      'toast.spool_created': 'Bobine ajoutée à l\'inventaire avec succès !',
      'toast.spool_updated': 'Bobine mise à jour avec succès !',
      'toast.spool_deleted': 'Bobine supprimée de l\'inventaire.',
      'toast.spool_duplicated': 'Bobine dupliquée avec nouveau code SP !',
      'toast.weighed_success': 'Nouveau poids enregistré avec succès !',
      'toast.shopping_saved': 'Filament enregistré dans la liste d\'achats !',
      'toast.shopping_deleted': 'Filament supprimé de la liste d\'achats.',
      'toast.settings_saved': 'Paramètres enregistrés avec succès !',
      'toast.lang_changed': 'Langue changée en {lang} !',
      'toast.ai_cancelled': 'Analyse Vision IA annulée.',
      'toast.ai_success': 'Données extraites avec succès par Gemini Flash !',
      'toast.ai_not_configured': 'API Gemini non configurée ! Veuillez entrer votre clé dans Paramètres.',
      'toast.network_error': 'Erreur de connexion au serveur.'
    },

    // =========================================================================
    // ESPAÑOL (ES)
    // =========================================================================
    es: {
      lang_name: 'Español',
      lang_flag: '🇪🇸',

      // Navigation & Topbar
      'nav.spools': 'Bobinas',
      'nav.shopping': 'Compras',
      'nav.sort': 'Ordenar',
      'nav.menu': 'Menú',
      'topbar.subtitle_spools': 'Base de Bobinas • v1.7',
      'topbar.subtitle_shopping': 'Lista de Compras de Filamentos • v1.7',
      'topbar.ai_photo': 'Foto IA',
      'topbar.new_spool': 'Nueva',
      'topbar.add_shopping': 'Añadir',
      'topbar.search_placeholder': 'Buscar marca, material, color...',
      'topbar.search_shopping_placeholder': 'Buscar marca, material, color...',
      'topbar.filters': 'Filtros',
      'topbar.tab_all': 'Todas',
      'topbar.tab_opened': '🟢 Abiertas',
      'topbar.tab_new': '📦 Nuevas',
      'topbar.shopping_tab_pending': 'Por Comprar',
      'topbar.shopping_tab_bought': 'Pedidos',
      'topbar.shopping_tab_all': 'Todos',
      'topbar.budget_tot': 'Total:',
      'topbar.active_filters': 'Filtros activos:',
      'topbar.reset_filters': 'Restablecer',

      // Spool List & Cards
      'spool.in_use': 'EN USO',
      'spool.opened': 'ABIERTA',
      'spool.new': 'NUEVA',
      'spool.empty': 'AGOTADA',
      'spool.net': 'Neto',
      'spool.gross': 'Bruto',
      'spool.tare': 'Tara',
      'spool.weigh': 'Pesar',
      'spool.open': 'Abrir',
      'spool.duplicate': 'Duplicar',
      'spool.delete': 'Eliminar',
      'spool.edit': 'Editar',
      'spool.print_label': 'Imprimir Etiqueta',
      'spool.no_spools_title': 'No se encontraron bobinas',
      'spool.no_spools_desc': 'Modifica los filtros o añade una nueva bobina.',
      'spool.add_spool_btn': 'Añadir Bobina',

      // Shopping List & Wishlist
      'shopping.to_buy': 'POR COMPRAR',
      'shopping.ordered': 'PEDIDO',
      'shopping.received_btn': 'Recibido',
      'shopping.received_title': 'Bobina recibida: añadir al inventario activo',
      'shopping.store': 'Tienda',
      'shopping.open_store': 'Abrir Tienda',
      'shopping.tot_price': 'Total:',
      'shopping.empty_title': 'No hay filamentos en la lista de compras',
      'shopping.empty_desc': 'Añade los filamentos que planeas pedir para controlar colores, cantidades, precios y enlaces.',
      'shopping.add_btn': 'Añadir Filamento',
      'shopping.modal_add_title': 'Nuevo Filamento por Comprar',
      'shopping.modal_edit_title': 'Editar Filamento',
      'shopping.brand_label': 'Marca / Fabricante *',
      'shopping.material_label': 'Material *',
      'shopping.subtype_label': 'Acabado / Subtipo',
      'shopping.color_name_label': 'Nombre del Color *',
      'shopping.color_hex_label': 'Color (HEX)',
      'shopping.quantity_label': 'Cantidad',
      'shopping.weight_label': 'Peso (g)',
      'shopping.price_label': 'Precio (€)',
      'shopping.store_url_label': 'Enlace Tienda / Oferta (opcional)',
      'shopping.notes_label': 'Notas (opcional)',
      'shopping.cancel': 'Cancelar',
      'shopping.save': 'Guardar en Lista',
      'shopping.convert_confirm': '¿Confirmas haber recibido la bobina "{name}"?\n\nSe generará un código único SP-xxxx y se añadirá a tu inventario activo.\n\nHaz clic en OK para convertir y quitar de la lista, o Cancelar para no continuar.',

      // AI Vision Progress HUD
      'hud.title': 'Análisis Neuronal de Etiqueta',
      'hud.elapsed': 'Tiempo transcurrido:',
      'hud.disclaimer': 'La IA está extrayendo marca, material, acabado, color exacto y código de barras. El procesamiento neuronal suele tardar de 3 a 8 segundos.',
      'hud.cancel_btn': 'Cancelar operación',
      'hud.step_connect': 'Enviando foto de alta resolución a Google Gemini Vision...',
      'hud.step_brand': 'Reconocimiento neuronal de marca y tipo de material...',
      'hud.step_color': 'Muestreo cromático y detección de acabado...',
      'hud.step_barcode': 'Decodificación de código de barras/QR y parámetros slicer...',
      'hud.step_finalize': 'Finalizando ficha técnica y validando pesos...',
      'hud.step_long': 'Procesamiento neuronal avanzado en curso, casi listo...',

      // Settings Modal
      'settings.title': 'Visión IA y preferencias',
      'settings.subtitle': 'Clave API personal y preferencias',
      'settings.lang_hint': 'Idioma para tu perfil',
      'menu.language_title': 'Idioma de la interfaz',
      'menu.language_subtitle': 'Selecciona tu idioma preferido',
      'settings.gemini_title': 'Google Gemini Vision API (Personal)',
      'settings.gemini_desc': 'Habilita la extracción automática de marca, material, color y código de barras a partir de fotos de etiquetas para tu cuenta.',
      'settings.configured': 'Configurada',
      'settings.not_configured': 'No configurada',
      'settings.api_key_label': 'Clave API Google Gemini',
      'settings.api_key_placeholder': 'Pegar clave API...',
      'settings.guide_title': 'Cómo obtener la clave gratuita:',
      'settings.guide_step1': 'Accede a Google AI Studio con tu cuenta de Google.',
      'settings.guide_step2': 'Haz clic en "Create API key".',
      'settings.guide_step3': 'Copia la clave generada y pégala aquí arriba.',
      'settings.guide_footer': 'El plan gratuito ofrece hasta 15 solicitudes por minuto, suficiente para escanear bobinas.',
      'settings.model_label': 'Modelo Gemini',
      'settings.lang_label': 'Idioma de la Interfaz',
      'settings.remove_key': 'Eliminar clave',
      'settings.cancel': 'Cancelar',
      'settings.save': 'Guardar Configuración',
      'settings.saving': 'Guardando...',

      // Login Modal
      'login.title': 'FilamentHub 3D',
      'login.subtitle': 'Inicia sesión en tu inventario privado de filamentos',
      'login.username_label': 'Nombre de Usuario',
      'login.username_placeholder': 'Introduce usuario...',
      'login.password_label': 'Contraseña',
      'login.password_placeholder': '••••••••',
      'login.submit_btn': 'Iniciar Sesión en el Inventario',
      'login.submitting': 'Iniciando sesión...',
      'login.private_note': 'Sistema privado multiusuario. Las cuentas son creadas por los administradores.',
      'login.select_lang': 'Idioma:',

      // Mobile Menu Sheet
      'menu.title': 'Menú Principal',
      'menu.close': 'Cerrar',
      'menu.personal_profile': 'Perfil Personal',
      'menu.admin_panel': 'Panel de Administración',
      'menu.laser_a4': 'Lámina Láser A4',
      'menu.tare_db': 'Base de Taras de Fabricantes',
      'menu.settings': 'Configuración y Visión IA',
      'menu.shopping_list': 'Lista de Compras de Filamentos',
      'menu.logout': 'Cerrar Sesión',
      'menu.app_version': 'Versión FilamentHub:',

      // Toasts & Messages
      'toast.login_success': '¡Inicio de sesión exitoso!',
      'toast.logout_success': 'Sesión finalizada.',
      'toast.spool_created': '¡Bobina añadida al inventario con éxito!',
      'toast.spool_updated': '¡Bobina actualizada con éxito!',
      'toast.spool_deleted': 'Bobina eliminada del inventario.',
      'toast.spool_duplicated': '¡Bobina duplicada con nuevo código SP!',
      'toast.weighed_success': '¡Nuevo peso registrado con éxito!',
      'toast.shopping_saved': '¡Filamento guardado en la lista de compras!',
      'toast.shopping_deleted': 'Filamento eliminado de la lista de compras.',
      'toast.settings_saved': '¡Configuración guardada con éxito!',
      'toast.lang_changed': '¡Idioma cambiado a {lang}!',
      'toast.ai_cancelled': 'Análisis de Visión IA cancelado.',
      'toast.ai_success': '¡Datos de la etiqueta extraídos con éxito por Gemini Flash!',
      'toast.ai_not_configured': '¡API Gemini no configurada! Introduce tu clave en Configuración.',
      'toast.network_error': 'Error de conexión con el servidor.'
    }
  };

  class I18nEngine {
    constructor() {
      this.defaultLang = 'en';
      this.currentLang = 'en';
      this.supportedLanguages = ['en', 'it', 'fr', 'es'];
    }

    init() {
      // 1. Check localStorage first
      const stored = localStorage.getItem('filamenthub_lang');
      if (stored && this.supportedLanguages.includes(stored)) {
        this.currentLang = stored;
      } else {
        // Default to English as explicitly requested
        this.currentLang = 'en';
        localStorage.setItem('filamenthub_lang', 'en');
      }

      this.applyTranslations();
      this.updateActiveLanguageUi();
      return this.currentLang;
    }

    getLanguage() {
      return this.currentLang;
    }

    setLanguage(lang, syncBackend = true) {
      if (!this.supportedLanguages.includes(lang)) {
        console.warn(`Unsupported language: ${lang}`);
        return;
      }
      this.currentLang = lang;
      localStorage.setItem('filamenthub_lang', lang);
      document.documentElement.setAttribute('lang', lang);

      this.applyTranslations();
      this.updateActiveLanguageUi();

      // Dispatch global event for reactive UI updates
      window.dispatchEvent(new CustomEvent('languagechange', { detail: { lang } }));

      // Optionally sync to user profile in backend if logged in
      if (syncBackend && window.app && window.app.user) {
        window.app.syncUserLanguage(lang).catch(err => console.warn('Failed to sync lang to backend:', err));
      }
    }

    t(key, params = {}) {
      const dict = translations[this.currentLang] || translations.en;
      let val = dict[key] || translations.en[key] || translations.it[key] || key;

      // Replace interpolated variables: {varName}
      if (params && typeof params === 'object') {
        Object.keys(params).forEach(k => {
          val = val.replace(new RegExp(`\\{${k}\\}`, 'g'), params[k]);
        });
      }
      return val;
    }

    updateActiveLanguageUi() {
      const lang = this.currentLang;

      // Update Login pills, Menu pills, and Settings pills
      this.supportedLanguages.forEach(l => {
        const loginBtn = document.getElementById(`loginLangBtn_${l}`);
        const menuBtn = document.getElementById(`menuLangBtn_${l}`);
        const settingsBtn = document.getElementById(`settingsLangBtn_${l}`);
        const isActive = (l === lang);

        if (loginBtn) {
          loginBtn.className = isActive
            ? 'lang-pill flex-1 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1 bg-indigo-600 text-white shadow-md shadow-indigo-600/40 scale-[1.02] active'
            : 'lang-pill flex-1 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1 text-slate-400 hover:text-white';
        }

        if (menuBtn) {
          menuBtn.className = isActive
            ? 'lang-pill py-2 rounded-xl font-bold flex flex-col items-center justify-center gap-0.5 bg-indigo-600 text-white shadow-md shadow-indigo-600/30 scale-[1.02] border border-indigo-400/50 active'
            : 'lang-pill py-2 rounded-xl font-bold flex flex-col items-center justify-center gap-0.5 bg-slate-200/60 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700/80 transition';
        }

        if (settingsBtn) {
          settingsBtn.className = isActive
            ? 'lang-pill py-2.5 rounded-xl font-bold flex flex-col items-center justify-center gap-1 bg-indigo-600 text-white shadow-md shadow-indigo-600/30 scale-[1.02] border border-indigo-400/50 active'
            : 'lang-pill py-2.5 rounded-xl font-bold flex flex-col items-center justify-center gap-1 bg-slate-200/50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 border border-slate-300/60 dark:border-slate-700/60 hover:bg-slate-300/70 dark:hover:bg-slate-700/70 transition';
        }
      });

      // Update Settings dropdown & any select
      const settingsSelect = document.getElementById('settingsLanguage');
      if (settingsSelect) {
        settingsSelect.value = lang;
      }

      // Update Menu badge
      const badge = document.getElementById('menuCurrentLangBadge');
      if (badge) {
        badge.textContent = lang.toUpperCase();
      }
    }

    applyTranslations(root = document) {
      if (!root) return;

      // 1. Text content via data-i18n
      root.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (key) {
          el.textContent = this.t(key);
        }
      });

      // 2. HTML content via data-i18n-html
      root.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.getAttribute('data-i18n-html');
        if (key) {
          el.innerHTML = this.t(key);
        }
      });

      // 3. Placeholders via data-i18n-placeholder
      root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (key) {
          el.setAttribute('placeholder', this.t(key));
        }
      });

      // 4. Titles via data-i18n-title
      root.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (key) {
          el.setAttribute('title', this.t(key));
        }
      });

      // 5. Update HTML lang attribute
      document.documentElement.setAttribute('lang', this.currentLang);
    }
  }

  // Export globally
  window.i18n = new I18nEngine();
})(window);
