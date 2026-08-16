"""Tests gegen eine synthetische DB mit USMCs echtem Schema.

Schema 1:1 aus ``usmc/schema.py`` uebernommen (Paketversion 0.2.1), damit der
Adapter gegen dieselbe Tabellenstruktur getestet wird, die USMC real anlegt --
nicht gegen eine erfundene Vereinfachung. Siehe auch
``tests/test_backends_gardener.py``, dasselbe Muster fuer die Schwesterquelle.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from memoryhooker.backends.usmc import UsmcBackend
from memoryhooker.config import BackendConfig, Config
from memoryhooker.modes import evaluate_prompt
from memoryhooker.state import SessionState

_SCHEMA = """
CREATE TABLE usmc_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    agent_id TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE usmc_working (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'note',
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    tags TEXT,
    agent_id TEXT NOT NULL DEFAULT 'default',
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE usmc_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL DEFAULT 'general',
    severity TEXT NOT NULL DEFAULT 'medium',
    title TEXT NOT NULL,
    problem TEXT NOT NULL,
    solution TEXT NOT NULL,
    agent_id TEXT NOT NULL DEFAULT 'default',
    is_active INTEGER DEFAULT 1,
    confidence REAL DEFAULT 1.0,
    times_shown INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE usmc_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    current_task TEXT,
    handoff_notes TEXT
);

CREATE TABLE usmc_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Nachbau der realen Lesson #44 (USMC-Live-DB, 2026-08-16) -- genau der
# Eintrag, den Ticket T-20260816-972236043 als "erreicht keine Sitzung"
# beschreibt. Wortlaut gekuerzt, Kernbegriffe (Sitzung, Zustellkette, USMC,
# Lessons, MemoryHooker) unveraendert, damit der Kalibrierungstest gegen den
# echten Fall prueft statt gegen ein erfundenes Beispiel.
_LESSON_44_TITLE = "USMC-Lessons erreichen keine Sitzung - Zustellkette unterbrochen"
_LESSON_44_PROBLEM = (
    "Die Regel verlangt Lessons in USMC. Zugestellt wird aber ueber "
    "MemoryHooker mit backend.order = [gardener, files]. Der WorkflowHooker "
    "stellt gar nichts zu, er fuehrt nur checks=[closing_gate]. Gemessen: "
    "145 bach-lessons in Gardener, 0 USMC-Lessons."
)
_LESSON_44_SOLUTION = (
    "Bis zur Behebung jede Lesson doppelt ablegen. Dauerhafte Fixes: (a) "
    "Gardener-Quelle registrieren, oder (b) usmc als Backend-Eintrag in "
    "memoryhooker.toml. Festgehalten als P8 in .AI/PATTERNS.md."
)


def _make_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
    return sqlite3.connect(str(path))


def _insert_lesson(
    conn: sqlite3.Connection,
    *,
    lesson_id: int,
    title: str,
    problem: str,
    solution: str,
    severity: str = "medium",
    is_active: int = 1,
    agent_id: str = "claude-code",
) -> None:
    conn.execute(
        """
        INSERT INTO usmc_lessons
            (id, category, severity, title, problem, solution, agent_id,
             is_active, confidence, times_shown, created_at, updated_at)
        VALUES (?, 'general', ?, ?, ?, ?, ?, ?, 1.0, 0, '2026-08-16', '2026-08-16')
        """,
        (lesson_id, severity, title, problem, solution, agent_id, is_active),
    )
    conn.commit()


def _insert_fact(conn: sqlite3.Connection, *, category, key, value, confidence=0.9) -> None:
    conn.execute(
        """
        INSERT INTO usmc_facts (category, key, value, confidence, source, agent_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'agent:cli', 'cli', '2026-08-16', '2026-08-16')
        """,
        (category, key, value, confidence),
    )
    conn.commit()


def _insert_working(conn: sqlite3.Connection, *, content, priority=0, is_active=1, agent_id="cli") -> None:
    conn.execute(
        """
        INSERT INTO usmc_working (type, content, priority, tags, agent_id, is_active, created_at, updated_at)
        VALUES ('context', ?, ?, NULL, ?, ?, '2026-08-16', '2026-08-16')
        """,
        (content, priority, agent_id, is_active),
    )
    conn.commit()


# ── available() ──────────────────────────────────────────────────────────


def test_unavailable_when_no_db_file(tmp_path: Path):
    backend = UsmcBackend(tmp_path / "usmc_memory.db")
    assert backend.available() is False
    assert backend.search("anything") == []


def test_unavailable_when_file_exists_but_wrong_schema(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    backend = UsmcBackend(db_path)
    assert backend.available() is False
    assert backend.search("anything") == []


def test_unavailable_when_only_some_tables_exist(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE usmc_facts (id INTEGER PRIMARY KEY, category TEXT, key TEXT, "
        "value TEXT, confidence REAL, source TEXT, agent_id TEXT, created_at TEXT, updated_at TEXT)"
    )
    conn.commit()
    conn.close()

    backend = UsmcBackend(db_path)
    assert backend.available() is False


def test_available_when_full_schema_exists(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    _make_db(db_path)
    assert UsmcBackend(db_path).available() is True


def test_never_writes_to_a_missing_db(tmp_path: Path):
    """Kernanforderung des Tickets: nur lesen. Ein Backend, das (wie der
    reservierte USMC-Client) beim Instanziieren die DB anlegen wuerde, wuerde
    diesen Test durchfallen lassen -- die Datei darf nach available()/
    search() gegen einen fehlenden Pfad weiterhin nicht existieren."""
    db_path = tmp_path / "nested" / "usmc_memory.db"
    backend = UsmcBackend(db_path)
    backend.available()
    backend.search("irgendetwas")
    assert not db_path.exists()
    assert not db_path.parent.exists()


# ── search(): Grundverhalten je Tabelle ─────────────────────────────────


def test_search_finds_lesson_by_term(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_lesson(
        conn,
        lesson_id=1,
        title="robocopy /E statt /MIR",
        problem="/MIR loescht im Ziel alles was in der Quelle fehlt.",
        solution="robocopy mit /E statt /MIR verwenden, nichts wird geloescht.",
        severity="critical",
    )
    conn.close()

    hits = UsmcBackend(db_path).search("robocopy MIR loeschen", limit=3)
    assert len(hits) == 1
    assert hits[0].source == "usmc:lesson:1"
    assert hits[0].meta["type"] == "lesson"
    assert hits[0].meta["severity"] == "critical"
    assert 0 < hits[0].rank <= 1.0


def test_search_excludes_inactive_lessons(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_lesson(
        conn,
        lesson_id=2,
        title="Veraltete Lesson ueber robocopy",
        problem="robocopy Problem, laengst durch neuere Lesson ersetzt.",
        solution="siehe Nachfolge-Lesson.",
        is_active=0,
    )
    conn.close()

    assert UsmcBackend(db_path).search("robocopy") == []


def test_search_finds_fact_by_term(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_fact(
        conn,
        category="project",
        key="emblem-regel",
        value="Jeder MCP-Server zeigt in README sein eigenes Wappen als Header.",
        confidence=0.99,
    )
    conn.close()

    hits = UsmcBackend(db_path).search("Wappen Header MCP", limit=3)
    assert len(hits) == 1
    assert hits[0].source == "usmc:fact:project/emblem-regel"
    assert hits[0].meta["type"] == "fact"


def test_search_finds_working_entry_by_term(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_working(
        conn,
        content="RESUME: naechster Schritt ist der USMC-Backend-Test fuer memoryhooker.",
        priority=10,
    )
    conn.close()

    hits = UsmcBackend(db_path).search("USMC Backend Test memoryhooker", limit=3)
    assert len(hits) == 1
    assert hits[0].source.startswith("usmc:working:")
    assert hits[0].meta["type"] == "working"


def test_search_excludes_inactive_working(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_working(conn, content="Erledigter RESUME-Punkt zum USMC-Backend.", is_active=0)
    conn.close()

    assert UsmcBackend(db_path).search("USMC Backend RESUME") == []


def test_search_returns_nothing_for_stopword_only_query(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_fact(conn, category="user", key="x", value="irrelevanter Inhalt")
    conn.close()

    assert UsmcBackend(db_path).search("und oder die das") == []


def test_search_on_corrupt_file_returns_empty_not_raises(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    db_path.write_bytes(b"not a sqlite file")

    backend = UsmcBackend(db_path)
    assert backend.available() is False
    assert backend.search("irgendetwas") == []


def test_search_merges_and_ranks_across_tables(tmp_path: Path):
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_lesson(
        conn,
        lesson_id=3,
        title="Deploy nach OneDrive robocopy Vorsicht",
        problem="robocopy Deploy nach OneDrive kann Daten zerstoeren ohne Vorsicht.",
        solution="robocopy Deploy Schritte mit Vorsicht und /E statt /MIR ausfuehren.",
        severity="critical",
    )
    _insert_working(conn, content="robocopy Deploy laeuft noch, Vorsicht mit dem Ziel.", priority=2)
    conn.close()

    hits = UsmcBackend(db_path).search("robocopy Deploy Vorsicht", limit=5)
    assert len(hits) == 2
    # Ranking stabil absteigend
    assert hits[0].rank >= hits[1].rank
    # Die kuratierte, kritische Lesson soll vor der Working-Memory-Notiz stehen
    assert hits[0].source == "usmc:lesson:3"


# ── Kalibrierung gegen den realen Ticket-Fall (Lesson #44) ────────────────


def test_rank_for_realistic_prompt_clears_default_min_rank(tmp_path: Path):
    """Reproduziert Lesson #44 aus der realen USMC-Live-DB (2026-08-16) und
    prueft mit einer realistischen Nutzerfrage, ob der Rang die Default-
    Schwelle ``min_rank = 0.5`` aus modes.ModeConfig ueberhaupt erreicht.
    Ohne diesen Test waere ein plausibel-aussehendes, aber zu strenges
    Rang-Mass unentdeckt geblieben -- genau die Art Fehler, die das Ticket
    ("Lessons erreichen keine Sitzung") ausloeste."""
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_lesson(
        conn,
        lesson_id=44,
        title=_LESSON_44_TITLE,
        problem=_LESSON_44_PROBLEM,
        solution=_LESSON_44_SOLUTION,
        severity="high",
    )
    conn.close()

    hits = UsmcBackend(db_path).search(
        "wieso bekommt eine neue Sitzung die USMC Lessons nicht angezeigt?", limit=3
    )
    assert hits
    assert hits[0].source == "usmc:lesson:44"
    assert hits[0].rank >= 0.5


# ── Zustellnachweis: modes.evaluate_prompt injiziert die Lesson wirklich ──


def test_evaluate_prompt_delivers_fresh_usmc_lesson_into_session(tmp_path: Path):
    """End-to-End-Nachweis fuer den eigentlichen Ticket-Zweck: eine frische
    USMC-Lesson erreicht ueber den bestehenden remember+search-Pfad
    (modes.evaluate_prompt, exakt der Pfad den cli._cmd_hook_run fuer
    UserPromptSubmit nutzt) tatsaechlich eine Injektion in eine neue
    Sitzung -- nicht nur backend.search() isoliert."""
    db_path = tmp_path / "usmc_memory.db"
    conn = _make_db(db_path)
    _insert_lesson(
        conn,
        lesson_id=44,
        title=_LESSON_44_TITLE,
        problem=_LESSON_44_PROBLEM,
        solution=_LESSON_44_SOLUTION,
        severity="high",
    )
    conn.close()

    config = Config(backend=BackendConfig(kind="usmc", path=str(db_path)))
    config.mode.active = "remember+search"  # der Modus, der backend.search() tatsaechlich befragt
    backend = UsmcBackend(db_path)
    state = SessionState()

    message = evaluate_prompt(
        "wieso bekommt eine neue Sitzung die USMC Lessons nicht angezeigt?",
        config,
        backend,
        state,
    )

    assert message is not None
    assert "Zustellkette" in message
    assert state.injections_count == 1
