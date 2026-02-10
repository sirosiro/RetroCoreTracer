; MC6800 Sample Program
; LDAA #$10
; ADDA #$20
; STAA $1000
; Loop: NOP
; BRA Loop

    ORG $0000
START:
    LDAA #$10
    ADDA #$20
    STAA $1000
LOOP:
    NOP
    BRA LOOP
