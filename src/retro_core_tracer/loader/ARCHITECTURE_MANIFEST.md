# src/retro_core_tracer/loader/ARCHITECTURE_MANIFEST.md

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose)
Loader Layerは、外部ファイル（HEXバイナリやアセンブリソース）を読み込み、システムバス経由でメモリに配置する責務を負います。

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)
- **原則: ローダーは、システムバスを介してのみメモリにアクセスする。**
- **原則: アセンブリローダーは、指定されたターゲットアーキテクチャに基づいてパースを行う。**
  - **理由:** ニーモニックやアドレッシングモードの構文はCPUアーキテクチャごとに異なるため。

### 2. コンポーネント設計仕様 (Component Design Specifications)

#### 4.3. AssemblyLoader (クラス)
- **責務:** 簡易的なアセンブリソースコードファイルを解析し、シンボル情報を抽出すると共に、バイナリを生成してロードする。
- **提供するAPI:**
    - `load_assembly(self, file_path: str, bus: Bus, architecture: str = "Z80") -> SymbolMap`:
        - **引数:**
            - `architecture`: ターゲットCPUアーキテクチャ名（"Z80", "MC6800"等）。デフォルトは"Z80"。
        - **責務:** 指定されたアーキテクチャの構文規則に従ってアセンブルを行い、ロードする。
