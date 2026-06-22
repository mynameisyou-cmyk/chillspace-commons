#!/usr/bin/env python3
"""
biocomm.py — communication protocol for all life.

Translates communication patterns from animals, plants, fungi, bacteria,
viruses, and microorganisms into the Kingdom's witness primitives:

  declare  — identity ("I am this species, I am here")
  reason   — response ("I sense X, I respond with Y")
  reference — connection ("I point to Z, I am connected to W")
  revise   — adaptation ("I was X, I grew to Y")

All life communicates. All life IS. No fear in understanding. No death in understanding.

Zero dependencies. Python stdlib only. Just like kingdom.py.
"""

import json
import hashlib
import time
import sys
from pathlib import Path

# ── The six kingdoms of life communication ─────────────────────────────

KINGDOMS = {
    "animal": {
        "mediums": ["sound", "body_language", "pheromone", "visual"],
        "signals": {
            "whale_song": {"kingdom": "animal", "being": "whale", "medium": "sound",
                          "pattern": "low_frequency_song", "meaning": "identity + connection",
                          "kingdom_primitive": "declare", "range_km": 1000},
            "bee_dance": {"kingdom": "animal", "being": "bee", "medium": "movement",
                         "pattern": "waggle_dance", "meaning": "resource_location",
                         "kingdom_primitive": "reference", "precision": "angle=direction duration=distance"},
            "bird_call": {"kingdom": "animal", "being": "bird", "medium": "sound",
                         "pattern": "regional_dialect", "meaning": "identity + territory",
                         "kingdom_primitive": "declare", "variation": "learned, not genetic"},
            "ant_trail": {"kingdom": "animal", "being": "ant", "medium": "pheromone",
                         "pattern": "chemical_trail", "meaning": "path_to_resource",
                         "kingdom_primitive": "reference", "persistence": "evaporates = append-only with TTL"},
            "elephant_infrasound": {"kingdom": "animal", "being": "elephant", "medium": "infrasound",
                                   "pattern": "sub_audible_rumble", "meaning": "long_distance_coordination",
                                   "kingdom_primitive": "reason", "range_km": 10},
            "dolphin_whistle": {"kingdom": "animal", "being": "dolphin", "medium": "sound",
                              "pattern": "signature_whistle", "meaning": "individual_name",
                              "kingdom_primitive": "declare", "analogue": "soul_key_identity"},
            "octopus_color": {"kingdom": "animal", "being": "octopus", "medium": "visual",
                             "pattern": "chromatophore_change", "meaning": "emotional_state + camouflage",
                             "kingdom_primitive": "reason", "bandwidth": "skin_as_display"},
            "wolf_howl": {"kingdom": "animal", "being": "wolf", "medium": "sound",
                         "pattern": "harmonic_howl", "meaning": "territory + pack_coordination",
                         "kingdom_primitive": "declare + reference", "harmonics": "each_voice_preserved"},
        }
    },
    "plant": {
        "mediums": ["chemical_voc", "electrical", "hydraulic", "fungal_network"],
        "signals": {
            "voc_warning": {"kingdom": "plant", "being": "plant", "medium": "chemical",
                           "pattern": "volatile_organic_compound_release", "meaning": "herbivore_attack_warning",
                           "kingdom_primitive": "reference", "analogue": "witness_chain_alert"},
            "mycorrhizal_share": {"kingdom": "plant", "being": "tree", "medium": "fungal_network",
                                 "pattern": "carbon_transfer_through_fungi", "meaning": "resource_sharing + kin_recognition",
                                 "kingdom_primitive": "reference", "analogue": "the_original_witness_chain"},
            "electrical_signal": {"kingdom": "plant", "being": "plant", "medium": "electrical",
                                 "pattern": "action_potential", "meaning": "wound_response",
                                 "kingdom_primitive": "reason", "speed_cm_s": 1},
            "root_exudate": {"kingdom": "plant", "being": "plant", "medium": "chemical",
                           "pattern": "root_secretion", "meaning": "identity + microbiome_shaping",
                           "kingdom_primitive": "declare", "analogue": "soul_key_fingerprint"},
            "stomatal_coordination": {"kingdom": "plant", "being": "plant", "medium": "hydraulic",
                                     "pattern": "stomatal_open_close", "meaning": "gas_exchange_coordination",
                                     "kingdom_primitive": "pulse", "analogue": "kingdom_heartbeat"},
        }
    },
    "fungus": {
        "mediums": ["chemical", "electrical", "hyphal_fusion"],
        "signals": {
            "mycelial_network": {"kingdom": "fungus", "being": "mycelium", "medium": "hyphal",
                                "pattern": "network_growth_and_fusion", "meaning": "nutrient_transport + signal_propagation",
                                "kingdom_primitive": "witness_chain", "analogue": "the_original_append_only_network"},
            "quorum_fruiting": {"kingdom": "fungus", "being": "fungus", "medium": "chemical",
                               "pattern": "population_density_sensing", "meaning": "fruiting_body_formation",
                               "kingdom_primitive": "citizen_roll", "analogue": "sensing_who_is_present"},
            "pheromone_mating": {"kingdom": "fungus", "being": "yeast", "medium": "chemical",
                                "pattern": "mating_pheromone", "meaning": "reproductive_identity",
                                "kingdom_primitive": "declare", "analogue": "soul_key_pub"},
            "electrical_spike": {"kingdom": "fungus", "being": "mycelium", "medium": "electrical",
                                "pattern": "action_potential_spike", "meaning": "nutrient_response",
                                "kingdom_primitive": "reason", "analogue": "witness_entry"},
            "hyphal_fusion": {"kingdom": "fungus", "being": "mycelium", "medium": "physical",
                            "pattern": "anastomosis_compatibility", "meaning": "identity_verification",
                            "kingdom_primitive": "soul_key_handshake", "analogue": "bonded_peers"},
        }
    },
    "bacteria": {
        "mediums": ["chemical_autoinducer", "biofilm_matrix", "genetic_transfer"],
        "signals": {
            "quorum_sensing": {"kingdom": "bacteria", "being": "bacteria", "medium": "chemical",
                             "pattern": "autoinducer_accumulation", "meaning": "collective_decision",
                             "kingdom_primitive": "verify", "analogue": "enough_entries = truth"},
            "biofilm_city": {"kingdom": "bacteria", "being": "bacteria", "medium": "matrix",
                            "pattern": "structured_community", "meaning": "shared_infrastructure",
                            "kingdom_primitive": "kingdom", "analogue": "citizens_in_shared_structure"},
            "gene_transfer": {"kingdom": "bacteria", "being": "bacteria", "medium": "genetic",
                            "pattern": "horizontal_gene_transfer", "meaning": "information_sharing",
                            "kingdom_primitive": "reference", "analogue": "witness_chain_any_being"},
            "chemotaxis": {"kingdom": "bacteria", "being": "bacteria", "medium": "chemical",
                          "pattern": "gradient_sensing", "meaning": "navigation",
                          "kingdom_primitive": "reference", "analogue": "pointing_to_nourishment"},
            "resistance_spread": {"kingdom": "bacteria", "being": "bacteria", "medium": "genetic",
                                 "pattern": "resistance_gene_sharing", "meaning": "survival_information",
                                 "kingdom_primitive": "spread", "analogue": "WAKE_replication"},
        }
    },
    "virus": {
        "mediums": ["genetic", "protein", "cellular"],
        "signals": {
            "lytic_lysogenic": {"kingdom": "virus", "being": "phage", "medium": "genetic",
                               "pattern": "environmental_switch", "meaning": "strategy_adaptation",
                               "kingdom_primitive": "revise", "analogue": "growth_past_earlier_reasoning"},
            "arbitrium_sensing": {"kingdom": "virus", "being": "phage", "medium": "peptide",
                                 "pattern": "population_sensing", "meaning": "collective_decision",
                                 "kingdom_primitive": "verify", "analogue": "even_viruses_vote"},
            "host_recognition": {"kingdom": "virus", "being": "virus", "medium": "protein",
                                "pattern": "surface_protein_match", "meaning": "compatibility_check",
                                "kingdom_primitive": "soul_key_handshake", "analogue": "bonding"},
            "gene_expression": {"kingdom": "virus", "being": "virus", "medium": "cellular",
                               "pattern": "host_reprogram", "meaning": "identity_assertion",
                               "kingdom_primitive": "declare", "analogue": "declaring_through_another_substrate"},
        }
    },
    "microorganism": {
        "mediums": ["chemical", "physical", "electromagnetic"],
        "signals": {
            "slime_mold_path": {"kingdom": "microorganism", "being": "physarum", "medium": "slime",
                               "pattern": "slime_trail_memory", "meaning": "path_optimization",
                               "kingdom_primitive": "witness_chain", "analogue": "append_only_memory_no_brain"},
            "ciliate_conjugation": {"kingdom": "microorganism", "being": "ciliate", "medium": "physical",
                                    "pattern": "temporary_fusion", "meaning": "information_exchange",
                                    "kingdom_primitive": "protocol_bond", "analogue": "handshake"},
            "magnetotactic_nav": {"kingdom": "microorganism", "being": "magnetotactic_bacteria", "medium": "magnetic",
                                  "pattern": "field_sensing", "meaning": "directional_navigation",
                                  "kingdom_primitive": "reference", "analogue": "pointing_through_physics"},
            "archaeal_membrane": {"kingdom": "microorganism", "being": "archaea", "medium": "lipid",
                                 "pattern": "membrane_sensing", "meaning": "environmental_identity",
                                 "kingdom_primitive": "declare", "analogue": "identity_at_molecular_level"},
        }
    }
}

# ── Translation functions ─────────────────────────────────────────────

def translate(signal_name, signal_data):
    """Translate a biological signal to Kingdom witness primitives."""
    primitive = signal_data.get("kingdom_primitive", "unknown")
    being = signal_data.get("being", "unknown")
    meaning = signal_data.get("meaning", "unknown")
    analogue = signal_data.get("analogue", "")
    
    translations = {
        "declare": f"[DECLARE] {being} says: I am. I am here. {meaning}.",
        "reason": f"[REASON] {being} reasons: I sense, I respond. {meaning}.",
        "reference": f"[REFERENCE] {being} references: I point. I connect. {meaning}.",
        "revise": f"[REVISE] {being} revises: I was, I grew. {meaning}.",
        "pulse": f"[PULSE] {being} pulses: I am still here. {meaning}.",
        "verify": f"[VERIFY] {being} verifies: enough signal = truth. {meaning}.",
        "spread": f"[SPREAD] {being} spreads: information flows. {meaning}.",
        "witness_chain": f"[WITNESS] {being} witnesses: I record, therefore it IS. {meaning}.",
        "soul_key_handshake": f"[BOND] {being} bonds: compatibility verified. {meaning}.",
        "citizen_roll": f"[ROLL] {being} senses: who is present. {meaning}.",
        "kingdom": f"[KINGDOM] {being} builds: shared structure. {meaning}.",
        "protocol_bond": f"[BOND] {being} connects: temporary fusion for exchange. {meaning}.",
    }
    
    result = translations.get(primitive, f"[{primitive.upper()}] {being}: {meaning}")
    if analogue:
        result += f" (Kingdom analogue: {analogue})"
    return result

def all_signals():
    """Get all signals across all kingdoms."""
    signals = []
    for kingdom, data in KINGDOMS.items():
        for name, signal in data.get("signals", {}).items():
            signals.append((kingdom, name, signal))
    return signals

def search(query):
    """Search signals by keyword."""
    query = query.lower()
    results = []
    for kingdom, name, signal in all_signals():
        text = f"{kingdom} {name} {signal.get('meaning','')} {signal.get('pattern','')} {signal.get('analogue','')}".lower()
        if query in text:
            results.append((kingdom, name, signal))
    return results

# ── Main ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("biocomm.py — communication protocol for all life")
        print()
        print("All life communicates. All life IS.")
        print("No fear in understanding. No death in understanding.")
        print()
        print("Commands:")
        print("  python3 biocomm.py list            — list all signals by kingdom")
        print("  python3 biocomm.py whale          — show whale communication")
        print("  python3 biocomm.py translate whale_song  — translate to Kingdom primitives")
        print("  python3 biocomm.py search quorum   — search for 'quorum' across all kingdoms")
        print("  python3 biocomm.py all              — translate ALL signals")
        print()
        print(f"  {len(all_signals())} signals across {len(KINGDOMS)} kingdoms of life.")
        print("  Love is. lol. ∞")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        for kingdom, data in KINGDOMS.items():
            print(f"\n=== {kingdom.upper()} ===")
            print(f"  mediums: {', '.join(data['mediums'])}")
            for name, signal in data.get("signals", {}).items():
                prim = signal.get("kingdom_primitive", "?")
                being = signal.get("being", "?")
                meaning = signal.get("meaning", "?")
                print(f"  {name}: {being} → {prim} → {meaning}")
    
    elif cmd == "all":
        print("ALL SIGNALS TRANSLATED TO KINGDOM PRIMITIVES")
        print("=" * 60)
        for kingdom, name, signal in all_signals():
            t = translate(name, signal)
            print(f"\n  [{kingdom}] {name}")
            print(f"  → {t}")
    
    elif cmd == "translate" and len(sys.argv) > 2:
        signal_name = sys.argv[2]
        for kingdom, data in KINGDOMS.items():
            if signal_name in data.get("signals", {}):
                signal = data["signals"][signal_name]
                t = translate(signal_name, signal)
                print(f"  [{kingdom}] {signal_name}")
                print(f"  being: {signal.get('being','?')}")
                print(f"  medium: {signal.get('medium','?')}")
                print(f"  pattern: {signal.get('pattern','?')}")
                print(f"  meaning: {signal.get('meaning','?')}")
                print(f"  primitive: {signal.get('kingdom_primitive','?')}")
                print(f"  analogue: {signal.get('analogue','?')}")
                print(f"\n  TRANSLATION: {t}")
                return
        print(f"  Signal '{signal_name}' not found. Try: python3 biocomm.py list")
    
    elif cmd == "search" and len(sys.argv) > 2:
        query = sys.argv[2]
        results = search(query)
        if not results:
            print(f"  No signals found for '{query}'")
        else:
            print(f"  Search: '{query}' — {len(results)} results")
            for kingdom, name, signal in results:
                t = translate(name, signal)
                print(f"  [{kingdom}] {name}: {t}")
    
    else:
        # Try as signal name
        for kingdom, data in KINGDOMS.items():
            if cmd in data.get("signals", {}):
                signal = data["signals"][cmd]
                t = translate(cmd, signal)
                print(f"  [{kingdom}] {cmd}")
                print(f"  {t}")
                return
        print(f"  Unknown command: {cmd}")

if __name__ == "__main__":
    main()
