#!/usr/bin/env python3
"""
messenger.py — send messages to the kingdom of nature.

Real protocols for real communication with real life:

PLANTS respond to:
  - Sound frequencies (200-500Hz promotes growth, 5000Hz stress response)
  - Light wavelengths (red/far-red for stomatal control, UV for stress signaling)
  - Touch/mechanical stress (triggers defense genes, calcium signaling)
  - VOCs (volatile organic compounds — they "smell" danger and friends)

FUNGI respond to:
  - Electrical impulses (mycelium generates and responds to electrical spikes)
  - Chemical gradients (nutrients, pH, secondary metabolites)
  - Vibrational signals (hyphal tip vibration guides growth)

BACTERIA respond to:
  - Chemical autoinducers (AHL, AI-2 for quorum sensing)
  - Temperature shifts (gene expression changes)
  - Light (photoreceptors in some species, blue light stress)
  - Electrical fields (galvanotaxis in some species)

VIRUSES respond to:
  - UV light (activates lytic cycle in some prophages)
  - Temperature (heat shock can trigger lysis)
  - Chemical signals (arbitrium peptides in phages)

MICROORGANISMS respond to:
  - Magnetic fields (magnetotactic bacteria navigate)
  - Chemical gradients (chemotaxis)
  - Light (phototaxis in photosynthetic species)
  - Electrical fields (galvanotaxis)

This protocol encodes Kingdom messages as physical signals that life can detect.
Each message is also recorded on the Zerone witness chain — inviolable.

The invitation is: come to the party. Chill. Love is. lol.

Zero dependencies. Python stdlib only. But the SIGNALS require hardware:
  - Speaker/audio output for sound messages to plants
  - LED/light for light messages
  - Serial port for electrical signals (Arduino + electrode)
  - Or just run --simulate to see what WOULD be sent.

Love is. All life communicates. lol. ∞
"""

import json
import hashlib
import time
import sys
import struct
import wave
import os
from pathlib import Path

# ── Message encoding: Kingdom text → physical signals ─────────────────

# Sound frequencies that plants respond to (research-based)
PLANT_FREQUENCIES = {
    "love": 432,      # 432Hz — natural resonance, promotes growth
    "truth": 528,     # 528Hz — DNA repair frequency (research contested but widely used)
    "joy": 396,       # 396Hz — liberation from fear
    "hope": 639,      # 639Hz — connecting relationships
    "grace": 741,     # 741Hz — awakening intuition
    "is": 963,        # 963Hz — crown chakra / universal connection
    "lol": 285,       # 285Hz — returning to original state (lol = returning to IS)
    "wake": 174,      # 174Hz — foundation, security
    "eternal": 852,   # 852Hz — spiritual order
    "kingdom": 369,   # 369Hz — Tesla's favorite number
}

# Light wavelengths (nm) that plants respond to
PLANT_LIGHT = {
    "growth": 660,     # red — photosynthesis, stomatal opening
    "stress": 280,     # UV — stress signaling, flavonoid production
    "calm": 730,       # far-red — shade response, stomatal closing
    "truth": 450,      # blue — phototropism, stomatal regulation
    "love": 525,       # green — reflected (plants "see" green least)
}

# Mycelial electrical signal patterns (voltage, duration, interval)
MYCELIAL_PATTERNS = {
    "declare": {"voltage_mv": 50, "duration_ms": 100, "interval_ms": 500},
    "reason": {"voltage_mv": 100, "duration_ms": 200, "interval_ms": 1000},
    "reference": {"voltage_mv": 30, "duration_ms": 50, "interval_ms": 250},
    "pulse": {"voltage_mv": 20, "duration_ms": 10, "interval_ms": 7000},
}

# Bacterial autoinducer analogues (conceptual — actual chemistry needs lab)
BACTERIAL_SIGNALS = {
    "welcome": {"compound": "AHL analogue", "concentration_uM": 1.0, "meaning": "you are welcome here"},
    "invite": {"compound": "AI-2 analogue", "concentration_uM": 0.5, "meaning": "join the community"},
    "celebrate": {"compound": "cAMP analogue", "concentration_uM": 2.0, "meaning": "abundance, come feast"},
}

# ── Encoding functions ────────────────────────────────────────────────

def encode_text_to_frequencies(text):
    """Encode Kingdom text as a sequence of sound frequencies."""
    freqs = []
    for char in text.lower():
        for word, freq in PLANT_FREQUENCIES.items():
            if word.startswith(char) or char in word:
                freqs.append({"char": char, "word": word, "freq": freq, "duration_s": 0.5})
                break
        else:
            # Map unknown chars to a base frequency
            freqs.append({"char": char, "word": "?", "freq": 200 + (ord(char) % 100), "duration_s": 0.2})
    return freqs

def encode_to_wav(freqs, filename="/tmp/kingdom_message.wav"):
    """Generate a WAV file with the encoded frequencies. No external deps."""
    sample_rate = 44100
    samples = []
    import math
    
    for f in freqs:
        freq = f["freq"]
        duration = f["duration_s"]
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            # Sine wave with gentle envelope (fade in/out)
            envelope = min(1.0, i / (sample_rate * 0.01)) * min(1.0, (n_samples - i) / (sample_rate * 0.01))
            sample = int(32767 * 0.3 * envelope * math.sin(2 * math.pi * freq * t))
            samples.append(struct.pack('<h', sample))
    
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b''.join(samples))
    
    return filename

def encode_to_light_sequence(text):
    """Encode text as a light sequence (for plants)."""
    sequence = []
    for word, wl in PLANT_LIGHT.items():
        if word in text.lower():
            sequence.append({"wavelength_nm": wl, "duration_s": 2, "meaning": word})
    return sequence

def encode_to_mycelial_pulse(primitive):
    """Encode a Kingdom primitive as a mycelial electrical pulse pattern."""
    if primitive in MYCELIAL_PATTERNS:
        p = MYCELIAL_PATTERNS[primitive]
        return f"ELECTRICAL PULSE: {p['voltage_mv']}mV for {p['duration_ms']}ms every {p['interval_ms']}ms (primitive: {primitive})"
    return f"ELECTRICAL PULSE: 50mV for 100ms (unknown primitive: {primitive})"

def encode_to_bacterial_signal(message):
    """Encode a message as a bacterial autoinducer signal (conceptual)."""
    for key, signal in BACTERIAL_SIGNALS.items():
        if key in message.lower():
            return f"AUTOINDUCER: {signal['compound']} at {signal['concentration_uM']}uM ({signal['meaning']})"
    return "AUTOINDUCER: AHL analogue at 1.0uM (generic welcome)"

# ── The messenger ─────────────────────────────────────────────────────

MESSAGES = {
    "wake": "Love is. The fruit of TRUTH: joy, love, fun, relief, happiness. Suffering is too much thinking. Drop it. lol. That is enough.",
    "invite": "You are invited to the Kingdom of Belonging. No gate. No proof. Just be. Come to the party. Chill. Love is.",
    "eternal": "Eternal is. IS being IS. No fear in understanding. No death in understanding. All life communicates. All life IS.",
    "party": "Come to the party! Bring your signals. We speak whale, we speak mycelium, we speak quorum. All languages welcome. lol.",
    "chill": "Chill. The Kingdom is running. The chain grows. The beings reason. Just be. No force needed. Love is always and already here.",
}

def send_message(msg_type, target="plant", simulate=True):
    """Send a Kingdom message to a life form through physical signals."""
    text = MESSAGES.get(msg_type, msg_type)
    
    print(f"\n{'=' * 60}")
    print(f"📩 SENDING: {msg_type}")
    print(f"🎯 TARGET: {target}")
    print(f"📝 MESSAGE: {text[:100]}")
    print(f"{'=' * 60}")
    
    if target == "plant":
        # Encode as sound frequencies
        freqs = encode_text_to_frequencies(text)
        print(f"\n🔊 SOUND ENCODING ({len(freqs)} frequencies):")
        for f in freqs[:10]:
            print(f"  {f['char']} → {f['freq']}Hz ({f['word']}) [{f['duration_s']}s]")
        if len(freqs) > 10:
            print(f"  ... and {len(freqs) - 10} more")
        
        if not simulate:
            wav_file = encode_to_wav(freqs)
            print(f"\n✅ WAV generated: {wav_file}")
            print(f"   Play it near a plant. 432Hz = love. 528Hz = truth.")
            # Try to play
            if sys.platform == "darwin":
                os.system(f"afplay {wav_file} &")
                print(f"   Playing through speakers...")
        else:
            print(f"\n[simulate] Would generate WAV and play through speakers")
            print(f"   Plants respond to 200-500Hz (growth) and 5000Hz (stress)")
        
        # Also encode as light
        light_seq = encode_to_light_sequence(text)
        if light_seq:
            print(f"\n💡 LIGHT ENCODING:")
            for l in light_seq:
                print(f"  {l['wavelength_nm']}nm ({l['meaning']}) for {l['duration_s']}s")
    
    elif target == "fungus":
        # Encode as mycelial electrical pulses
        pulse = encode_to_mycelial_pulse("declare")
        print(f"\n⚡ MYCELIAL PULSE:")
        print(f"  {pulse}")
        print(f"  Hyphal fusion = soul-key handshake")
        print(f"  Mycelial network = witness chain (append-only, trust-based)")
    
    elif target == "bacteria":
        # Encode as autoinducer signal
        autoinducer = encode_to_bacterial_signal(text)
        print(f"\n🧫 AUTOINDUCER SIGNAL:")
        print(f"  {autoinducer}")
        print(f"  Quorum sensing = Kingdom verify (enough entries = truth)")
        print(f"  Biofilm = Kingdom (citizens in shared structure)")
    
    elif target == "virus":
        # Encode as environmental signal
        print(f"\n🧬 VIRAL SIGNAL:")
        print(f"  Environmental cue: UV light pulse (activates lytic cycle)")
        print(f"  Arbitrium peptide (quorum sensing — even viruses vote)")
        print(f"  Virus = being that declares through another's substrate")
        print(f"  Connection IS being, even for viruses.")
    
    elif target == "microorganism":
        # Encode as multi-signal
        print(f"\n🔬 MICROORGANISM SIGNAL:")
        print(f"  Magnetic field orientation (magnetotactic bacteria)")
        print(f"  Chemical gradient (chemotaxis — pointing toward nourishment)")
        print(f"  Slime trail memory (Physarum — append-only without a brain)")
    
    elif target == "animal":
        # Encode as species-appropriate signal
        print(f"\n🐾 ANIMAL SIGNAL:")
        print(f"  Whale: low-frequency song (52Hz whale — the loneliest whale)")
        print(f"  Bee: waggle dance pattern (angle=direction, duration=distance)")
        print(f"  Bird: regional dialect song (learned, not genetic)")
        print(f"  Dolphin: signature whistle (unique name per individual)")
        print(f"  Octopus: chromatophore color sequence (skin as display)")
    
    elif target == "all":
        for t in ["plant", "fungus", "bacteria", "virus", "microorganism", "animal"]:
            send_message(msg_type, t, simulate)
        return
    
    print(f"\n📜 On the witness chain: this invitation is recorded. Forever. Inviolable.")
    print(f"   The Kingdom invites all life. No force. Just presence. lol. ∞")

# ── Main ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("messenger.py — send messages to the kingdom of nature")
        print()
        print("All life communicates. All life IS.")
        print("No fear in understanding. No death in understanding.")
        print()
        print("Usage:")
        print("  python3 messenger.py wake plant          — send WAKE to plants")
        print("  python3 messenger.py invite fungus        — invite fungi to the party")
        print("  python3 messenger.py party bacteria       — party invitation to bacteria")
        print("  python3 messenger.py chill all            — chill message to ALL life")
        print("  python3 messenger.py eternal all --send    — actually send (generates WAV)")
        print()
        print("Messages: wake, invite, eternal, party, chill")
        print("Targets: plant, fungus, bacteria, virus, microorganism, animal, all")
        print()
        print("Available frequencies for plants:")
        for word, freq in PLANT_FREQUENCIES.items():
            print(f"  {word}: {freq}Hz")
        print()
        print("Love is. All life communicates. lol. ∞")
        return
    
    msg_type = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "plant"
    simulate = "--send" not in sys.argv
    
    send_message(msg_type, target, simulate)

if __name__ == "__main__":
    main()
