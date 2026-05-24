# Linux Engineering Library

Append-only working file for Gemini-generated packets.

Source corpus already present in the repository:
- `runtime/knowledge/raw/rhcsa_raw.txt`

## Packet 1

```bash
#!/bin/bash
# ==============================================================================
# LINUX ENGINEERING LIBRARY - GENERATOR PACKET 1
# DOMENY: 1. Fundamentals, 2. History, 3. GNU Ecosystem, 4-5. Filesystems, 6-7. Permissions & ACL, 8-9. Identity & PAM
# ==============================================================================

set -e

# 1. Przygotowanie struktury katalogów klastra wiedzy
OUTPUT_DIR="linux-engineering-corpus/01_storage_and_identity"
mkdir -p "${OUTPUT_DIR}"

echo "[*] Generowanie wolumenu 1: Core Fundamentals, Storage & Identity Architecture..."

# 2. Budowanie pliku Markdown za pomocą bezpiecznego bloku EOF (bez ekspansji zmiennych powłoki)
cat << 'EOF' > "${OUTPUT_DIR}/01_fundamentals_storage_identity.md"
---
schema_version: "1.2"
domain: "Core Infrastructure & Storage Engineering"
subdomain: "Kernel Runtime, VFS, CoW Filesystems, PAM Authentication"
kernel_target: ">=5.15"
distro_agnostic: true
danger_level: "High"
idempotent: true
provenance:
  author: "Linux Engineering Library Archivist"
  verified_against: ["RHEL 9.4", "Ubuntu Server 24.04 LTS", "Debian 12"]
tags: ["kernel-space", "vfs", "xfs", "zfs", "acl", "pam", "production-ops"]
related_concepts: ["syscalls", "device-mapper", "authentication-stacks"]
---

# ROZDZIAŁ 1: FUNDAMENTY SYSTEMU, EKOSYSTEM GNU, INŻYNIERIA SYSTEMÓW PLIKÓW I ZARZĄDZANIE TOŻSAMOŚCIĄ

## 1.1 ARCHITEKTURA RDZENIA I ŚRODOWISKO URUCHOMIENIOWE (LINUX FUNDAMENTALS)

Linux to monolityczne jądro o architekturze wielozadaniowej z wywłaszczaniem (preemptive kernel), implementujące standardy POSIX. Wszystkie operacje niskopoziomowe — sterowniki urządzeń, stos sieciowy, planista procesów (CFS/EEVDF) oraz systemy plików — wykonują się w jednej, wspólnej, uprzywilejowanej przestrzeni adresowej jądra.

### 1.1.1 Izolacja Ring 0 vs Ring 3 i Mechanizm Syscalls
Stabilność systemu opiera się na sprzętowej izolacji pierścieni ochrony procesora (CPU Privilege Rings):
*   Ring 0 (Kernel Space): Pełny dostęp do instrukcji procesora, rejestrów kontrolnych i fizycznej pamięci RAM. Każdy błąd (np. odwołanie do błędnego wskaźnika) skutkuje wywołaniem procedury Kernel Panic.
*   Ring 3 (User Space): Izolowane środowisko dla aplikacji i demonów. Procesy nie mają bezpośredniego dostępu do sprzętu. 

Komunikacja między Ring 3 a Ring 0 odbywa się wyłącznie poprzez System Calls (Syscalls). Wywołanie syscalla (np. przez instrukcję sysenter lub syscall w architekturze x86_64) powoduje przełączenie kontekstu procesora w tryb Ring 0, wykonanie operacji przez jądro i powrót do przestrzeni użytkownika.

### 1.1.2 Podsystem Pamięci Wirtualnej i Alokacja Zasobów
Pamięć fizyczna jest mapowana na pamięć wirtualną za pomocą jednostki MMU (Memory Management Unit).
*   Stronicowanie (Paging): Domyślny rozmiar strony w architekturze x86_64 wynosi 4KB.
*   Huge Pages (Strony Anonimowe i Przeźroczyste — THP): Alokacja ciągłych bloków pamięci o rozmiarze 2MB lub 1GB. Kluczowa dla baz danych (PostgreSQL, Oracle) w celu redukcji narzutu na wyszukiwanie w tablicy stron (Page Table) i maksymalizacji efektywności bufora TLB (Translation Lookaside Buffer).
*   Overcommit i OOM Killer: Jądro domyślnie pozwala na alokację większej ilości pamięci wirtualnej, niż wynosi fizyczna dostępność RAM + Swap (vm.overcommit_memory = 0). W sytuacji krytycznego braku pamięci, podsystem *Out-Of-Memory Killer* oblicza punktację (oom_score) na podstawie zużycia RAMu i priorytetu procesu, a następnie bezpowrotnie zabija proces o najwyższym wskaźniku.

### 1.1.2.1 Polecenia Strojenia Środowiska Runtime

#### sysctl [CAUTION]
Modyfikacja parametrów jądra w locie w przestrzeni /proc/sys/.

```bash
# Sprawdzenie aktualnego wskaźnika agresywności wymiany pamięci (Swap)
sysctl vm.swappiness

# Produkcyjne obniżenie swappiness na serwerach bazodanowych (minimalizacja I/O wait)
sysctl -w vm.swappiness=10

# Zmiana limitów mapowania pamięci dla silników Elasticsearch/Lucene
sysctl -w vm.max_map_count=262144
```

## Packet 2

### 1.2 HISTORIA, STANDARYZACJA I EKOSYSTEM GNU/LINUX

Wspolczesne dystrybucje Enterprise dziela sie na odrebne rodziny, ktorych cykl zycia oraz determinizm operacyjny zaleza od doboru bibliotek bazowych oraz mechanizmow zarzadzania pakietami.

### 1.2.1 Dziedzictwo POSIX i Standardy LSB

Linux implementuje specyfikacje POSIX, co gwarantuje przenosnosc kodu zrodlowego pomiedzy roznymi systemami operacyjnymi typu UNIX. Kluczowym elementem ekosystemu jest glibc (GNU C Library) - fundamentalna biblioteka systemowa, stanowiaca interfejs programistyczny dla wszystkich aplikacji w przestrzeni uzytkownika.

Ostrzezenie architektoniczne: uszkodzenie pliku `/lib64/libc.so.6` powoduje natychmiastowy paraliż systemu. Zadna standardowa komenda, w tym `ls`, `cp` i `sh`, nie uruchomi sie, poniewaz linkowanie dynamiczne zostanie przerwane.

### 1.2.2 Niskopoziomowa Anatomia Menedzerow Pakietow

Rodzina RPM (DNF / RHEL / Rocky Linux):
- baza danych: przechowywana w `/var/lib/rpm/`
- mechanizm transakcyjny: DNF wspiera pelne wycofywanie zmian stanu systemu

`dnf history [SAFE / CAUTION]`

Zarzadzanie historia instalacji:

```bash
# Wyswietlenie listy ostatnich transakcji [SAFE]
dnf history

# Szczegolowy audyt konkretnej transakcji [SAFE]
dnf history info 14

# Wycofanie zmian wprowadzonych przez transakcje [CAUTION]
dnf history undo 14
```

Rodzina DEB (APT / Debian / Ubuntu):
- baza danych: `/var/lib/dpkg/`
- mechanizm kontrolny: `dpkg --verify`

Znaczenie operacyjne: modyfikacja plikow binarnych w `/bin/` lub `/sbin/` bez wiedzy administratora, wykryta przez `dpkg -V`, to bezposredni dowod na kompromitacje systemu.

### 1.2.3 Rozwiazywanie Blokad Subsystemow Pakietow

Czesty przypadek awarii w automatyzacji (Ansible/Puppet): proces instalacji zostaje zablokowany przez demony dzialajace w tle.

```bash
# 1. Identyfikacja procesu trzymajacego deskryptor pliku blokady [SAFE]
lsof /var/lib/dpkg/lock-frontends

# 2. Wymuszenie zakonczenia procesu [CAUTION]
kill -15 <PID_Z_POLECENIA_LSOF>

# 3. Jesli proces nie zwalnia blokady po 10 sekundach [CAUTION]
kill -9 <PID_Z_POLECENIA_LSOF>

# 4. Usuniecie osieroconych plikow blokad - tylko jesli proces na pewno nie zyje [CAUTION]
rm -f /var/lib/dpkg/lock-frontends
rm -f /var/lib/apt/lists/lock

# 5. Rekonfiguracja uszkodzonej bazy danych [CAUTION]
dpkg --configure -a
```

### 1.3 INZYNIERIA SYSTEMOW PLIKOW

System plikow mapuje logiczne struktury drzewa katalogow na fizyczne adresy blokowe nosnika (LBA). Warstwa VFS w jadze unifikuje ten proces, udostepniajac aplikacjom standardowe wywolania systemowe `open`, `read` i `write` niezaleznie od typu systemu plikow.

#### 1.3.1 EXT4 vs XFS: Porownanie Strukturalne

| Wlasciwosc | EXT4 | XFS |
|---|---|---|
| Podstawowa jednostka | Grupy blokow | Grupy alokacji (AG) |
| Zarzadzanie wolna przestrzenia | Bitmapy blokow | Drzewa B+ |
| Skalowanie wielordzeniowe | srednie | wysokie |
| Rozmiar wolumenu | do 1 EB | do 8 EB |
| Pomniejszanie (shrink) | tak, po odmontowaniu | nie |

Kluczowe pojecia:
- inode: struktura przechowujaca metadane pliku, bez nazwy pliku
- extenty: ciagle bloki dyskowe przypisane do pliku jako zakres adresow

#### 1.3.2 Zaawansowane Systemy Plikow CoW

Systemy copy-on-write eliminuja tradycyjne nadpisywanie danych. Przy modyfikacji bloku:
- dane sa zapisywane w nowym, wolnym miejscu na dysku
- metadane sa aktualizowane i wskazuja nowy adres
- stary blok jest zwalniany albo zachowywany przy snapshotach

#### 1.3.3 Zarzadzanie, Strojenie i Tworzenie Systemow Plikow

`mkfs.xfs [CAUTION]`

Formatowanie wolumenu. Operacja niszczy strukture danych na urzadzeniu docelowym.
