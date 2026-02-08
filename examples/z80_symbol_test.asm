; Z80 Symbol and New Instruction Test
; 
; このファイルを RCT の "File -> Load Assembly..." から読み込むと、
; 各ラベル（START, EX_TEST等）がデバッガ上でシンボルとして表示されます。

ORG $0000

START:
    NOP
    LD A, $55
    
    ; 交換命令のテスト
EX_TEST:
    EX DE, HL
    EX AF, AF'
    EXX

    ; インデックスレジスタのテスト (DBで直接オペコードを記述)
IX_TEST:
    ; LD IX, $1234 (DD 21 34 12)
    DB $DD, $21, $34, $12
    ; LD A, (IX+5) (DD 7E 05)
    DB $DD, $7E, $05

    ; 割り込み制御のテスト
INT_TEST:
    DI
    EI

LOOP:
    LD A, $01
    NOP
    ; 停止
    HALT
