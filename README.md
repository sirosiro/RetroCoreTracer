# Retro Core Tracer

**「計算の本質を可視化する」**

Retro Core Tracerは、CPUエミュレーションの内部動作（レジスタ、バス、フラグ、スタック）をリアルタイムかつ詳細に可視化するための教育的ツールです。

## ✨ 特徴

*   **マルチアーキテクチャ対応基盤:** UI層が特定のCPU実装から完全に分離されており、メタデータ駆動で動的に表示します。現在は **Z80** および **MC6800** に対応しています。
*   **教育的透明性 (Transparency):** レジスタの変化、フラグの更新、スタックの積み上げなど、CPUの内部状態を隠さず全て表示します。
*   **Pure Bus Logging (純粋なバス監視):** UI描画のためのメモリ読み出し（Peek）と、CPUによる実際の実行アクセス（Read/Write）を厳密に区別します。
*   **Visualized Block Transfer:** `LDIR` などのブロック転送命令において、1バイト転送ごとにステップ実行が可能。
*   **Snapshotベースの可視化:** 1命令ごとのCPU状態を不変（Immutable）なスナップショットとして記録。
*   **モダンで柔軟なUI:** PySide6 (Qt) を採用したドッキングウィンドウシステム。
*   **直感的なデバッグ操作:**
    *   **Breakpoints:** PC一致、メモリ読み書き、レジスタ変化など。
    *   **Code View:** 実行予定の次行が常に見えるスマートスクロール機能。
    *   **Multiple Loaders:** Intel HEX, Motorola S-Record, 簡易アセンブラをサポート。

### 対応するアーキテクチャと命令セット

#### **Z80**
![Z80 Screenshot](docs/assets/Z80-window-snapshot.png)
*   転送、演算、分岐、ビット操作、ブロック転送、I/O、割り込み制御など、主要な命令セットを網羅。

#### **MC6800**
![MC6800 Screenshot](docs/assets/mc6800-window-snapshot.png)
*   **転送命令:** `LDAA`, `LDAB`, `LDX`, `STAA`, `STAB`, `STS`, `LDS` (Direct/Extended/Immediate対応)
*   **演算命令:** `ADDA`, `SUBA`, `ANDA`, `ORAA`, `CMPA` など
*   **分岐・制御:** `BRA`, `BNE`, `BEQ`, `JMP`, `JSR`, `RTS`
*   *(順次実装拡充中)*

## 🚀 インストール & 使い方

### 前提条件
*   Python 3.10 以上

### 手順
1.  `pip install -r requirements.txt`
2.  `export PYTHONPATH=$(pwd)/src`
3.  `python3 -m retro_core_tracer.ui.app`

### 基本操作
1.  **Load Config:** `File` -> `Load Config...` (例: `examples/mc6800_system_config.yaml`)
2.  **Load Program:** HEXファイルやアセンブリソースをロード。
3.  **Run/Step:** ツールバーで実行制御。

## 🛠️ 開発について
このプロジェクトは **「マニフェスト駆動開発」** を採用しています。変更前に必ず `ARCHITECTURE_MANIFEST.md` を更新し、設計意図（Intent）を明確にしてください。

### ディレクトリ構造
*   `src/retro_core_tracer/`
    *   `transport/`: バスとメモリデバイス（RAM/ROM）。
    *   `core/`: 抽象CPUコア。
    *   `arch/`: Z80/MC6800固有実装。
    *   `debugger/`: デバッガロジック。
    *   `loader/`: 各種バイナリローダーとFactory。
    *   `ui/`: PySide6によるUI。

---
## Attribution
This project was created with the assistance of [`CIP`](https://github.com/sirosiro/cip) (Core-Intent Prompting Framework).
