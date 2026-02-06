# Retro Core Tracer

**「計算の本質を可視化する」**

Retro Core Tracerは、CPUエミュレーションの内部動作（レジスタ、バス、フラグ、スタック）をリアルタイムかつ詳細に可視化するための教育的ツールです。単に命令を実行するだけでなく、「ビットの羅列がどのように意味を持ち、回路を駆動するか」というプロセスを透明化することを目的としています。

![Retro Core Tracer Main Window](assets/Main-window-snapshot.png)

現在は **Z80** アーキテクチャに対応しています。

## ✨ 特徴

*   **教育的透明性 (Transparency):** レジスタの変化、フラグの更新、スタックの積み上げなど、CPUの内部状態を隠さず全て表示します。
*   **Snapshotベースの可視化:** 1命令ごとのCPU状態を不変（Immutable）なスナップショットとして記録。UIとコアロジックが完全に分離されています。
*   **モダンなUI:** PySide6 (Qt) を採用し、Windows/MacOS/Linuxで動作するクロスプラットフォームなデスクトップアプリケーション。
*   **詳細なインスペクタ:**
    *   **HEX View:** メモリ内容のリアルタイム表示とハイライト。
    *   **Register View:** 全レジスタ（裏レジスタ含む）の状態表示。
    *   **Flag View:** フラグレジスタの各ビットの状態を可視化。
    *   **Stack View:** スタックポインタ周辺のメモリを可視化。
    *   **Breakpoints:** PC一致、メモリ読み書き、レジスタ変化など、柔軟な条件でのブレークポイント設定。

## 🚀 インストール

### 前提条件
*   Python 3.10 以上

### 手順

1.  リポジトリをクローンします。
    ```bash
    git clone https://github.com/yourusername/RetroCoreTracer.git
    cd RetroCoreTracer
    ```

2.  仮想環境を作成し、有効化することをお勧めします。
    ```bash
    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate

    # Windows (PowerShell)
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

3.  依存パッケージをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

## 🎮 使い方

プロジェクトのルートディレクトリで以下のコマンドを実行し、アプリケーションを起動します。

```bash
# Mac/Linux
export PYTHONPATH=$(pwd)/src
python3 -m retro_core_tracer.ui.app

# Windows (PowerShell)
$env:PYTHONPATH="$(pwd)\src"
python -m retro_core_tracer.ui.app
```

### 基本操作
1.  **Load HEX:** `File` -> `Load HEX...` からIntel HEX形式のプログラムを読み込みます。
2.  **Run/Step:** ツールバーのボタンで実行制御を行います。
    *   `Step`: 1命令ずつ実行します。
    *   `Run`: 連続実行します。
    *   `Stop`: 実行を停止します。
3.  **Breakpoints:** `Breakpoints` タブで条件を追加し、特定の状態で実行を一時停止できます。

## 🛠️ 開発について

このプロジェクトは **「マニフェスト駆動開発」** を採用しています。
コードの変更を行う前に、対応する `ARCHITECTURE_MANIFEST.md`（各ディレクトリに配置）を更新し、設計意図（Intent）を明確にする規律を守っています。

### ディレクトリ構造
このプロジェクトはフラクタルなマニフェスト構造を採用しています。各ディレクトリの設計詳細は、それぞれの `ARCHITECTURE_MANIFEST.md` を参照してください。

*   `src/retro_core_tracer/`
    *   [`transport/`](src/retro_core_tracer/transport/ARCHITECTURE_MANIFEST.md): バスとメモリデバイス。
    *   [`core/`](src/retro_core_tracer/core/ARCHITECTURE_MANIFEST.md): 抽象CPUコアとSnapshot定義。
    *   [`arch/z80/`](src/retro_core_tracer/arch/z80/ARCHITECTURE_MANIFEST.md): Z80固有の実装。
    *   [`debugger/`](src/retro_core_tracer/debugger/ARCHITECTURE_MANIFEST.md): 実行制御とブレークポイント。
    *   [`loader/`](src/retro_core_tracer/loader/ARCHITECTURE_MANIFEST.md): HEXファイルローダー。
    *   [`ui/`](src/retro_core_tracer/ui/ARCHITECTURE_MANIFEST.md): PySide6によるユーザーインターフェース。

---

## Attribution

This project was created with the assistance of
[`CIP`](https://github.com/sirosiro/cip) (Core-Intent Prompting Framework),
a CC BY 4.0 licensed prompt framework for generative AI.
