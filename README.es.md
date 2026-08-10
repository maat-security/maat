# Maat 🪶

Your identity, in balance.

![License: MIT](https://img.shields.io/badge/License-MIT-C9A84C.svg)
![By Heru](https://img.shields.io/badge/by-Heru-2D2D2D.svg)
![Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-555555.svg)

🌐 También disponible en: [English](README.md)

Un proyecto open source de Heru · heru.life · Licencia MIT

## Tabla de Contenidos

- [El Problema Que Nadie Está Resolviendo](#el-problema-que-nadie-está-resolviendo)
- [Qué Hace Maat](#qué-hace-maat)
- [Por Dónde Empezar](#por-dónde-empezar)
- [Cómo Empezar](#cómo-empezar)
- [Lo Que Nunca Hace](#lo-que-nunca-hace)
- [Principio de Diseño: Local-First, Sin Excepciones](#principio-de-diseño-local-first-sin-excepciones)
- [El SIM Swap Está en el Modelo](#el-sim-swap-está-en-el-modelo)
- [Roadmap](#roadmap)
- [Estado de Implementación](#estado-de-implementación)
- [Cómo Contribuir](#cómo-contribuir)
- [Seguridad](#seguridad)
- [Acerca de](#acerca-de)

## El Problema Que Nadie Está Resolviendo

Administrás políticas de zero-trust en el trabajo. Revisás access logs. Sabés qué es un blast radius.

Y tu Gmail personal se recupera por SMS al mismo teléfono donde vive tu app de TOTP.

Toda herramienta de seguridad hecha para uso personal evalúa cuentas de forma aislada. Los gestores de contraseñas marcan passwords débiles. Have I Been Pwned te dice si tu correo apareció en un breach. Ninguna responde la única pregunta que importa:

Si un atacante compromete una cuenta, ¿cuánto más cae con ella?

Los canales de recuperación son la superficie de ataque real. La recuperación de cuenta existe precisamente para saltarse la autenticación. Un usuario con passkey en Gmail y un número de teléfono de recuperación por SMS tiene, en la práctica, seguridad de nivel SMS. La puerta trasera es más débil que la puerta principal, y ninguna herramienta te lo está mostrando.

## Qué Hace Maat

Maat mapea tu identidad digital como un grafo de dependencias — cada cuenta, factor de autenticación, dispositivo, canal de recuperación y proveedor, y cada relación entre ellos.

A partir de ese mapa, te dice lo que realmente importa:

- "Si te roban el teléfono, estas 6 cuentas quedan expuestas de inmediato."
- "Tu correo y tu teléfono se protegen mutuamente. Si perdés uno, perdés los dos."
- "Tu TOTP de GitHub no tiene backup. Si perdés el teléfono, perdés el acceso para siempre."
- "Tu banco tiene autenticación fuerte, pero se puede recuperar por SMS. En la práctica, tiene seguridad de nivel SMS."

Después te da una lista priorizada de acciones, ordenada por cuántas cuentas protegés con cada corrección. El grafo es el motor. Las consecuencias son la interfaz.

## Por Dónde Empezar

No hay un camino obligatorio. Empezá con lo que tengas:

- Importá el export de tu gestor de contraseñas — trae tu inventario completo de cuentas en minutos.
- Respondé preguntas sobre tus cuentas — repasá cómo te autenticás y cómo recuperarías el acceso si perdieras tu factor principal.
- Conectá una integración — GitHub y otros leen tu configuración de seguridad directamente vía API.

Usá una. Usá las tres. Hacelas en el orden que quieras. Maat construye tu panorama con lo que le den y muestra resultados de inmediato — no hay una puerta de "configuración completa" antes de obtener valor.

## Cómo Empezar

> **Pre-alpha.** Todavía no está publicado como paquete ni como binario — se corre desde el código fuente.

```bash
git clone https://github.com/maat-security/maat.git
cd maat
python -m venv .venv
.venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

La app misma te guía por los tres caminos opcionales de onboarding — importar el export de tu gestor de contraseñas, responder el cuestionario guiado, o conectar una integración (todavía no construida; ver [Estado de Implementación](#estado-de-implementación)). Usá uno, usá los tres, en el orden que quieras.

`pip install maat` y binarios nativos instalables son los objetivos de v1/v4 del [Roadmap](#roadmap) de abajo, no algo que puedas hacer hoy.

## Lo Que Nunca Hace

- Almacenar passwords, seeds de TOTP o recovery codes.
- Enviar datos a ningún lado. Sin telemetría, sin backend, sin cuenta requerida.
- Ejecutar cambios en tu nombre.
- Dejar un archivo sin cifrar en el disco.

## Principio de Diseño: Local-First, Sin Excepciones

El archivo que produce Maat es el mapa completo de tu identidad digital. Guardarlo en la nube crearía exactamente el punto único de falla que la herramienta existe para eliminar. Todo corre en tu máquina. Las únicas llamadas hacia afuera son a Have I Been Pwned (k-anonymity, los hashes de tus passwords nunca salen de tu dispositivo) y las integraciones de proveedores que conectés explícitamente.

## El SIM Swap Está en el Modelo

Tu operadora móvil puede sufrir un SIM swap. Maat modela esto y te muestra qué cuentas quedan expuestas si portan tu número sin tu consentimiento. Las remediaciones son reales y accionables: bloqueo de número a nivel operadora, migración a eSIM, o quitar la recuperación por teléfono de las cuentas críticas.

## Roadmap

- **v1 — MVP:** Import de gestor de contraseñas, chequeo de HIBP, cuestionario guiado, mapa de dependencias, score de postura, lista de acciones priorizadas, almacén local cifrado.
- **v2 — Monitoreo de drift:** Re-import periódico, detección de cambios, sesiones de revisión livianas.
- **v3 — Remediación guiada:** Runbooks específicos por proveedor con advertencias de secuencia, simulación pre/post, verificación vía API.
- **v4 — Apps de escritorio:** Instaladores nativos para Windows, macOS y Linux. Mismo motor, sin necesidad de terminal.

## Estado de Implementación

_Última actualización: 09/08/2026._ Lo que realmente funciona hoy, contra lo que sigue siendo roadmap.

**Funciona hoy:**

- Bóveda local cifrada — clave derivada de passphrase, nunca se escribe texto plano en disco
- Motor del grafo de dependencias — validación de nodos/aristas, blast radius, cut vertices, detección de ciclos
- Score de postura — los cuatro componentes ponderados del spec del producto, con desglose auditable
- Cuestionario guiado — cuatro preguntas salteables por cuenta, como máquina de estados
- Import de gestor de contraseñas — 1Password (`.1pux`), Bitwarden (JSON), KeePass (XML), CSV genérico — con detección de reutilización de passwords y chequeo de Have I Been Pwned en memoria, ninguno de los dos persiste el valor de la password
- Integración con Have I Been Pwned — chequeo k-anonymity contra Pwned Passwords (solo un prefijo de 5 caracteres del hash sale del dispositivo), corre en un hilo de fondo durante el import, aparece como gap priorizado ("esta password está filtrada") con su propio runbook de remediación
- Remediación guiada — runbooks específicos por proveedor (Google, GitHub, Microsoft, Apple, fallback genérico honesto para el resto), simulación de impacto antes/después, historial de remediaciones auto-reportadas
- Export a HTML autocontenido — score, desglose, gaps priorizados e historial de remediaciones en un solo archivo estático, sin recursos externos y sin secretos, guardado donde el usuario elija
- UI bilingüe (inglés/español) y toggle de tema oscuro/claro
- Shell de escritorio (CustomTkinter) con spec de empaquetado PyInstaller y workflow de CI para 3 sistemas operativos

**Gaps conocidos:**

- No hay pantalla de visualización del grafo — el grafo existe y se consulta, pero no hay nada que mostrar visualmente todavía
- No hay suite de tests automatizados commiteada — todo lo de arriba se verificó con scripts descartables durante el desarrollo, no con un suite de `pytest` en el repo

**Sin empezar:**

- Cualquier integración de API de proveedor (GitHub, Google Workspace, Microsoft Entra) — postergado a propósito, para terminar primero el núcleo local-first
- Monitoreo de drift / sesiones de revisión periódicas (Roadmap v2)
- Instaladores nativos publicados (Roadmap v4) — el workflow de CI existe pero nunca se disparó con un tag de release real
- La excepción acotada de remediación automática para escrituras de API mínimas y no destructivas (ej. revocar un PAT vencido de GitHub) — bloqueada hasta tener la integración de arriba

Ver [TODO.md](TODO.md) para la lista priorizada de próximos pasos, y [QA.md](QA.md) para el plan de testeo manual que cubre Windows, macOS y Linux.

## Cómo Contribuir

**Bugs.** Reportalos como GitHub Issues.

**Pull requests.** Hacé fork del repo, creá una branch a partir de `main`, abrí un PR contra `main`.

**Traducciones.** `/docs/en` es la fuente de verdad. Las traducciones van en `/docs/{locale}`. Un PR que agregue o actualice una traducción requiere revisión de un hablante nativo de ese idioma antes de mergear.

El código y los issues están en inglés. `/docs/es` es la excepción — lo mantiene oficialmente en español el equipo core, no es una traducción comunitaria.

## Seguridad

Los problemas de seguridad deben reportarse en privado a alvartorres@heru.life. No abras issues públicos en GitHub para vulnerabilidades de seguridad.

## Acerca de

Maat es un proyecto open source donado a la comunidad de seguridad por Heru (heru.life). Su nombre viene de la diosa egipcia de la verdad, la justicia y el equilibrio — cuya pluma era el estándar contra el que se pesaba el corazón. Si el corazón pesaba más que la pluma, había desequilibrio. Eso es lo que encuentra Maat. Licencia MIT.
