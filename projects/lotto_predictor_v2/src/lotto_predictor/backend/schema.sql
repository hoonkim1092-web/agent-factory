-- 로또 6/45 백엔드 SQLite 스키마.
-- 모든 테이블은 IF NOT EXISTS 로 정의해 ensure_schema() 멱등성을 보장한다.
-- 상위 계층(Frontend Dev 수집기/캐시/통계)은 이 스키마에만 의존한다.

CREATE TABLE IF NOT EXISTS lotto_draw (
    drw_no INTEGER PRIMARY KEY,
    drw_date TEXT NOT NULL,
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    n6 INTEGER NOT NULL,
    bonus_no INTEGER NOT NULL,
    tot_sell_amnt INTEGER,
    first_win_amnt INTEGER
);

CREATE TABLE IF NOT EXISTS fetch_checkpoint (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_fetched_drw_no INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    source_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS number_frequency (
    number INTEGER PRIMARY KEY,
    count INTEGER NOT NULL,
    last_seen_drw_no INTEGER NOT NULL,
    recent_50_count INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lotto_draw_date ON lotto_draw (drw_date);
