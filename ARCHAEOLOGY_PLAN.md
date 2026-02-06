# ARCHAEOLOGY_PLAN.md (発掘計画書)

## 1. ドメイン特定 (Domain Identification)

プロジェクト `RetroCoreTracer` は、ディレクトリ構造とファイル名から、以下の主要なドメイン（コンポーネント）から構成される「CPUエミュレーションフレームワーク」であると推定されます。

- **`transport`**: システムバス
- **`core`**: 抽象CPUコア
- **`arch/z80`**: Z80アーキテクチャ固有実装
- **`debugger`**: デバッガ
- **`loader`**: コードローダー
- **`ui`**: ユーザーインターフェース

## 2. マニフェスト配置マップ (Manifest Placement Map)

`DESIGN_PHILOSOPHY.md`で定義された「フラクタル構成」に基づき、以下の階層構造で`ARCHITECTURE_MANIFEST.md`を配置する計画を提案します。

```
/mnt/c/Users/shiro/Project/GitHub/RetroCoreTracer/
├── ARCHITECTURE_MANIFEST.md  (ルート)
└── src/
    └── retro_core_tracer/
        ├── transport/
        │   └── ARCHITECTURE_MANIFEST.md
        ├── core/
        │   └── ARCHITECTURE_MANIFEST.md
        ├── arch/
        │   └── z80/
        │       └── ARCHITECTURE_MANIFEST.md
        ├── debugger/
        │   └── ARCHITECTURE_MANIFEST.md
        ├── loader/
        │   └── ARCHITECTURE_MANIFEST.md
        └── ui/
            └── ARCHITECTURE_MANIFEST.md
```

## 3. 各階層の推定責務 (Estimated Responsibilities)

各マニフェストが担うべき責務の概要は、以下の通りと推定します。

- **ルート (`./ARCHITECTURE_MANIFEST.md`):**
  - プロジェクト全体の核となる原則（教育的透明性、UIとの分離など）を定義する。
  - 各サブコンポーネントの責務概要を記述し、詳細な仕様はサブマニフェストへ委譲する。

- **`transport`:**
  - メモリアドレス空間を抽象化し、読み書きアクセスを管理する責務。

- **`core`:**
  - 抽象的なCPUの状態管理と、命令サイクルの実行制御に関する責務。

- **`arch/z80`:**
  - Z80プロセッサ固有の命令セット、レジスタ構造、状態遷移の定義に関する責務。

- **`debugger`:**
  - 実行制御（ステップ実行、ブレークポイント）と、コアの状態観測に関する責務。

- **`loader`:**
  - 実行可能ファイル（HEX形式など）を解析し、シミュレータのメモリ空間にロードする責務。

- **`ui`:**
  - コアから受け取った`Snapshot`情報を可視化し、ユーザーとのインタラクションを提供する責務。

---

この計画をご承認いただけましたら、各ディレクトリの詳細なコード解析に進み、それぞれの`ARCHITECTURE_MANIFEST.md`を生成します。
