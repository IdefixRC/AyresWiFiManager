# AyresWiFiManager

[![Version](https://img.shields.io/badge/version-2.4.0-4361ee)](https://github.com/IdefixRC/AyresWiFiManager/releases)
[![Platform](https://img.shields.io/badge/platform-ESP32-2ec27e?logo=espressif)](https://www.espressif.com/en/products/socs/esp32)
[![Arduino](https://img.shields.io/badge/framework-Arduino-00979d?logo=arduino)](https://www.arduino.cc/)
[![License](https://img.shields.io/badge/license-MIT-6c757d)](LICENSE)

> **This is a fork.** [IdefixRC](https://github.com/IdefixRC) maintains it to keep AyresWiFiManager current with recent Arduino-ESP32 cores and to add what our own projects need, starting with [Monitor-Buddy](https://github.com/IdefixRC/Monitor-Buddy). The original library is [ayresnet/AyresWiFiManager](https://github.com/ayresnet/AyresWiFiManager), and the credit for it belongs to its author. We offer our changes back to the original author as pull requests, so the fixes end up where everyone can use them. If you build on Arduino-ESP32 core 3.x, this fork may carry fixes that upstream has not merged yet.

AyresWiFiManager (AWM) is an ESP32 library for Wi-Fi provisioning and connectivity management. It combines a captive portal, LittleFS credential storage, explicit fallback policies, reconnection control, NTP synchronization and field diagnostics behind a small Arduino-friendly API.

[Leer en español](README.es.md)

## Why AWM

- Captive portal with SoftAP, DNS catch-all and operating-system detection routes.
- Responsive portal UI served from LittleFS, with embedded GZIP pages as fallback.
- Wi-Fi scanning, credential provisioning and configurable portal inactivity timeout.
- Portal in English, Spanish and German, with automatic browser language detection and an optional language menu.
- Explicit fallback policies: `ON_FAIL`, `NO_CREDENTIALS_ONLY`, `SMART_RETRIES`, `BUTTON_ONLY` and `NEVER`.
- Non-blocking reconnection driver with configurable backoff and attempt windows.
- Background time sync (NTP with an HTTP `Date` fallback) that never blocks the loop and keeps your timezone.
- Unified connectivity state and diagnostic information for application code.
- Automatic LED patterns and boot-button actions.
- Optional credential encryption at rest.
- Optional compile-time logging.

## Compatibility

Version 2.4.0 officially supports:

- ESP32 using the Arduino framework.
- Arduino-ESP32 core 2.x and 3.x.
- ArduinoJson 6.21.2 or newer within major version 6.
- LittleFS, DNSServer, WebServer and HTTPClient from the ESP32 Arduino core.

Version 2.4.0 supports ESP32 exclusively.

## Installation

This fork isn't published to a library registry. If you install `AyresWiFiManager` from a registry, you get the upstream library, which doesn't include this fork's changes.

### Arduino IDE

Download the source ZIP of the latest release from [Releases](https://github.com/IdefixRC/AyresWiFiManager/releases) and add it with **Sketch → Include Library → Add .ZIP Library…**. Make sure ArduinoJson 6 is installed. The portal has built-in pages, so a LittleFS upload is optional unless you customize the UI.

### PlatformIO

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
board_build.filesystem = littlefs

lib_deps =
  https://github.com/IdefixRC/AyresWiFiManager.git#2.4.0
```

Replace `2.4.0` with the latest release tag. To use the upstream library from the PlatformIO registry instead, use `ayresnet/AyresWiFiManager@^2.3.0`.

## Quick start

```cpp
#include <AyresWiFiManager.h>

AyresWiFiManager wifi;

void setup() {
  Serial.begin(115200);

  wifi.setHostname("my-device");
  wifi.setAPCredentials("MyDevice-Setup", "change-me");
  wifi.setLanguage(AyresWiFiManager::Language::AUTO);
  wifi.setLanguageSwitcher(true);
  wifi.setPortalTimeout(300);
  wifi.setAPClientCheck(true);
  wifi.setWebClientCheck(true);
  wifi.setFallbackPolicy(
      AyresWiFiManager::FallbackPolicy::SMART_RETRIES);
  wifi.setSmartRetries(3, 60000);

  wifi.begin();
  wifi.run();
}

void loop() {
  wifi.update();
  wifi.reintentarConexionSiNecesario();
}
```

Use an empty AP password for an open provisioning network, or at least eight characters for a protected SoftAP.

To generate a unique setup name from the Station MAC:

```cpp
const String macSuffix = AyresWiFiManager::getMacSuffix(); // e.g. "4C25"
wifi.setHostname(String("my-device-") + macSuffix);
wifi.setAPCredentials(String("MyDevice-Setup-") + macSuffix, "change-me");

const String fullMac = AyresWiFiManager::getMacAddress();
```

## Connectivity state and diagnostics

AWM exposes one primary state so applications do not need to combine several low-level checks:

```cpp
AyresWiFiManager::State state = wifi.getState();

Serial.println(AyresWiFiManager::stateToString(state));
Serial.println(AyresWiFiManager::errorToString(wifi.getLastError()));
Serial.println(wifi.getReconnectCount());
Serial.println(wifi.getLastInternetCheck());
```

Available states:

- `OFFLINE`
- `WIFI_CONNECTING`
- `WIFI_CONNECTED`
- `INTERNET_OK`
- `NO_INTERNET`
- `PORTAL_ACTIVE`

`PORTAL_ACTIVE` takes precedence while the captive portal is open, including AP+STA operation. `INTERNET_OK` and `NO_INTERNET` are updated when `hayInternet()` runs. `getLastInternetCheck()` returns the last check time in milliseconds since boot.

## Lifecycle

- `begin()` initializes GPIO, Wi-Fi and LittleFS, then loads stored credentials.
- `run()` handles the boot-button window, performs the initial connection, waits for the time (see [Time sync](#time-sync)) and applies the selected fallback policy.
- `update()` serves HTTP and DNS requests, updates LED patterns, handles portal timeouts and drives the time sync. Call it on every loop iteration.
- `reintentarConexionSiNecesario()` advances the non-blocking reconnection state machine.

## Time sync

The ESP32 has no battery-backed clock, so every boot starts in 1970. After each connection, AWM starts SNTP (`time.google.com`, `time.cloudflare.com`, `pool.ntp.org`) and rotates to other servers every 10 seconds, for three rounds. If NTP doesn't answer, it falls back to the HTTP `Date` header (see below). The sync runs in the background and `update()` drives it; only the HTTP fallback uses a short-lived task of its own.

- `run()` waits for the time after the initial connection, as in earlier versions: until the sync succeeds or gives up (about 45 seconds in the worst case, without internet). `setTimeSyncWait(ms)` caps that wait, and `setTimeSyncWait(0)` returns straight away.
- Every reconnect starts a new sync, but never waits.
- `isTimeSynced()` is `true` once the system clock is valid (2017 or later). Check it before anything that needs the real time, such as HTTPS with certificate checks.
- `getTimeSyncStatus()` returns `IDLE`, `SYNCING`, `SYNCED` or `FAILED`. `FAILED` means AWM gave up for this connection; SNTP keeps retrying in the background, so it can still become `SYNCED`.
- AWM keeps your timezone. Set `TZ` before `run()` and `localtime()` keeps returning local time after every sync. Without `TZ`, the clock is UTC.
- `setTimeSync(false)` turns all of this off, for applications that run their own NTP client. Call it before `run()`.

```cpp
void setup() {
  setenv("TZ", "AEST-10", 1); // optional: your local timezone
  tzset();

  wifi.setTimeSyncWait(0);    // don't hold up setup() for the time
  wifi.begin();
  wifi.run();
}

void loop() {
  wifi.update();
  wifi.reintentarConexionSiNecesario();

  if (wifi.isTimeSynced()) {
    // the clock is real: HTTPS certificate checks and timestamps work
  }
}
```

**Upgrading from 2.4.x.** `run()` waits as before. Reconnects now re-sync the time reliably and never wait. AWM no longer forces the timezone to `UTC0`; if you never set `TZ`, nothing changes. `getTimestamp()` returns 0 until the clock reads 2017 or later. The `setBusyCallback()` callback is now also called while `run()` waits for the time.

## Connectivity checks, privacy and trust

`hayInternet()` is an **optional reachability probe**, not a security check. When called, it performs an HTTP request to `http://clients3.google.com/generate_204` and returns `true` only for an HTTP `204` response. This updates `INTERNET_OK` or `NO_INTERNET`; it does not send the configured Wi-Fi SSID, Wi-Fi password, encryption key, portal form data, or application payload.

After connecting, AWM also tries to synchronize time with NTP. If NTP is unavailable, it can use the public HTTP `Date` header from `http://google.com` or `http://worldtimeapi.org/api/ip` as a fallback. This fallback likewise does not transmit stored credentials.

Because those probes use plain HTTP, a captive network, proxy, or malicious network can forge, redirect, or modify their response. Therefore:

- Treat `hayInternet()` as a practical indication of network reachability, not proof that a connection is trusted or private.
- Do not make authorization, payment, firmware-validation, or other security-sensitive decisions solely from `INTERNET_OK`, `NO_INTERNET`, or the HTTP time fallback.
- Applications that exchange sensitive data must use their own HTTPS/TLS connection and validate the remote service as appropriate.

HTTP is intentional here: it keeps the reachability test lightweight and compatible with captive networks. HTTPS can provide stronger authenticity, but requires certificate handling and consumes additional flash/RAM on constrained devices.

## Captive portal

The portal uses these local endpoints:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Portal UI |
| `GET` | `/scan` or `/scan.json` | Nearby Wi-Fi networks |
| `GET` | `/info` | Library, AP and host information, plus the portal language settings (`lang`, `lang_switch`) |
| `POST` | `/save` | Save credentials and restart |
| `POST` | `/erase` | Remove only `/wifi.json` or perform a confirmed JSON reset |

Captive-network detection routes for Android, iOS and Windows redirect to the portal when captive mode is enabled.

The recovery section offers two different operations. `scope=wifi` removes only `/wifi.json`. `scope=all` searches LittleFS recursively; protected files are honored unless `force=1` is explicitly included. The portal's full-reset action uses `force=1`, reports how many files were found, removed or failed, and restarts only when the operation completes without errors.

AWM closes every file handle it owns before deleting and retries each removal three times. It cannot safely close a handle owned by another library or application component; such files are reported as failed instead of claiming a successful reset.

To replace the built-in pages, put your own `index.html`, `success.html` and `error.html` in your project's `data/` folder and upload them to LittleFS (in PlatformIO: `pio run --target uploadfs`). Pages in LittleFS take precedence over the built-in ones, including their language handling. Use `setHtmlPathPrefix()` when storing them under a subdirectory.

## Portal language

The built-in portal pages are available in English, Spanish and German. Two settings control them, both called in `setup()` before `begin()`:

```cpp
wifi.setLanguage(AyresWiFiManager::Language::AUTO); // default; AUTO, EN, ES or DE
wifi.setLanguageSwitcher(true);                     // default; false hides the language menu
```

| `setLanguage` | Language shown when the portal opens |
| --- | --- |
| `AUTO` (default) | The browser's language if the portal supports it, otherwise English |
| `EN` | English |
| `ES` | Spanish |
| `DE` | German |

**How `AUTO` decides.** The page reads the browser's preferred languages in order (on a phone, its language settings) and uses the first one the portal supports, matching on the language only, not the region:

| Browser languages | Portal shows |
| --- | --- |
| `es-AR` | Spanish |
| `de-CH`, `en` | German |
| `pt-BR`, `es` | Spanish (the second preference is supported) |
| `fr-FR`, `it` | English (neither is supported yet) |

If none of the browser's languages is supported, or the browser reports none, the portal falls back to English.

**The language menu.** Unless you turn it off with `setLanguageSwitcher(false)`, every page shows a language menu (globe icon) in its header, so the user can switch at any time. A fixed `setLanguage()` value only chooses the starting language. The choice carries over to the success and error pages after saving.

| `setLanguage` | `setLanguageSwitcher` | Result |
| --- | --- | --- |
| `AUTO` | `true` (default) | Browser language or English; the user can change it |
| `AUTO` | `false` | Browser language or English; no manual choice |
| `EN` / `ES` / `DE` | `true` | Starts in that language; the user can change it |
| `EN` / `ES` / `DE` | `false` | Locked to that language |

The setup page reads both settings from `/info` each time it loads, so a later change takes effect on the next page load. The success and error pages don't call `/info`; they take the language and menu state from the address the setup page submits to.

**Upgrading from 2.3.x.** The built-in portal used to be Spanish only. With the default `AUTO`, browsers in other languages now see English (or German). To keep the old behaviour, call `setLanguage(AyresWiFiManager::Language::ES)` and `setLanguageSwitcher(false)`.

**Custom pages.** Pages you upload to LittleFS replace the built-in ones completely, including their language handling.

**Adding a language.** Add a value to `Language` and its code to `languageCode()` in `AyresWiFiManager.cpp`, add a table to the `i18n` block of each page in `data/`, then regenerate the built-in pages (see [Built-in portal pages](#built-in-portal-pages)). `tools/check_i18n.py` reports any missing or unused text. Translations are welcome as pull requests.

## Fallback policies

- `NO_CREDENTIALS_ONLY` — default; opens the portal only when no credentials exist.
- `ON_FAIL` — opens the portal after the initial connection fails.
- `SMART_RETRIES` — opens it after the configured number of reconnect failures.
- `BUTTON_ONLY` — only a physical or application action opens it.
- `NEVER` — disables automatic portal fallback.

## Button and LED

Default pins are GPIO 0 for the active-low button and GPIO 2 for the LED.

The button is read only while `run()` starts: press it within the first 3 seconds (for example, hold it while the device boots) and keep holding:

- 2–5 seconds opens the portal. `enableButtonPortal(false)` disables this.
- 5 seconds or longer erases the stored credentials and restarts.

LED patterns:

- Slow blink: disconnected from Wi-Fi.
- Fast blink: connecting or scanning.
- Solid: connected to Wi-Fi.
- Double blink: Wi-Fi connected without verified Internet access.
- Triple blink: captive portal active.

Pins can be changed with the constructor:

```cpp
AyresWiFiManager wifi(LED_PIN, BUTTON_PIN);
```

## Credential storage and encryption

Credentials are stored in `/wifi.json`. Select the storage mode before `begin()` with one boolean; the key must contain exactly 16 bytes when encryption is enabled:

```cpp
wifi.setCredentialEncryption(true, myPrivateKey);
wifi.begin();
```

Use `false` instead of `true` for plaintext storage. Changing the value migrates an existing file automatically in either direction, provided the same key is supplied. The method returns `false` and leaves encryption disabled when the key is invalid.

Do not commit a real key to a public repository. With encryption disabled, the file contains only `{"ssid":"...","password":"..."}`. With encryption enabled, the complete credential record is stored as one authenticated AES-128-GCM envelope represented by a single opaque JSON string, such as `"QVdNA..."`; it exposes no field names or algorithm metadata. Older encrypted objects and legacy CBC records are read and automatically migrated to this envelope. This still does not protect a device whose firmware and key can both be extracted; stronger threat models require hardware-backed storage.

AWM deliberately does not embed an AES key. The sketch using the library supplies its own 16-byte key; each project must decide how to provision and protect it. For public source repositories, keep the real key outside version control (for example, in a private build configuration or external provisioning process).

### Reusing credentials without exposing them

Applications that need the stored Wi-Fi password for another local access check do not need to retrieve or duplicate it:

```cpp
wifi.setAPCredentialsUsingStoredPassword("Device-Control");

if (wifi.verifyWiFiPassword(candidate)) {
  // Authorized.
}
```

`setAPCredentialsUsingStoredPassword()` configures the SoftAP inside AWM and returns `false` when the stored password is not valid for WPA (8 to 63 characters). `verifyWiFiPassword()` returns only a boolean and uses a comparison whose work does not depend on the first differing character. `getWiFiPass()` remains available for source compatibility, but new integrations should prefer these methods so the secret stays owned by AWM.

## Logging

AWM uses `AyresLog.h` internally and retains the `AWM_LOGE`, `AWM_LOGW`, `AWM_LOGI`, `AWM_LOGD` and `AWM_LOGV` macros for application diagnostics.

```ini
build_flags =
  -D AWM_ENABLE_LOG=1
  -D AWM_LOG_LEVEL=3
  -D AWM_LOG_TAG=\"AWM\"
```

Set `AWM_ENABLE_LOG=0` to compile logging out. Levels range from 1 (`ERROR`) to 5 (`VERBOSE`).

## Repository layout

```text
data/          Source of the built-in portal pages
examples/      Arduino and PlatformIO examples
src/           Public headers, library implementation and the generated AWM_html_gz.h
tools/         Checks for the built-in pages and their translations, and host tests
.github/       Continuous integration
```

The local `src/main.cpp` development harness is intentionally ignored and is not distributed as part of the library.

## Built-in portal pages

The pages in `data/` are compressed into `src/AWM_html_gz.h`, which the library serves whenever LittleFS has no page of the same name. After editing a page, regenerate the header and run the checks:

```bash
python ayres_gzip.py data/index.html data/success.html data/error.html -o src/AWM_html_gz.h
python tools/check_portal_assets.py
python tools/check_i18n.py
```

`ayres_gzip.py` is the AyresNet GZIP Asset Compiler. AyresNet keeps it out of the repository (it is listed in `.gitignore`), so restore the last published version from the Git history before the first use:

```bash
git restore --source=8871946 -- ayres_gzip.py
```

`tools/check_portal_assets.py` confirms that the header matches `data/`, and `tools/check_i18n.py` confirms that every page's translations are complete. CI runs both, plus the tools' own tests, on every pull request.

## License

MIT © AyresNet. See [LICENSE](LICENSE).
