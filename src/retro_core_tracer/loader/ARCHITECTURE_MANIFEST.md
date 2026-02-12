# src/retro_core_tracer/loader/ARCHITECTURE_MANIFEST.md

---
## Part 1: このマニフェストの取扱説明書 (Guide)

### 1. 目的 (Purpose)
Loader Layerは、外部ファイル（HEXバイナリやアセンブリソース）を読み込み、システムバス経由でメモリに配置する責務を負います。

---
## Part 2: マニフェスト本体 (Content)

### 1. 核となる原則 (Core Principles)
- **原則: ローダーは、システムバスを介してのみメモリにアクセスする。**
- **原則: ローダーは入力データに対して「非侵襲的」かつ「忠実」でなければならない。**
- **原則: 多様なバイナリフォーマットを抽象化し、一貫したロード体験を提供する。**
- **原則: アセンブリローダーは、アーキテクチャごとのアセンブラクラスに処理を委譲する。**
  - **理由:** 巨大な条件分岐を避け、新しいアーキテクチャの追加を容易にするため。
- **原則: UI層は具体的なローダークラスを知る必要はなく、Factoryを介して取得する。**

### 2. コンポーネント設計仕様 (Component Design Specifications)

#### 4.0. BaseLoader (抽象基底クラス)
- **責務:** 全てのローダーが実装すべき共通インターフェースを定義する。
    - `load(self, file_path: str, bus: Bus, **kwargs) -> Optional[SymbolMap]`

#### 4.1. IntelHexLoader / SRecordLoader
- **責務:** それぞれのバイナリ形式を解析し、バスにロードする。

#### 4.2. AssemblyLoader (ファサードクラス)
- **責務:** ファイルを読み込み、指定されたアーキテクチャに対応する `BaseAssembler` 実装を選択して処理を委譲する。

#### 4.3. BaseAssembler (抽象基底クラス)
- **責務:** アーキテクチャ固有のアセンブリ構文解析とバイナリ生成のインターフェース。
    - `assemble(lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]`

#### 4.4. Z80Assembler / Mc6800Assembler (具象クラス)
- **責務:** 各アーキテクチャのニーモニックと疑似命令を解析する。

#### 4.5. LoaderFactory
- **責務:** ファイル拡張子に基づいて適切なローダーインスタンスを生成する。
