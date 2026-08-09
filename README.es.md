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

> **Pre-alpha.** El instalador y el CLI que siguen son placeholders para el MVP de v1. Nada de esto está publicado todavía.

Instalación (planeada):

```bash
pip install maat
```

Corré el onboarding usando cualquiera de los tres caminos opcionales — de forma independiente o combinada:

```bash
# Camino 1: importar el export de tu gestor de contraseñas
maat import --source 1password export.1pux

# Camino 2: responder el cuestionario guiado
maat questionnaire

# Camino 3: conectar una integración
maat connect github
```

Después mirá tu score de postura y las acciones priorizadas:

```bash
maat status
```

Esto llega en v1. Maat está en pre-alpha — todavía no hay una versión instalable.

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

## Cómo Contribuir

**Bugs.** Reportalos como GitHub Issues.

**Pull requests.** Hacé fork del repo, creá una branch a partir de `main`, abrí un PR contra `main`.

**Traducciones.** `/docs/en` es la fuente de verdad. Las traducciones van en `/docs/{locale}`. Un PR que agregue o actualice una traducción requiere revisión de un hablante nativo de ese idioma antes de mergear.

El código y los issues están en inglés. `/docs/es` es la excepción — lo mantiene oficialmente en español el equipo core, no es una traducción comunitaria.

## Seguridad

Los problemas de seguridad deben reportarse en privado a alvartorres@heru.life. No abras issues públicos en GitHub para vulnerabilidades de seguridad.

## Acerca de

Maat es un proyecto open source donado a la comunidad de seguridad por Heru (heru.life). Su nombre viene de la diosa egipcia de la verdad, la justicia y el equilibrio — cuya pluma era el estándar contra el que se pesaba el corazón. Si el corazón pesaba más que la pluma, había desequilibrio. Eso es lo que encuentra Maat. Licencia MIT.
