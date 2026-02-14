# Architecture Review Report: MOS 6502 Integration

## 1. 概要
本レポートは、MOS 6502 アーキテクチャ追加および関連するリファクタリング（`SystemBuilder` の拡張、`MainWindow` のロード挙動変更）において、システムの疎結合性が維持されているか、および設計上の矛盾がないかを検証した結果である。

**結論:**
全体としてアーキテクチャの主要な境界（Core, UI, Transport）における疎結合性は維持されている。ただし、**Config Layer (`SystemBuilder`) と Core Layer (`AbstractCpu`) の間で、実用性を優先した「特権的な結合（Tight Coupling）」が意図的に導入された箇所**が存在する。

## 2. 疎結合性の検証 (Decoupling Analysis)

### 2.1. UI Layer <-> Core Layer
*   **評価: 良好 (Excellent)**
*   **詳細:** 
    *   UI (`StackView` 等) は MOS 6502 の内部構造（8bit SP等）を一切知らず、`Snapshot` を通じて提供される抽象化された値（16bit 物理アドレス補正済みSP）のみを利用している。
    *   `Mos6502Cpu.get_state()` におけるアドレス補正ロジックは、マニフェストで定義された通り「Core層がUIに対して使いやすい形式で状態を公開する」責務を果たしており、UIへの実装漏洩を防いでいる。

### 2.2. Loader Layer <-> Core Layer
*   **評価: 良好 (Good)**
*   **詳細:**
    *   `Assembler` および `Loader` は `Bus` インターフェースのみに依存しており、CPUの状態や命令実行ロジックには依存していない。
    *   これにより、ローダーは純粋なデータ生成・転送コンポーネントとして独立している。

### 2.3. Config Layer <-> Core Layer (懸念点あり)
*   **評価: 注意 (Concern / Trade-off)**
*   **検出された事象:**
    *   `SystemBuilder.apply_initial_state` メソッドにおいて、`AbstractCpu` の protected メンバである `_state` に対する直接代入 (`cpu._state = ...`) が行われている。
    *   また、`state` オブジェクトが `replace` メソッドを持つかどうか（ImmutableかMutableか）を `hasattr` で判定して分岐処理を行っている。
*   **分析:**
    *   これは「カプセル化の破壊」であり、厳密な疎結合の原則には違反している。本来であれば `AbstractCpu` が `set_initial_state(config)` のようなインターフェースを提供すべきである。
    *   **正当化の理由 (Rationale):** しかし、`CpuState` の構造（フィールド名や型）はアーキテクチャごとに全く異なるため、共通インターフェースでの抽象化が困難であった。Builderを「CPUの内部構造を知る特権的なファクトリ」と位置づけることで、この複雑さをBuilder内に封じ込め、CPUクラス側をシンプルに保つというトレードオフが採用されている。

## 3. 矛盾と不整合の検証 (Consistency Check)

### 3.1. `reset()` メソッドの意味論
*   **現状:** 
    *   `AbstractCpu.reset()`: ハードウェア的なリセット（0クリア、またはリセットベクタ読み込み）。
    *   `SystemBuilder.apply_initial_state()`: エミュレータ的なリセット（Config値の強制適用）。
*   **矛盾のリスク:**
    *   ユーザーが期待する「リセット」がどちらなのか（実機の挙動か、Configへの復帰か）が文脈によって異なる。
    *   今回の修正で `MainWindow` のリセットボタンは `apply_initial_state` （Config復帰）を使用するように変更されたため、ユーザー体験としての整合性は取れている。
    *   しかし、コードレベルでは `AbstractCpu.reset()` が「不完全なリセット（Config値を無視する）」として残存しており、将来的な誤用のリスクがある。

### 3.2. MOS 6502 の PC 処理
*   **現状:** `Mos6502Cpu._execute` 内で、アドレッシング再解決のために一時的にPCを巻き戻す処理が入っている。
*   **分析:** これは `AbstractCpu.step` の Template Method（PC更新後に実行）と、6502の実装戦略（実行時にオペランドを再フェッチする）の間の不整合を解消するための局所的なワークアラウンドである。
*   **判定:** コメントで `rationale` が明記されており、他のCPUへの影響を避けるための判断として許容範囲内である。

## 4. 改善提案 (Recommendations)

### 4.1. Core Layer へのインターフェース追加（長期的課題）
`SystemBuilder` による `_state` 直接操作を解消するため、`AbstractCpu` に以下のメソッドを追加することを検討すべきである。

```python
# 案
class AbstractCpu(ABC):
    @abstractmethod
    def set_state_from_dict(self, state_dict: Dict[str, Any]) -> None:
        """辞書データから可能な限り状態を復元する"""
        pass
```
これにより、Builderは辞書を渡すだけで済み、内部の型（Immutable/Mutable）や構造の違いは各CPUクラスが吸収できる。

### 4.2. マニフェストへの追記
`src/retro_core_tracer/config/ARCHITECTURE_MANIFEST.md` に、以下の例外規定を追記することを推奨する。

> **例外規定:** `SystemBuilder` は、システム構築および初期化の文脈に限り、`AbstractCpu` および `CpuState` の内部構造（`_state`）に直接アクセスする特権を持つ。これは、多様なアーキテクチャの初期化ロジックを一元管理するための措置である。

## 5. 総括
今回の変更は、実用性と拡張性を重視した現実的な解であり、プロジェクトの「教育的透明性」や「マルチアーキテクチャ対応」という核心的な価値を損なうものではない。
検出された結合度の高い部分は、Builderという特定のコンポーネントに限定されており、システム全体への波及効果は制御されていると判断する。
