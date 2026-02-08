# ARCHITECTURE MANIFEST - Retro Core Tracer (Z80 Architecture Layer)

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose): なぜこの憲章が存在するのか

このドキュメントは、プロジェクト「Retro Core Tracer」の特定モジュール「Z80 Architecture Layer」の「北極星」です。開発者とAIが共有する高レベルな目標と、決して譲れない技術的・哲学的制約を定義します。その目的は、場当たり的な実装を防ぎ、モジュールが長期にわたって技術的負債を抱えることなく、クリーンなアーキテクチャを維持し続けることにあります。

これにより、AIは単なるコード生成ツールを超え、アーキテクチャ全体と一貫した、より洞察に富んだ提案が可能な、真の協調開発パートナーとして機能します。

### 2. 憲章の書き方 (Guidelines)

*   **原則1: 具体的に記述する。**
    *   悪い例: 「高速であるべき」
    *   良い例: 「Z80の1命令あたりの実行オーバーヘッドは、ネイティブ実行時間の500%未満に抑える」のように、検証可能な目標を設定します。

*   **原則2: 「なぜ」に焦点を当てる。**
    *   ルールだけではなく、その背景にあるトレードオフの判断を明記します。これが憲章の形骸化を防ぎ、将来の変更を助けます。
    *   例: 「我々は、UIの応答性よりもエミュレーションの正確性を優先する。なぜなら、このプロジェクトの第一目的は教育的な透明性の確保だからだ。」

*   **原則3: 「禁止」ではなく「判断の背景」を記述する。**
    *   「禁止事項」や「守るべきルール」といった思考停止を招く言葉を避け、「我々はこういう判断をした」といった形で、判断に至った文脈や背景そのものを記述します。
    *   例: 「現時点では、コアロジックとUIの結合を避けるため、両者はSnapshotオブジェクトを通してのみ通信する、という判断をした。」

### 3. リスクと対策 (Risks and Mitigations)

*   **リスク:** ドキュメントが陳腐化し、現実のコードと乖離する。
    *   **対策:** アーキテクチャに影響を与えるコード変更（例: 新コンポーネントの追加、既存APIの責務変更）は、必ずこのマニフェストの更新とセットでレビューします。これは、`DESIGN_PHILOSOPHY.md`で定義された、AIと人間の双方が遵守すべき厳格なプロトコルです。

*   **リスク:** 全体原則と、特定のCPUアーキテクチャ（局所的な要求）が衝突する。
    *   **対策:** 原則としてこの憲章を優先します。ただし、局所的なコード内コメントで明確な理由（例: 「6809の特殊なアドレッシングモードのため、標準バスアクセスを逸脱」）が示されている場合に限り、戦術的な逸脱を許容します。

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)

*このセクションは、モジュールの不変的なルールを「なぜ」の理由付けと共に定義します。*

<!--
- **原則: Z80エミュレーションは、公式ドキュメント（Zilog Z80 CPU User's Manual）の動作に厳密に準拠する。**
  - **理由:** エミュレーションの正確性を最優先するため。特にフラグの挙動、レジスタ操作、メモリ/I/Oアクセスのタイミングとデータは厳密に再現されるべきである。

- **原則: 命令のデコードと実行ロジックは、Instruction Layerの責務であり、Z80Cpuクラスはそれらをオーケストレーションする。**
  - **理由:** Core Layerで定義された抽象CPUの原則に準拠し、Z80固有の複雑な命令セットを管理しやすくするため。
-->

### 2. 主要なアーキテクチャ決定の記録 (Key Architectural Decisions)

*このセクションは、「なぜこの構造になったのか」を後から追えるように、重要な設計判断をログとして残します。*

<!--
- **Date:** 2026-02-05
- **Core Principle:** Z80エミュレーションは、公式ドキュメントの動作に厳密に準拠する。
- **Decision:** Z80のレジスタセットとフラグレジスタの特定のビット位置を正確にモデル化する`Z80State`クラスを導入する。
- **Rationale:** Z80の複雑なフラグ操作（特に演算結果に基づくHフラグやNフラグの更新）を正確にシミュレートするためには、これらのレジスタの状態をビットレベルで厳密に管理する必要がある。
- **Alternatives:**
  - 汎用的な`CpuState`をそのまま使用し、Z80固有のレジスタをフィールドとして追加する。→ フラグ操作のロジックが`Z80Cpu`クラス内に散在し、可読性と保守性が低下する。
- **Consequences:** `Z80State`が`CpuState`を継承し、Z80固有のレジスタとフラグ管理ロジックを持つことになる。
-->

### 3. モジュール構成 (Module Structure)

*このセクションは、モジュール内部の構造を定義します。*

- **`cpu.py`**: `AbstractCpu` を継承した Z80 CPU のメイン実装。
- **`state.py`**: Z80 固有のレジスタとフラグの状態定義。
- **`instructions/`**: Z80命令セットの実装パッケージ。
    - **`__init__.py`**: 外部（`cpu.py`）に対するファサード。
    - **`base.py`**: レジスタアクセス等の共通ヘルパー関数。
    - **`alu.py`**: 算術論理演算命令の実装。
    - **`load.py`**: 転送・ブロック転送命令の実装。
    - **`control.py`**: 分岐・制御・ビット操作命令の実装。
    - **`maps.py`**: デコード・実行関数のマッピング定義。
- **`alu.py`**: フラグ計算の低レベルロジック（`instructions/alu.py`とは別、こちらは純粋な計算のみ）。
- **`disassembler.py`**: メモリ上のバイナリをニーモニックに変換するロジック。

### 4. コンポーネント設計仕様 (Component Design Specifications)

#### 4.1. Z80CpuState (データクラス)
- **責務 (Responsibility):** `CpuState`を拡張し、Z80 CPU固有の全てのレジスタ（主レジスタ、代替レジスタ、インデックスレジスタ、特殊用途レジスタ）とフラグビットの状態を保持する。
- **主要なデータ構造 (Key Data Structures):**
    - **フラグビットマスク:** `S_FLAG` (Sign), `Z_FLAG` (Zero), `H_FLAG` (Half Carry), `PV_FLAG` (Parity/Overflow), `N_FLAG` (Add/Subtract), `C_FLAG` (Carry) の各ビット位置を定義する定数。
    - **主レジスタ:** `a`, `b`, `c`, `d`, `e`, `h`, `l` (8ビットレジスタ), `f` (フラグレジスタ)。
    - **代替レジスタ:** `a_`, `b_`, `c_`, `d_`, `e_`, `h_`, `l_`, `f_`。
    - **インデックスレジスタ:** `ix`, `iy` (16ビットレジスタ)。
    - **特殊用途レジスタ:** `i` (割り込みベクタレジスタ), `r` (リフレッシュレジスタ)。
    - **CPU状態フラグ:** `halted` (CPUがHALT命令により停止中かどうかを示すブール値)。
    - **割り込み制御:** `iff1`, `iff2` (割り込み許可フラグ), `im` (割り込みモード: 0, 1, 2)。
- **提供するAPI (Public API) - プロパティ:**
    - **フラグアクセサ:** `flag_s`, `flag_z`, `flag_h`, `flag_pv`, `flag_n`, `flag_c` (それぞれ`bool`型のゲッター/セッターを提供し、`f`レジスタの対応するビットを操作する)。
    - **16ビットレジスタペアアクセサ:** `af`, `bc`, `de`, `hl` (それぞれ`int`型のゲッター/セッターを提供し、対応する8ビットレジスタペアを操作する)。
- **状態とライフサイクル (State and Lifecycle):**
    - `Z80CpuState`のインスタンスは、Z80 CPUの可変状態を保持する。
    - `CpuState`からの継承により、`pc`と`sp`も管理される。

#### 4.2. Z80InstructionSet (パッケージ、`instructions/`に実装)
- **責務 (Responsibility):** Z80命令セットのデコードロジックと実行ロジックを定義し提供する。内部は機能別にモジュール分割されているが、`__init__.py`を通じて統一されたAPIを提供する。
- **提供するAPI (Public API) - `instructions/__init__.py`:**
    - `decode_opcode(opcode: int, bus: Bus, pc: int) -> Operation`:
        - **責務:** 与えられたオペコードをZ80の命令としてデコードし、`Operation`オブジェクトを返す。マルチバイト命令の場合、`bus`を介してオペランドバイトをフェッチする。
    - `execute_instruction(operation: Operation, state: Z80CpuState, bus: Bus) -> None`:
        - **責務:** デコードされたZ80命令を実行し、`Z80CpuState`を更新し、必要に応じて`Bus`を介したメモリ/I/O操作を行う。
- **モジュール構造と役割:**
    - `alu.py`: 算術論理演算を担当。フラグ更新ロジックもここに集約される。
    - `load.py`: 8/16ビット転送、スタック操作、ブロック転送を担当。
    - `control.py`: 分岐、I/O、割り込み制御、ビット操作を担当。
    - `maps.py`: `DECODE_MAP` と `EXECUTE_MAP` を構築し、オペコードと実装関数の紐付けを管理する。
- **重要なアルゴリズム (Key Algorithms):**
    - **命令デコード:** オペコードをキーとして`DECODE_MAP`から対応するデコード関数をルックアップし、実行する。マルチバイトオペランドは`bus`から直接読み込む。
    - **命令実行:** オペコードをキーとして`EXECUTE_MAP`から対応する実行関数をルックアップし、`Z80CpuState`と`Bus`を引数として実行する。
    - **レジスタ交換 (Exchange):** `EX AF,AF'`, `EXX`, `EX DE,HL` などの命令により、メインレジスタと代替レジスタ、またはレジスタペア間で値を交換する。
    - **インデックス修飾アドレッシング:** `IX`, `IY` プレフィックスを検出し、続く命令の `HL` 指定を `IX+d` または `IY+d` に動的に置換して実行する。
    - **割り込み制御:** `EI`, `DI` 命令による `iff1`, `iff2` の操作、および `IM` 命令による割り込みモードの切り替えを管理する。
- **状態とライフサイクル (State and Lifecycle):** このモジュールはステートレスな関数群とマップで構成されており、`Z80CpuState`と`Bus`インスタンスを介して間接的にCPUの状態とシステムバスに作用する。

#### 4.3. Z80Cpu (具象CPUエミュレータ)
- **責務 (Responsibility):** `AbstractCpu`インターフェースをZ80プロセッサ向けに完全に実装し、Z80固有の`Z80CpuState`と`Z80InstructionSet`を利用して、フェッチ、デコード、実行の命令サイクルをオーケストレートする。
- **追加責務:** 命令ごとの正確なマシンサイクル（Mサイクル/Tステート）を計算し、`Snapshot.metadata` に反映させる。条件分岐命令における分岐成立/不成立によるサイクル数の変化も正確にエミュレートする。
- **継承元:** `AbstractCpu`。
- **提供するAPI (Public API) - `AbstractCpu`からのオーバーライド:**
    - `_create_initial_state(self) -> Z80CpuState`:
        - **責務:** Z80 CPUの初期状態を表す`Z80CpuState`のインスタンスを生成して返す。
        - **設計上の決定:** Z80の一般的なリセット時の状態を反映したデフォルト値を設定。
    - `_fetch(self) -> int`:
        - **責務:** 現在の`Z80CpuState.pc`から、システムバス(`self._bus`)を介してオペコードバイトを読み出す。
    - `_decode(self, opcode: int) -> Operation`:
        - **責務:** `instructions`モジュールの`decode_opcode`関数を呼び出し、与えられたオペコードをデコードする。`bus`と`pc`情報も渡すことで、マルチバイトオペランドの処理を可能にする。
    - `_execute(self, operation: Operation) -> None`:
        - **責務:** `instructions`モジュールの`execute_instruction`関数を呼び出し、デコードされた命令を実行する。`Z80CpuState`と`Bus`のインスタンスを渡すことで、命令がCPUの状態を変更したり、バスと相互作用したりできるようにする。
    - `step(self) -> Snapshot`:
        - **責務:** Z80 CPUを1命令サイクル分実行し、その結果を完全な`Snapshot`オブジェクトとして返す。
        - **処理フロー:**
            1. 実行前の`pc`を保存する。
            2. `self._bus.get_and_clear_activity_log()`を呼び出し、前サイクルのバスアクティビティをクリアする。
            3. `_fetch()`によりオペコードを取得する。
            4. `_decode()`によりオペコードをデコードし、`Operation`オブジェクトを得る。
            5. `operation.length`に基づいて`Z80CpuState.pc`をインクリメントし、次の命令の先頭を指すようにする。
            6. `_execute()`により命令を実行する。
            7. `self._bus.get_and_clear_activity_log()`を呼び出し、このサイクル中に発生した全てのバスアクティビティを取得する。
            8. 実行後の`Z80CpuState`、`Operation`、`Metadata`（`cycle_count`と`symbol_info`を含む）、および取得した`bus_activity`を含む`Snapshot`オブジェクトを構築し、返す。
    - `get_register_map(self) -> Dict[str, int]`:
        - **責務:** `Z80CpuState`の各レジスタ（AF, BC, DE, HL, IX, IY, SP, PC, I, R, AF', BC', DE', HL'）の現在の値を辞書形式で返す。
    - `get_register_layout(self) -> List[RegisterLayoutInfo]`:
        - **責務:** Z80のレジスタ構成（8bit/16bit、メイン/代替/インデックス/特殊グループ）を定義する静的なレイアウト情報を返す。
    - `get_flag_state(self) -> Dict[str, bool]`:
        - **責務:** フラグレジスタ（F）から S, Z, H, PV, N, C の各フラグの状態を抽出し、辞書形式で返す。
    - `disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]`:
        - **責務:** 内部の`disassembler`モジュールに処理を委譲し、指定範囲の逆アセンブル結果を返す。
- **主要なデータ構造 (Key Data Structures):**
    - `self._state: Z80CpuState`: `AbstractCpu`から継承されるCPUの状態。
- **重要なアルゴリズム (Key Algorithms):**
    - **命令サイクルオーケストレーション:** `step`メソッド内でフェッチ、デコード、PCインクリメント、実行、バスアクティビティキャプチャ、スナップショット生成の厳密な順序を管理する。
- **状態とライフサイクル (State and Lifecycle):** `Z80Cpu`インスタンスは、Z80エミュレーションの実行時コンテキスト全体を管理し、`AbstractCpu`のライフサイクルに従う。

#### 4.4. Z80Alu (ALUおよびフラグ計算、`alu.py`に実装)
- **責務 (Responsibility):** Z80の算術・論理演算の結果に基づいて、フラグレジスタ（S, Z, H, P/V, N, C）を正確に計算・更新するロジックを集約する。
- **提供するAPI (Public API):**
    - `update_flags_add8(state: Z80CpuState, val1: int, val2: int, result: int) -> None`: 8ビット加算のフラグ更新。
    - `update_flags_sub8(state: Z80CpuState, val1: int, val2: int, result: int) -> None`: 8ビット減算のフラグ更新。
    - `update_flags_logic8(state: Z80CpuState, result: int) -> None`: 8ビット論理演算のフラグ更新。
    - `update_flags_add16(state: Z80CpuState, val1: int, val2: int, result: int) -> None`: 16ビット加算のフラグ更新。

#### 4.5. Z80Disassembler (逆アセンブラ、`disassembler.py`に実装)
- **責務 (Responsibility):** 指定されたメモリ範囲のバイナリデータを解析し、Z80アセンブリ言語のニーモニック形式に変換する。
- **提供するAPI (Public API):**
    - `disassemble(bus: Bus, start_addr: int, length: int) -> List[str]`: メモリ上のデータを読み取り、ニーモニックのリストを返す。
