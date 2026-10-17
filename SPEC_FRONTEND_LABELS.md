## 3. File `SPEC_FRONTEND_LABELS.md` (UI/UX, Calibrazioni & Stampa Etichette)

Salva questo file come `SPEC_FRONTEND_LABELS.md`.

```markdown
# Frontend UI/UX & Label Printing Specification

## 1. Design System & Layout Responsive ("Dark Tech")
- **Palette:** Sfondo primario `#0b0f19` (Slate 950), Card `#111827` (Gray 900) con bordo sottile `#1f2937`, Testo primario `#f9fafb`, Accenti `#6366f1` (Indigo) e `#10b981` (Emerald).
- **Desktop Layout:**
  - Topbar con ricerca istantanea, filtri combinabili (Materiale, Brand, Finitura, Stato In Uso, Alert Umidità/Scorta), switch **Vista Griglia Card** / **Vista Tabella Tecnica** (con ordinamento per K-Factor, Flow, Grammi, Prezzo) e accesso al **Pannello Admin** (se ruolo `admin`).
  - **Cockpit Stampante (4 Slot + Esterno):** Barra visuale sempre visibile in alto con 5 box interattivi (`Slot 1`, `Slot 2`, `Slot 3`, `Slot 4`, `Esterno`). Mostra l'icona SVG della bobina col colore Hex reale, materiale, K-Factor e grammi residui. Cliccando su uno slot vuoto si può assegnare rapidamente una bobina dall'archivio.
- **Mobile Layout (PWA):**
  - Header compatto, Cockpit Slot scorrevole orizzontalmente (swipe), Bottom Navigation Bar fissa con pulsante centrale flottante **"Scansiona"** (Barcode / QR / Vision AI).

## 2. Componente Visivo Bobina & Azioni Rapide su Card
Ogni Card bobina deve mostrare:
1. **Anello SVG Dinamico:** Rappresentazione grafica della bobina con il colore `color_hex` (e gradiente se `color_hex_secondary` è presente) circondata da un ring circolare di progresso che indica `percent_remaining`.
2. **Badge Tecnici:** `Materiale + Subtype` (es. `PLA Matte`), `Brand`, `uid_code` (`SP-0014`), Temperature (`220°C / 60°C`), `K: 0.022`, `Flow: 0.98`, e badge di stato (`Slot 1`, `Umida`, `Sotto Scorta`, `Drybox`).
3. **3 Pulsanti Rapidi sulla Card (senza aprire il form completo):**
   - **⚖️ Pesa Ora:** Apre un mini-popover con tastierino numerico per inserire il **Peso Lordo Attuale (g)** letto sulla bilancia; mostra in tempo reale il delta rispetto alla pesata precedente (es. `-68g consumati`) e salva con un tap.
   - **🔄 Slot / Uso:** Permette di caricare/scaricare la bobina in `Slot 1-4` o `Esterno` con un tap.
   - **🏷️ Etichetta:** Apre il menu di stampa rapida (Brother Bluetooth o aggiungi a coda A4).

## 3. Modal Bobina a 2 Tab (Creazione / Modifica)
- **Area Superiore (Scanner & Foto):**
  - Pulsante **Avvia Scanner Barcode/QR** (usa `html5-qrcode` per leggere EAN/UPC o codici `SP-xxxx`).
  - Pulsante **Foto Etichetta AI + Campionatore Colore**: scatta/carica foto, la disegna su `<canvas>`, invia a `/api/scanner/vision` per l'auto-compilazione con Gemini Flash e permette all'utente di **toccare qualsiasi punto del filamento sulla foto** per campionare il colore esadecimale reale (`ctx.getImageData`).
- **Tab 1 - Dati Principali & Pesi:**
  - `Brand` (con autocompletamento e selezione automatica della Tara da `brands_tare`), `Materiale`, `Subtype`, `Nome Colore`, `Colore Hex`.
  - `Peso Netto Iniziale (g)`, `Tara Bobina Vuota (g)`, `Peso Lordo Attuale (g)`, `Prezzo (€)`, `Posizione Scaffale`, `In Drybox` (checkbox), `In Uso` + `Slot`.
- **Tab 2 - Slicer & Calibrazione:**
  - `K-Factor (Pressure Advance)`, `Flow Ratio`, `Max Volumetric Speed (mm³/s)`, `Retraction Length (mm)`, `Retraction Speed (mm/s)`.
  - `Nozzle Min/Max (°C)`, `Bed Temp (°C)`, `Chamber Temp (°C)`.
  - `Data Apertura`, `Data Ultima Essiccazione` (con bottone **"Essiccata Oggi"**), `Temp/Ore Essiccazione`, `Note libere`.

## 4. Modulo Stampa Etichette: Brother Bluetooth & Laser A4

### 4.1 Modalità Etichettatrice Termica Brother Bluetooth (`/api/labels/brother/{uid_code}`)
- Il backend (usando `Pillow` + `python-barcode` / `qrcode`) genera un'immagine **PNG monocromatica (Bianco/Nero 1-bit o alto contrasto puro, 300 DPI)** perfettamente proporzionata per nastri orizzontali Brother (**12mm, 18mm, 24mm**, selezionabile dall'utente):
  - **Parte sinistra:** Barcode lineare **Code128** (o QR Code opzionale) che codifica `SP-xxxx`.
  - **Parte destra (testo nitido Bold):**
    - Riga 1: `SP-0014 | PLA MATTE`
    - Riga 2: `Bambu Lab - Nero`
    - Riga 3: `220/60°C | K:0.020 | T:250g`
- **Flusso Smartphone Bluetooth:**
  - Nella finestra di anteprima etichetta su mobile, il pulsante **"Invia a Brother Bluetooth"** utilizza la `navigator.share({ files: [pngFile] })` (Web Share API Level 2) per passare direttamente il file PNG all'app **Brother iPrint&Label** o **P-Touch Design&Print** sul telefono, oppure scarica il PNG pronto per la stampa.

### 4.2 Modalità Stampante Laser Foglio Adesivo A4 (`/print-a4`)
- Pagina dedicata con griglia A4 configurabile (es. standard 3x8 = 24 etichette per foglio o 3x7 = 21 etichette, con margini regolabili).
- **Selettore Interattivo "Salva-Foglio":** L'utente vede la sagoma del foglio A4 e può cliccare sulla **casella di partenza** (es. inizia dalla casella n° 7 per saltare le prime 6 etichette già staccate in precedenza) oppure attivare/disattivare singole celle prima di lanciare `window.print()`.

## 5. Quick Action View per Tag NFC / Scansione Rapida (`/s/{uid_code}`)
- Aprendo l'URL `/s/SP-0014` (tramite lettura Tag NFC sulla bobina o inquadrando il QR/Barcode), si apre una vista mobile ultra-compatta con:
  1. Riepilogo visivo della bobina e grammi netti attuali.
  2. Campo numerico gigante **"Aggiorna Peso Lordo (g)"** + Salva.
  3. Bottoni rapidi **Carica in Slot 1 / 2 / 3 / 4 / Esterno** o **Smonta**.
  4. Bottone **"Segna Essiccata Oggi"**.