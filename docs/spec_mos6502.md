# spec_mos6502.md

## 1. 物理アーキテクチャ・データ
* [cite_start]**アドレス空間**: 16ビット（0x0000 - 0xFFFF） [cite: 183, 185]
* [cite_start]**データ幅**: 8ビット [cite: 10, 184]
* **バイトオーダー**: リトルエンディアン（下位バイト、上位バイトの順）
* [cite_start]**スタック**: 0x0100 - 0x01FF の256バイト領域に固定。SPレジスタは下位8ビットのオフセットのみを保持。 [cite: 56]
* **ベクタアドレス**: 
    * [cite_start]NMI: 0xFFFA/B [cite: 54]
    * [cite_start]RESET: 0xFFFC/D [cite: 52]
    * [cite_start]IRQ/BRK: 0xFFFE/F [cite: 54]

## 2. レジスタセット (Programmer's Model)
* **A (Accumulator)**: 8ビット。主要な算術・論理演算用。
* **X / Y (Index)**: 8ビット。インデックス修飾、カウンタ、ポインタオフセット用。
* **PC (Program Counter)**: 16ビット。
* **S (Stack Pointer)**: 8ビット。常に 0x01 ページ内を指す。
* **P (Status Register)**: 8ビット。
    * [7:N] (Negative), [6:V] (Overflow), [5:R] (Reserved), [4:B] (Break), [3:D] (Decimal), [2:I] (Interrupt Mask), [1:Z] (Zero), [0:C] (Carry)
    * **注意**: `D` フラグがセットされている場合、ADC/SBC命令はBCD（2化10進数）演算として実行される。

## 3. 命令セットとアドレッシング
MOS 6502は合計56種類の命令（OpCodeとしては255種類弱）を持つ。

### 3.1 命令カテゴリ
* **データ転送**: `LDA`, `LDX`, `LDY`, `STA`, `STX`, `STY`, `TAX`, `TAY`, `TXA`, `TYA`, `TSX`, `TXS`
* **算術演算**: `ADC`, `SBC`, `INC`, `DEC`, `CMP`, `CPX`, `CPY`
* **論理/シフト**: `AND`, `ORA`, `EOR`, `BIT`, `ASL`, `LSR`, `ROL`, `ROR`
* **分岐/ジャンプ**: `BCC`, `BCS`, `BEQ`, `BNE`, `BVC`, `BVS`, `BPL`, `BMI`, `JMP`
* **スタック/サブルーチン**: `JSR`, `RTS`, `PHA`, `PHP`, `PLA`, `PLP`
* **フラグ操作/その他**: `CLC`, `SEC`, `CLD`, `SED`, `CLI`, `SEI`, `CLV`, `BRK`, `RTI`, `NOP`

### 3.2 アドレッシングモード（実装上の重要度：高）
* **Implied / Accumulator**: 命令自体が対象を保持（例: `INX`, `ASL A`）。
* **Immediate**: 8ビット即値（例: `LDA #$10`）。
* **Zero Page**: $0000-$00FF への高速アクセス。
* **Absolute**: 16ビット絶対番地指定。
* **Relative**: 条件分岐用（PC相対 -128〜+127）。
* [cite_start]**Indexed (X/Y)**: `Absolute,X` や `ZeroPage,X` 等。 [cite: 55]
* [cite_start]**Indirect**: `JMP ($1234)` 形式。 [cite: 55]
* [cite_start]**Indexed Indirect (X)**: `($00,X)` ゼロページ内でXを加算し、その番地にあるポインタを参照。 [cite: 55]
* [cite_start]**Indirect Indexed (Y)**: `($00),Y` ゼロページ内のポインタ取得後、Yを加算。 [cite: 55]

## 4. RCT統合における特性と警告
* **メモリマップドI/O**: I/O専用空間を持たず、全ての周辺機器はメモリとしてアクセスされる。
* **ゼロページのラップアラウンド**: ゼロページアドレッシング（`Zero Page, X`等）での加算において、0xFFを超えた場合は0x0100にならず0x0000に戻る。
* **ページ境界またぎのペナルティ**: ページ境界（下位8ビットの溢れ）を跨ぐアドレッシングが発生した場合、実行サイクルが1増加する。
* **JMPバグ**: `JMP ($xxFF)` 実行時にページを跨げず、`$xxFF` と `$xx00` からアドレスを読み込んでしまうオリジナルハードウェアの挙動が存在する。
* **SPの挙動**: スタックへのPushによりSPは減少し、Pullにより増加する。
