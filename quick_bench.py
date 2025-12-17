"""
Quick benchmark comparing optimized vs previous performance.
Tests the 100K state DFA that showed 1.49x speedup before optimization.
"""

import random
import time
from automata.fa.dfa import DFA

def generate_highly_reducible_dfa(num_equivalent_groups, states_per_group, alphabet_size):
    """Generate a DFA with many equivalent states."""
    total_states = num_equivalent_groups * states_per_group
    states = set(range(total_states))
    input_symbols = set(chr(ord("a") + i) if i < 26 else f"s{i}" for i in range(alphabet_size))
    initial_state = 0

    # Create final states
    final_states = set()
    for group_id in range(num_equivalent_groups):
        if group_id % 2 == 0:
            for i in range(states_per_group):
                final_states.add(group_id * states_per_group + i)

    # Create transitions
    transitions = {}
    group_behaviors = []

    for group_id in range(num_equivalent_groups):
        group_behavior = {}
        for symbol in input_symbols:
            if random.random() < 0.8:
                target_group = random.randint(0, num_equivalent_groups - 1)
                group_behavior[symbol] = target_group
            else:
                group_behavior[symbol] = None
        group_behaviors.append(group_behavior)

    for group_id in range(num_equivalent_groups):
        group_behavior = group_behaviors[group_id]
        for i in range(states_per_group):
            state_id = group_id * states_per_group + i
            state_transitions = {}
            for symbol, target_group in group_behavior.items():
                if target_group is not None:
                    target_state = target_group * states_per_group + random.randint(0, states_per_group - 1)
                    state_transitions[symbol] = target_state
            transitions[state_id] = state_transitions

    return DFA(
        states=states,
        input_symbols=input_symbols,
        transitions=transitions,
        initial_state=initial_state,
        final_states=final_states,
        allow_partial=True,
    )

random.seed(42)

print("=" * 80)
print("Testing Optimized Implementation")
print("=" * 80)

# Test case: 100K states, 150 symbols (same as showed 1.49x speedup before)
print("\n100,000 state DFA with 150 symbol alphabet")
print("Expected: 200× reduction (100,000 → ~500 states)")
print("-" * 80)

print("Generating DFA...", end=" ", flush=True)
start = time.perf_counter()
dfa = generate_highly_reducible_dfa(500, 200, 150)
gen_time = time.perf_counter() - start
print(f"done in {gen_time:.2f}s")

num_transitions = sum(len(trans) for trans in dfa.transitions.values())
print(f"DFA: {len(dfa.states):,} states, {num_transitions:,} transitions")

print("\nMinimizing...", end=" ", flush=True)
start = time.perf_counter()
minimal_dfa = dfa.minify()
minify_time = time.perf_counter() - start
print(f"done in {minify_time:.2f}s")

reduction = len(dfa.states) / len(minimal_dfa.states)
print(f"Result: {len(minimal_dfa.states):,} states ({reduction:.1f}× reduction)")

print("\n" + "=" * 80)
print("Performance Summary")
print("=" * 80)
print(f"Previous (unoptimized): ~30.89s")
print(f"Current (optimized):     {minify_time:.2f}s")

if minify_time < 30.89:
    improvement = (30.89 - minify_time) / 30.89 * 100
    speedup = 30.89 / minify_time
    print(f"✅ IMPROVEMENT: {improvement:.1f}% faster ({speedup:.2f}x speedup)")
else:
    slowdown = (minify_time - 30.89) / 30.89 * 100
    print(f"⚠️  Slower by {slowdown:.1f}%")

print("=" * 80)
