# src/retro_core_tracer/transport/ARCHITECTURE_MANIFEST.md

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose): なぜこの憲章が存在するのか

このドキュメントは、プロジェクト「Retro Core Tracer」の特定モジュール「Transport Layer」の「北極星」です。開発者とAIが共有する高レベルな目標と、決して譲れない技術的・哲学的制約を定義します。

### 2. 憲章の書き方 (Guidelines)
*   **原則1: 具体的に記述する。**
*   **原則2: 「なぜ」に焦点を当てる。**
*   **原則3: 「禁止」ではなく「判断の背景」を記述する。**

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)

- **原則: バスアクセスは、アドレスとデータペイロードのみに限定される。**
  - **理由:** CPUコアからバスへのインターフェースをシンプルに保ち、下位レイヤー（デバイスドライバ）の複雑性を上位レイヤーに伝播させないため。
  - **例外:** システム初期化（ロード）時のみ、物理的な書き込み制限（ROMなど）をバイパスする特権的な `load` メソッドの使用を許可する。

- **原則: メモリマップドI/Oを含む全てのアクセスは、単一のBusインターフェースを介して行われる。**
  - **理由:** CPUコア側がROM、RAM、I/Oを意識することなく、アドレス指定だけでアクセスを完結できるようにし、CPU実装の抽象度を高めるため。
  - **補足:** 独立したI/O空間（Z80のPort I/Oなど）を持つアーキテクチャのために、`read_io`/`write_io` インターフェースも提供するが、これらもBusクラスが一元管理する。

### 2. コンポーネント設計仕様 (Component Design Specifications)

#### 4.1. BusAccessType (Enum)
- **責務:** バス上で発生する操作の種類（読み込みまたは書き込み）を明確に定義する。
    - `READ`, `WRITE`, `IO_READ`, `IO_WRITE`

#### 4.2. BusAccess (データクラス)
- **責務:** バス上で行われた個々のアクセス操作を不変な形式で記録する。
    - `address: int`, `data: int`, `access_type: BusAccessType`
    - `previous_data: Optional[int]`: `WRITE` 操作の場合、上書きされる前のメモリ値を記録する。タイムトラベルデバッグ（Undo）用。読み込み操作や、以前の値が取得できない場合（I/O書き込み等）は `None`。

#### 4.3. Device (抽象基底クラス)
- **責務:** バスに接続される全てのメモリマップドデバイス、またはI/Oデバイスが実装すべき標準インターフェースを定義する。
- **提供するAPI:**
    - `read(self, address: int) -> int`
    - `write(self, address: int, data: int) -> None`

#### 4.4. RAM (具象デバイス)
- **責務:** 読み書き可能なメモリ機能を提供する。
- **API:**
    - `read`: データを返す。
    - `write`: 内部バッファを更新する。

#### 4.5. ROM (具象デバイス)
- **責務:** 読み込み専用メモリ機能を提供する。
- **API:**
    - `read`: 初期化データを返す。
    - `write`: 何もしない、またはログ警告を出力する（例外は投げないことで実機の挙動に近づける）。
    - `load_data(self, data: bytes, offset: int) -> None`: 初期化時にデータをロードするためのバックドアメソッド。

#### 4.6. Bus (主要コンポーネント)
- **責務:** アドレス空間およびI/Oポート空間を一元管理し、アクセスを適切なデバイスへディスパッチする。全てのアクセスをログに記録する。
- **提供するAPI:**
    - `register_device(start: int, end: int, device: Device)`: メモリ空間へのデバイス登録。
    - `register_io_device(start: int, end: int, device: Device)`: I/O空間へのデバイス登録。
    - `read(address: int) -> int`: メモリ読み込み。
    - `write(address: int, data: int) -> None`: メモリ書き込み（ROMの場合は無視）。書き込み前の値を読み出し、ログの `previous_data` に記録する責務を負う。
    - `load(address: int, data: int) -> None`: 初期化データロード（ROMへも書き込み可）。
    - `read_io(port: int) -> int`: I/Oポート読み込み。
    - `write_io(port: int, data: int) -> None`: I/Oポート書き込み。
    - `peek(address: int) -> int`: ログを残さないメモリ読み込み（デバッガ用）。
    - `get_and_clear_activity_log()`: バスの活動ログ取得とクリア。