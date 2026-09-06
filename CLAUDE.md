# Projekt: Outlook ↔ Gmail Kontakt-Vergleichstool

> Diese Datei ist der Einstiegspunkt für eine Claude Code Session. Kontext, Entscheidungen und offene Punkte aus der Konzeptionsphase mit dem Nutzer (Chat-Interface) sind hier festgehalten, damit keine Rückfragen zu bereits getroffenen Entscheidungen nötig sind.

## Umsetzungsstand (Stand: erste Coding-Sessions, Sep 2026)

Entscheidungen, die die ursprüngliche Konzeption unten an einigen Stellen überschreiben:

- **Name:** endgültig **ContactDiffWizard** (Python-Paket `contact_diff_wizard`). Die Namensliste unten ist erledigt.
- **UI/OAuth:** Streamlit + Loopback-Flow der offiziellen Google-Libs (`InstalledAppFlow.run_local_server`). Die „offene technische Frage" zum Redirect-Callback ist damit beantwortet — kein separater FastAPI-Server nötig. Token-Cache in gitignorierten `*.token.json`-Dateien.
- **Google:** vollständig funktionsfähig (OAuth + People API, gegen echtes Konto getestet). Einmalige OAuth-App liegt beim Maintainer, Client-ID/-Secret in gitignorierter `config.toml`.
- **Microsoft/Outlook:** **kein Azure, kein Microsoft Graph, kein `msal`.** Ein privates Microsoft-Konto kann keinen Entra-Tenant anlegen (Microsoft hat das zugemacht), und der Nutzer will kein kostenpflichtiges/kreditkartengebundenes Azure-Konto. Stattdessen: **Outlook-Kontakte werden als Datei-Export eingelesen** (CSV im Outlook-Format oder vCard `.vcf`) über `sources/outlook_file.py`. Microsoft Graph bleibt eine mögliche *spätere* Ergänzung, ist aber nicht Teil des MVP.
- **Repo:** öffentlich unter https://github.com/menderle75/contact-diff-wizard (MIT).

Wo unten „Microsoft OAuth", „Azure/Entra", „`msal`" oder „beide OAuth-Flows" steht: gilt nicht mehr, siehe oben. Die Architektur-Leitplanken (anbieter-agnostisches Modell, `ContactSource`-Interface, Liste von Quellen) bleiben — die Datei-Quelle ist einfach eine weitere `ContactSource`-Implementierung.

## Namensvorschläge (erledigt — entschieden: ContactDiffWizard)

Im Konzeptions-Chat vorgeschlagen, Entscheidung inzwischen gefallen (siehe Umsetzungsstand oben):

1. **ContactSync Bridge**
2. **ContactMerge** / Kontaktabgleich
3. **Rosetta Contacts**
4. **ContactDiffWizard** ← gewählt
5. **ContactCompare Wizard**
6. **DualContact Wizard**

## Ziel

Ein lokal startbarer Client, der die Kontakte aus einem **Outlook-Konto** (Microsoft Graph API) und einem **Gmail-Konto** (Google People API) abruft, vergleicht und Unterschiede übersichtlich darstellt:

- Kontakte, die nur in Outlook existieren
- Kontakte, die nur in Gmail existieren
- Kontakte, die in beiden existieren, aber mit abweichenden Feldern (Telefonnummer, E-Mail, Adresse etc.)

Reine Vergleichs-/Anzeige-Funktion als Ziel des MVP — **kein** automatisches Schreiben/Mergen/Synchronisieren in dieser Phase.

## Zielgruppe des Tools

- Primär: der Nutzer selbst
- Sekundär: andere Personen sollen das Tool ebenfalls **lokal bei sich** starten und mit ihren eigenen Konten nutzen können — ohne selbst etwas bei Google/Microsoft einrichten zu müssen.

## Wichtige Architektur-Entscheidung: OAuth-Modell

**Ein Missverständnis wurde in der Konzeptionsphase ausgeräumt und sollte nicht erneut aufkommen:**

- Es wird **eine einmalige** OAuth-App-Registrierung geben (je eine bei Google Cloud Console und Azure/Microsoft Entra), durchgeführt vom Projekt-Maintainer (dem Nutzer, ggf. mit Claude Code Unterstützung Schritt für Schritt).
- Die resultierenden Client-IDs werden fest im Projekt hinterlegt (Client-ID ist bei OAuth "Authorization Code Flow" mit PKCE nicht geheim, kein Client-Secret im Repo nötig für Desktop-/native Apps).
- **Jeder Endnutzer** loggt sich beim Start des Clients ganz normal über den Standard-Login-Screen von Google bzw. Microsoft ein (Browser öffnet sich, normaler Consent-Screen, fertig). Kein manuelles API-Setup durch Endnutzer.
- Bekannter Nebeneffekt: Solange die Google-App nicht von Google verifiziert ist, sehen Nutzer einen "Diese App wurde nicht überprüft"-Warnhinweis mit einem zusätzlichen Klick ("Erweitert" → "Trotzdem fortfahren"). Das ist für die MVP-Phase akzeptiert, keine Google-Verifizierung notwendig/geplant.

## Benötigte OAuth-Scopes

| Anbieter | Scope | Zweck |
|---|---|---|
| Google | `https://www.googleapis.com/auth/contacts.readonly` | Lesezugriff auf alle Kontakte |
| ~~Microsoft~~ | ~~`Contacts.Read` (Microsoft Graph)~~ | **entfällt im MVP** — Outlook kommt per Datei-Export rein (siehe Umsetzungsstand oben) |

Entscheidung: **Nur Lesezugriff (readonly)** für das MVP. Schreibzugriff (`contacts` / `Contacts.ReadWrite`) erst ergänzen, falls das Tool später auch Merge/Sync-Funktionen bekommen soll — das ist explizit NICHT Teil des aktuellen Scopes.

## Tech-Stack-Entscheidung

Bewusst gegen Electron und für **Python** entschieden, mit folgender Begründung (siehe Diskussion im Chat vor dieser Session):

- Schnellere Entwicklungsgeschwindigkeit für MVP, ausgereifte offizielle Bibliotheken für beide OAuth-Flows
- "Andere Nutzer sollen es lokal starten können" wird für MVP-Phase durch Python-Skript + lokalen Webserver gelöst, NICHT durch eine gepackte Desktop-App
- Electron/Tauri als möglicher späterer Schritt, falls Verteilung an eine breitere/nicht-technische Nutzergruppe relevant wird — nicht Teil des aktuellen Scopes, nicht vorzeitig implementieren

Konkreter Stack:

| Komponente | Wahl | Begründung |
|---|---|---|
| Sprache | Python 3.11+ | siehe oben |
| Google OAuth | `google-auth-oauthlib`, `google-api-python-client` | offiziell von Google gepflegt |
| ~~Microsoft OAuth~~ | ~~`msal`~~ → **Outlook-Datei-Import** (`csv` stdlib + `vobject` für vCard) | Azure-Tenant für privates MS-Konto nicht möglich/gewollt |
| Lokales UI | Streamlit + Google-Loopback-Flow (entschieden) | Diff-Tabellen-Darstellung ist Streamlits Stärke |
| Fuzzy-Matching | `rapidfuzz` | für Namens-/Telefonnummer-Abgleich, wenn E-Mail als Schlüssel fehlt |
| Packaging (später, nicht MVP) | PyInstaller | einzelne ausführbare Datei ohne Python-Installation beim Endnutzer |

**~~Offene technische Frage~~ (gelöst):** Der OAuth-Redirect läuft über den Loopback-Server, den `google-auth-oauthlib` (`InstalledAppFlow.run_local_server(port=0)`) selbst hochfährt. Kein separater FastAPI-/`http.server`-Callback nötig. Da Outlook per Datei-Import kommt, gibt es nur noch *einen* OAuth-Flow (Google).

## Matching-Strategie für den Kontaktvergleich

1. **Primärer Schlüssel:** E-Mail-Adresse (normalisiert: lowercase, getrimmt)
2. **Sekundärer Schlüssel (Fallback):** Telefonnummer (normalisiert, z. B. via `phonenumbers`-Bibliothek für einheitliches Format)
3. **Tertiär (Fuzzy):** Namensähnlichkeit via `rapidfuzz`, nur wenn weder E-Mail noch Telefonnummer einen eindeutigen Match liefern — Schwellenwert für Fuzzy-Match muss experimentell mit echten Testdaten festgelegt werden, nicht blind einen Wert übernehmen.

Diff-Kategorien für die Darstellung:
- Nur in Outlook
- Nur in Gmail
- In beiden, identisch
- In beiden, mit abweichenden Feldern (Feld-für-Feld-Diff anzeigen)

## Sprache: README und UI

- Die **README.md** im GitHub-Repo ist von Anfang an auf **Englisch** auszulegen (Standard-Erwartung für Open-Source-Projekte, breitere Zielgruppe/Auffindbarkeit).
- Die **Anwendung selbst** (UI) soll von Anfang an eine **Sprachauswahl inkl. Deutsch** eingebaut haben — nicht als späteres Nice-to-have, sondern als Grundanforderung des MVP. Konkrete Umsetzung (z. B. einfache i18n-Lösung mit JSON/YAML-Sprachdateien pro UI-Text) in der Coding-Session festlegen.

## Mittelfristige Erweiterung: weitere Anbieter (u. a. iCloud)

Das Tool ist **nicht** dauerhaft auf Outlook/Gmail beschränkt gedacht. Mittelfristig geplant ist die Erweiterung um weitere Kontakt-Anbieter, insbesondere **iCloud** (CardDAV-basiert, kein OAuth wie Google/Microsoft — eher App-spezifisches Passwort oder Apple-eigener OAuth-artiger Flow, muss zum Zeitpunkt der Umsetzung recherchiert werden) sowie potenziell weitere CardDAV-fähige Anbieter.

Konsequenzen für das aktuelle MVP-Design, die schon jetzt berücksichtigt werden sollten, um spätere Refactorings zu vermeiden:

- Das interne Datenmodell für Kontakte sollte von Anfang an **anbieter-agnostisch** aufgebaut sein (kein Outlook- oder Gmail-spezifisches Feld-Naming im Kern-Modell, sondern eine neutrale Zwischenschicht, in die jeder Anbieter seine Felder mapped)
- Die Matching-/Diff-Logik sollte mit einer **Liste von Kontaktquellen** arbeiten (n Anbieter), nicht hart mit genau zwei Quellen (Outlook, Gmail) verdrahtet sein
- Der Auth-Layer sollte pro Anbieter austauschbar/erweiterbar sein (z. B. ein gemeinsames Interface/Protokoll für "Kontakte abrufen", unabhängig davon ob dahinter OAuth, CardDAV mit App-Passwort o. ä. steckt)
- Für das MVP selbst reicht weiterhin die Umsetzung mit genau zwei Anbietern (Outlook, Gmail) — die obigen Punkte sind Architektur-Leitplanken, keine Aufforderung, iCloud-Support bereits jetzt zu implementieren

## Explizit NICHT Teil des aktuellen Projektumfangs

- Kein automatisches Schreiben/Mergen/Synchronisieren von Kontakten
- Keine Google-App-Verifizierung
- **Kein Microsoft Graph / Azure / `msal` im MVP** — Outlook nur per Datei-Export (CSV/vCard). Graph ggf. als spätere Ergänzung.
- Kein Electron/natives Desktop-Packaging
- Keine Implementierung von iCloud oder weiteren Anbietern im MVP (nur architektonisch vorbereiten, siehe oben) — konkrete Umsetzung erst nach MVP-Abschluss

## Arbeitsmodus des Nutzers

Der Nutzer möchte **keine einzige Zeile Code selbst anfassen** und arbeitet bewusst im **reinen Dialog-Modus über Claude Desktop (Code-Tab)** — nicht über die VS Code Extension. Konsequenzen für den Umgang in einer Coding-Session:

- Schritte in verständlicher Sprache erklären und Ergebnisse/Diffs visuell zusammenfassen, nicht voraussetzen, dass der Nutzer selbst Dateien öffnet oder Code liest
- Vor Zwischenschritten (z. B. OAuth-App-Registrierung in Google Cloud Console/Azure), die zwingend eine manuelle Aktion des Nutzers außerhalb des Chats erfordern, dies klar als solche kennzeichnen — das ist die Ausnahme, nicht die Regel
- Rückfragen und Freigaben ("passt das so?") statt stillschweigender Annahmen, analog zum iterativen Vorgehen aus der Konzeptionsphase dieses Dokuments

## Nächste Schritte (aktualisiert)

1. ~~Repo-Grundgerüst~~ ✅ erledigt
2. ~~Google Cloud Console App-Registrierung~~ ✅ erledigt (Client-ID/-Secret in `config.toml`)
3. ~~Azure/Microsoft Entra App-Registrierung~~ ❌ entfällt — Outlook per Datei-Import
4. ~~OAuth-Flow isoliert testen~~ ✅ Google getestet (`scripts/test_google_login.py`, echtes Konto, 228 Kontakte)
5. Kontaktabruf: Google People API (alle Felder, paginiert) + Outlook-Datei-Parser (`sources/outlook_file.py` ✅) ins neutrale Modell normalisieren
6. ~~Matching-Logik~~ ✅ `matching/engine.py`, gegen echte Daten verifiziert (99 identisch / 87 abweichend / 38 nur-Gmail / 363 nur-Outlook). Fuzzy-Schwelle 90, Adressvergleich fuzzy (≥82).
7. ~~Diff-UI in Streamlit~~ ✅ `app.py` — Sidebar (Sprache, Gmail-OAuth, Outlook-Upload, Vergleichen) + zentrale Ansicht mit `segmented_control` über die vier Kategorien. Start: `streamlit run contact_diff_wizard/app.py` oder `.claude/launch.json`.
8. README ✅ (bei Feature-Fortschritt aktualisieren)

### Stand UI
Master-Detail: links Kontaktliste (eine Zeile/Kontakt, in der „abweichend"-Ansicht mit Δ-Icon-Spalte + Anzahl, sortiert nach meisten Abweichungen), rechts Gmail↔Outlook-Seitenvergleich (abweichende Felder gelb + oben, übereinstimmende eingeklappt). Pro abweichendem Feld „übernehmen: Gmail/Outlook/beide" → „Entscheidungen als CSV herunterladen" (reine Arbeitsliste, kein Write-back). `CDW_DEV_OUTLOOK=<pfad>` lädt lokal eine Datei vor (Dev). In der laufenden App gegen echte Daten getestet.

### Noch offen / Feinschliff
- Prev/Next-Buttons im Detail (durch alle Abweichungen blättern ohne zurück zur Liste)
- Dubletten-Ansicht (22 Gruppen bündeln mehrere Kontakte aus *einer* Quelle)
- `report.py` Spaltenüberschriften/Feldlabels sind noch hart Deutsch → i18n
- Fuzzy-Schwelle / `PHONE_MATCH_MIN_NAME_SIM` ggf. am UI-Feedback justieren
- Packaging/README-Feinschliff für Fremdnutzer (PyInstaller später)
