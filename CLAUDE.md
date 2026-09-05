# Projekt: Outlook ↔ Gmail Kontakt-Vergleichstool

> Diese Datei ist der Einstiegspunkt für eine Claude Code Session. Kontext, Entscheidungen und offene Punkte aus der Konzeptionsphase mit dem Nutzer (Chat-Interface) sind hier festgehalten, damit keine Rückfragen zu bereits getroffenen Entscheidungen nötig sind.

## Namensvorschläge (noch nicht final entschieden)

Im Konzeptions-Chat vorgeschlagen, Auswahl/Entscheidung steht noch aus — bei Bedarf in der Coding-Session nachfragen oder Platzhalter-Namen weiterverwenden:

1. **ContactSync Bridge**
2. **ContactMerge** / Kontaktabgleich
3. **Rosetta Contacts**
4. **ContactDiffWizard** (favorisierte Richtung laut Nutzer)
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
| Microsoft | `Contacts.Read` (Microsoft Graph) | Lesezugriff auf alle Outlook-Kontakte |

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
| Microsoft OAuth | `msal` (Microsoft Authentication Library) | offiziell von Microsoft gepflegt |
| Lokales UI | Streamlit (bevorzugt für schnellen Start) — alternativ FastAPI + Jinja2, falls mehr Kontrolle über den OAuth-Redirect-Flow nötig ist | Diff-Tabellen-Darstellung ist Streamlits Stärke |
| Fuzzy-Matching | `rapidfuzz` | für Namens-/Telefonnummer-Abgleich, wenn E-Mail als Schlüssel fehlt |
| Packaging (später, nicht MVP) | PyInstaller | einzelne ausführbare Datei ohne Python-Installation beim Endnutzer |

**Offene technische Frage, die in der ersten Coding-Session zu klären ist:** Streamlit hat keinen eingebauten Mechanismus für OAuth-Redirect-Callbacks (lokaler Callback-Server auf z. B. `localhost:8080/callback`). Ggf. Kombination nötig: kleiner lokaler HTTP-Server (z. B. via `http.server` oder FastAPI) nur für den OAuth-Redirect, danach Übergabe an Streamlit-UI. Muss beim Aufsetzen entschieden werden.

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
- Kein Electron/natives Desktop-Packaging
- Keine Implementierung von iCloud oder weiteren Anbietern im MVP (nur architektonisch vorbereiten, siehe oben) — konkrete Umsetzung erst nach MVP-Abschluss

## Arbeitsmodus des Nutzers

Der Nutzer möchte **keine einzige Zeile Code selbst anfassen** und arbeitet bewusst im **reinen Dialog-Modus über Claude Desktop (Code-Tab)** — nicht über die VS Code Extension. Konsequenzen für den Umgang in einer Coding-Session:

- Schritte in verständlicher Sprache erklären und Ergebnisse/Diffs visuell zusammenfassen, nicht voraussetzen, dass der Nutzer selbst Dateien öffnet oder Code liest
- Vor Zwischenschritten (z. B. OAuth-App-Registrierung in Google Cloud Console/Azure), die zwingend eine manuelle Aktion des Nutzers außerhalb des Chats erfordern, dies klar als solche kennzeichnen — das ist die Ausnahme, nicht die Regel
- Rückfragen und Freigaben ("passt das so?") statt stillschweigender Annahmen, analog zum iterativen Vorgehen aus der Konzeptionsphase dieses Dokuments

## Nächste Schritte für die erste Coding-Session

1. Repo-Grundgerüst anlegen (Ordnerstruktur, `requirements.txt`, `.gitignore` inkl. Token-/Credential-Dateien)
2. Google Cloud Console App-Registrierung gemeinsam mit dem Nutzer durchgehen (OAuth Consent Screen, Client-ID für Desktop-App)
3. Azure/Microsoft Entra App-Registrierung gemeinsam durchgehen (Redirect-URI für lokalen Callback, API-Permissions)
4. Minimalen OAuth-Flow für beide Anbieter isoliert testen (nur Login + Token erhalten, noch kein Kontaktabruf)
5. Kontaktabruf beider APIs implementieren, in einheitliches internes Datenmodell normalisieren
6. Matching-Logik implementieren und mit echten (anonymisierten Test-)Kontakten des Nutzers verifizieren
7. Diff-UI in Streamlit bauen
8. README für andere Nutzer schreiben (Setup-Anleitung: Python installieren, Repo klonen, `pip install -r requirements.txt`, starten)
