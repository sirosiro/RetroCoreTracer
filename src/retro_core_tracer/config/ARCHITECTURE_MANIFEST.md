# ARCHITECTURE MANIFEST - Retro Core Tracer (Configuration Layer)

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose)

このドキュメントは、「Configuration Layer」の設計原則を定義します。このレイヤーの目的は、ハードコードされたシステム構成（Bus, RAM, CPUの組み合わせ）を排除し、外部の設定ファイルに基づいて動的かつ柔軟にエミュレーション環境を構築することです。

### 2. リスクと対策

*   **リスク:** 設定ファイルの記述が複雑になりすぎる。
    *   **対策:** 必須項目を最小限にし、妥当なデフォルト値（例：指定がなければ全域RAM）を提供する。
*   **リスク:** 将来的なデバイス（MMIO、特殊なバンク切り替えなど）に対応できない。
    *   **対策:** デバイス定義をプラグイン可能な構造にし、設定ファイルでは「デバイスタイプ」と「パラメータ」を抽象的に記述する形式をとる。

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)

- **原則: システム構成は宣言的に定義される。**
  - **理由:** コードを変更することなく、異なるハードウェア構成（メモリマップ、I/O配置）をシミュレートするため。

- **原則: 構成データは、特定のCPUアーキテクチャに依存しない汎用フォーマットを持つ。**
  - **理由:** Z80（独立I/O空間）と6800（メモリマップドI/O）の両方を、統一されたスキーマで表現するため。

### 2. モジュール構成 (Module Structure)

- **`schema.py`**: 設定ファイルのバリデーションスキーマとデータモデル（Pydantic等を利用想定、あるいは標準dataclass）。
- **`loader.py`**: YAML/JSONファイルを読み込み、内部データモデルに変換する。
- **`builder.py`**: データモデルに基づいて、実際の`Bus`、`Device`、`Cpu`インスタンスを生成・接続する（Dependency Injection的な役割）。

### 3. コンポーネント設計仕様 (Component Design Specifications)

#### 3.1. SystemConfig (データモデル)
- **責務:** システム全体の構成情報を保持する不変のデータ構造。
- **主要フィールド:**
    - `architecture: str`: CPUタイプ ("Z80" など)。
    - `memory_map: List[MemoryRegion]`: メモリ領域の定義リスト。
    - `initial_state: CpuInitialState`: CPUの初期レジスタ状態。
    - `io_map: List[IoRegion]`: I/O領域の定義リスト（将来拡張）。

#### 3.2. CpuInitialState (データモデル)
- **責務:** CPUのリセット直後のレジスタ状態（PC, SPなど）を定義する。
- **主要フィールド:**
    - `pc: int`: 初期プログラムカウンタ。
    - `sp: int`: 初期スタックポインタ。
    - `registers: dict`: その他、個別に設定したいレジスタ名と値のマップ。

#### 3.3. MemoryRegion (データモデル)
- **責務:** 単一のメモリ領域（範囲、種類、ラベル）を定義する。
- **主要フィールド:**
    - `start: int`: 開始アドレス。
    - `end: int`: 終了アドレス。
    - `type: str`: デバイスタイプ ("RAM", "ROM", "MMIO" など)。
    - `label: str`: UI表示用のラベル（例: "Video RAM"）。
    - `permissions: str`: アクセス権限 ("RW", "RO")。

#### 3.4. ConfigLoader
- **責務:** 設定ファイル（YAML形式）を読み込み、バリデーションを行って`SystemConfig`オブジェクトを返す。
- **API:**
    - `load_from_file(path: str) -> SystemConfig`

#### 3.5. SystemBuilder
- **責務:** `SystemConfig`を受け取り、組み立てられた`Bus`と`Cpu`のインスタンスを返す。
    - メモリマップ (`memory_map`) に基づいてデバイスを登録する。
    - I/Oマップ (`io_map`) に基づいてI/Oデバイスを登録する。
    - CPUの初期状態 (`initial_state`) を適用する。
- **API:**
    - `build_system(config: SystemConfig) -> Tuple[AbstractCpu, Bus]`
