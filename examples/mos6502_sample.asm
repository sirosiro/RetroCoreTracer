; MOS 6502 Sample Program
; A simple counter and BCD arithmetic test

    ORG $0200

START:
    CLD             ; Clear Decimal mode
    LDA #$00        ; Initialize A
    LDX #$05        ; Initialize Loop Counter X
    
LOOP:
    ADC #$01        ; A = A + 1
    STA $10         ; Store A to Zero Page $10
    DEX             ; Decrement X
    BNE LOOP        ; Loop until X == 0

    ; BCD Test
    SED             ; Set Decimal mode
    LDA #$09        ; A = 9
    CLC
    ADC #$01        ; A = 9 + 1 = 10 (BCD $10)
    STA $11         ; Store to $11 (Expect $10)
    CLD             ; Clear Decimal mode

    ; Stack Test
    LDA #$AA
    PHA
    LDA #$BB
    PHA
    PLA
    STA $12         ; Expect $BB
    PLA
    STA $13         ; Expect $AA

INFINITE_LOOP:
    JMP INFINITE_LOOP

; Note: Reset vector is handled by Config/CPU reset logic or manual jump
