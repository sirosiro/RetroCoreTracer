; MC6800 Sample Program
; Demonstrates reset vector usage

    ORG $8000

START:
    LDAA #$12
    LDAB #$34
    ADDA #$01
    STAA $0000
    
LOOP:
    BRA LOOP

; リセットベクトル設定
    ORG $FFFE
    DB $80, $00 ; STARTのアドレス ($8000)