# ARCHITECTURE MANIFEST - Retro Core Tracer (MC6800 Architecture Layer)

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose)
このドキュメントは、MC6800 CPUアーキテクチャ層の設計原則を定義します。エミュレーションの正確性と教育的透明性を両立させることを目的とします。

### 2. 憲章の書き方 (Guidelines)
*   **原則1: 具体的に記述する。**
*   **原則2: 「なぜ」に焦点を当てる。**
*   **原則3: 「禁止」ではなく「判断の背景」を記述する。**

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)

- **原則: MC6800エミュレーションは、公式データシートの動作に厳密に準拠する。**
  - **理由:** エミュレーションの信頼性を担保するため。特に条件コード（フラグ）の更新ロジックは、命令ごとの定義に忠実に実装する。

- **原則: ビッグエンディアンの処理は、CPU層で明示的に行う。**
  - **理由:** MC6800はビッグエンディアンである。Bus層は単一バイトを扱うため、16ビットアドレスやデータの結合・分割はCPUクラスの責務として明確に実装し、リトルエンディアンアーキテクチャ（Z80等）との混同を防ぐ。

- **原則: リセット動作はハードウェア仕様（リセットベクトル）を尊重する。**
  - **理由:** 実機では電源投入時に $FFFE-$FFFF からエントリアドレスを読み込む。この挙動を再現することで、ROMへのプログラム配置と起動プロセスを正しくシミュレートする。

### 2. 主要なアーキテクチャ決定の記録 (Key Architectural Decisions)

- **Date:** 2026-02-10
- **Decision:** MC6800専用の `Mc6800CpuState` と `Mc6800Cpu` クラスを導入する。
- **Rationale:** Z80とはレジスタ構成（A, B, X, PC, SP, CC）が根本的に異なるため、`AbstractCpu` を継承して独立したクラスとして実装するのが最もクリーンであると判断。

- **Date:** 2026-02-11
- **Decision:** リセットベクトル読み込み機能の導入 (`set_use_reset_vector`)。
- **Rationale:** ユーザーがPCを任意のアドレスに設定したい場合と、実機通りベクトルから読み込みたい場合の両方に対応するため。Configの `use_reset_vector` フラグと連動する。

### 3. モジュール構成 (Module Structure)

- **`cpu.py`**: `AbstractCpu` を継承したメイン実装。
- **`state.py`**: A, B, X, PC, SP, CC レジスタおよびフラグの状態定義。
- **`instructions/`**:
    - `maps.py`: 1バイトオペコードのマッピング。
    - `load.py`: 転送、スタック操作。
    - `alu.py`: 算術論理演算、フラグ更新。
    - `control.py`: 分岐、ジャンプ、制御命令。
- **`disassembler.py`**: MC6800固有の逆アセンブラ。

### 4. コンポーネント設計仕様 (Component Design Specifications)

#### 4.1. Mc6800CpuState
- **責務:** MC6800のレジスタ状態（A, B, X, PC, SP, CC）を保持する。
- **データ構造:**
    - `a, b`: 8ビットアキュムレータ。
    - `x`: 16ビットインデックスレジスタ。
    - `cc`: 8ビットコンディションコードレジスタ（H, I, N, Z, V, C）。
- **フラグ:**
    - H (Half-carry), I (Interrupt mask), N (Negative), Z (Zero), V (Overflow), C (Carry)。

#### 4.2. Mc6800Cpu
- **責務:** `AbstractCpu` のインターフェースを実装し、MC6800の命令サイクルをシミュレートする。
- **UI連携:**
    - `get_register_layout()` は以下のグループを返す：
        1. "Accumulators/Flags": A, B, CC
        2. "Index/Pointers": X, SP, PC
- **ビッグエンディアン対応:**
    - `_read_word(addr)`: `(bus.read(addr) << 8) | bus.read(addr+1)`
    - `_write_word(addr, val)`: `bus.write(addr, val >> 8); bus.write(addr+1, val & 0xFF)`
    - **`step` メソッド:** `AbstractCpu` のTemplate Methodを使用。デフォルトのPC更新（命令長分加算）に従う。
