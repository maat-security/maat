"""Minimal i18n layer for Maat.

Two locales for now: English and Spanish. Every user-facing string in
the app is written as the literal English text and used as the lookup
key here — t() returns the Spanish translation when the active locale
is "es", and falls back to the English text unchanged for English or
for any string with no translation entry yet.

Strings with a runtime value (a count, a length) are written as
{placeholder}-style templates: translate the template with t(), then
.format() the result — never f-string the value in before translating,
or the string won't match a dictionary key.
"""

DEFAULT_LOCALE = "en"
LOCALES = ("en", "es")

_current_locale = DEFAULT_LOCALE

# Tone matches README.es.md: informal Latin American Spanish ("vos"),
# direct, no marketing language. Technical terms stay in English.
_ES = {
    # Welcome screen: intro
    "Maat": "Maat",
    "Your identity, in balance.": "Tu identidad, en equilibrio.",
    (
        "Maat maps your digital identity as a dependency graph — every "
        "account, device, and recovery channel — and shows you which "
        "single point of failure puts the most at risk. Local-first. "
        "No account, no telemetry, no data leaving this device."
    ): (
        "Maat mapea tu identidad digital como un grafo de dependencias — "
        "cada cuenta, dispositivo y canal de recuperación — y te muestra "
        "cuál es el punto único de falla que más te expone. Local-first. "
        "Sin cuenta, sin telemetría, sin que ningún dato salga de este "
        "dispositivo."
    ),

    # Welcome screen: top bar controls
    "🌙 Dark": "🌙 Oscuro",
    "☀️ Light": "☀️ Claro",

    # Create vault
    "Create Your Vault": "Creá Tu Bóveda",
    (
        "Choose a passphrase. It never leaves this device and cannot be "
        "recovered if lost."
    ): (
        "Elegí una passphrase. Nunca sale de este dispositivo y no se "
        "puede recuperar si la perdés."
    ),
    "Passphrase": "Passphrase",
    "Confirm Passphrase": "Confirmar Passphrase",
    (
        "At least {n} characters. Longer is better than complex — a "
        "plain phrase beats P@ssw0rd!"
    ): (
        "Al menos {n} caracteres. Más largo es mejor que complejo — "
        "una frase simple le gana a P@ssw0rd!"
    ),
    "Passphrase cannot be empty.": "La passphrase no puede estar vacía.",
    "Passphrase must be at least {n} characters.": "La passphrase debe tener al menos {n} caracteres.",
    "Passphrases do not match.": "Las passphrases no coinciden.",
    "Create": "Crear",

    # Unlock vault
    "Unlock Your Vault": "Desbloqueá Tu Bóveda",
    (
        "Your vault is encrypted at rest. Enter your passphrase to continue."
    ): (
        "Tu bóveda está cifrada en reposo. Ingresá tu passphrase para continuar."
    ),
    "Unlock": "Desbloquear",

    # store.py error messages, surfaced verbatim in the UI
    "Incorrect passphrase.": "Passphrase incorrecta.",
    "A vault already exists. Use unlock_store() instead.": "Ya existe una bóveda. Usá unlock_store() en su lugar.",
    "No vault found. Use init_store() to create one.": "No se encontró una bóveda. Usá init_store() para crear una.",
    "Store is not open.": "La bóveda no está abierta.",

    # Dashboard shell
    "Import Password Manager": "Importar Gestor de Contraseñas",
    "Bring in your account inventory": "Traé tu inventario de cuentas",
    "Answer Questions": "Responder Preguntas",
    "Map how you authenticate and recover access": "Mapeá cómo te autenticás y recuperás el acceso",
    "Connect Integration": "Conectar Integración",
    "Let Maat read your configuration directly": "Dejá que Maat lea tu configuración directamente",
    "Coming Soon": "Próximamente",
    "This is coming in a future phase.": "Esto llega en una fase futura.",
    "Close": "Cerrar",
    "Vault": "Bóveda",
    "Graph coverage: —": "Cobertura del grafo: —",

    # Onboarding
    "Add your first accounts to see where you stand.": "Agregá tus primeras cuentas para ver dónde estás parado.",
    "Start": "Empezar",
    "Select your password manager export": "Seleccioná el export de tu gestor de contraseñas",
    "Supported exports": "Exports soportados",
    "All files": "Todos los archivos",
    "Confirm Format": "Confirmar Formato",
    "Which password manager is this export from?": "¿De qué gestor de contraseñas es este export?",
    "Import": "Importar",
    "Imported {n} account{s}.": "Se importaron {n} cuenta{s}.",

    # Questionnaire
    "Account name (e.g. Gmail)": "Nombre de la cuenta (ej. Gmail)",
    (
        "How critical is this account? 5 = most critical (financial, primary email)"
    ): (
        "¿Qué tan crítica es esta cuenta? 5 = más crítica (financiera, correo principal)"
    ),
    "Back": "Atrás",
    "Skip": "Saltear",
    "Next": "Siguiente",
    "Finish": "Terminar",
    "Finish and Return": "Terminar y Volver",
    "How do you normally sign in to this account?": "¿Cómo entrás normalmente a esta cuenta?",
    "Password": "Contraseña",
    "SMS": "SMS",
    "Push notification": "Notificación push",
    "TOTP app": "App de TOTP",
    "Biometric": "Biometría",
    "Passkey": "Passkey",
    "Hardware security key": "Llave de seguridad física",
    "If you lost that, how would you get back in?": "Si perdieras eso, ¿cómo volverías a entrar?",
    "Optional detail (e.g. which phone number)": "Detalle opcional (ej. qué número de teléfono)",
    "Backup email": "Correo alternativo",
    "Phone number": "Número de teléfono",
    "Recovery codes": "Códigos de recuperación",
    "Something else": "Otra cosa",
    "How is that recovery method itself protected?": "¿Cómo protegés ese método de recuperación?",
    (
        "Where do backup codes or your second-factor backup live?"
    ): (
        "¿Dónde viven los códigos de respaldo o el backup de tu segundo factor?"
    ),
    "e.g. printed in a drawer, in my password manager": "ej. impreso en un cajón, en mi gestor de contraseñas",
    (
        "Describe where — never enter the actual codes."
    ): (
        "Describí dónde — nunca ingreses los códigos reales."
    ),

    # Dashboard
    "Concentration": "Concentración",
    (
        "How much falls if your single riskiest point is compromised"
    ): (
        "Cuánto cae si se compromete tu punto más riesgoso"
    ),
    "Factor Resistance": "Resistencia de Factores",
    "How well your critical accounts resist phishing": "Qué tan bien resisten phishing tus cuentas críticas",
    "Recovery Hygiene": "Higiene de Recuperación",
    (
        "Whether your backdoors are weaker than your front doors"
    ): (
        "Si tus puertas traseras son más débiles que las principales"
    ),
    "Exposure and Freshness": "Exposición y Frescura",
    "Whether there are known breaches or stale data": "Si hay breaches conocidos o datos desactualizados",
    "Add More Data": "Agregar Más Datos",
    (
        "Your graph is empty. Add a few accounts to see your first result."
    ): (
        "Tu grafo está vacío. Agregá algunas cuentas para ver tu primer resultado."
    ),
    "No urgent gaps found.": "No se encontraron gaps urgentes.",
    "Graph coverage: {known}/{total}": "Cobertura del grafo: {known}/{total}",
}

TRANSLATIONS = {"es": _ES}


def get_locale() -> str:
    """Return the currently active locale code ('en' or 'es')."""
    return _current_locale


def set_locale(locale: str) -> None:
    """Set the active locale. Raises ValueError for anything outside LOCALES."""
    global _current_locale
    if locale not in LOCALES:
        raise ValueError(f"Unsupported locale: {locale!r}")
    _current_locale = locale


def t(s: str) -> str:
    """Translate s into the active locale.

    Falls back to s unchanged when the active locale is English, or
    when no translation entry exists yet for s.
    """
    return TRANSLATIONS.get(_current_locale, {}).get(s, s)
