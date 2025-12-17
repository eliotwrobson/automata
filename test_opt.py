"""Test optimizations with smaller DFA first"""

import random
import time
from automata.fa.dfa import DFA

def generate_highly_reducible_dfa(num_equivalent_groups, states_per_group, alphabet_size):
    """Generate a DFA with many equivalent states."""
    total_states = num_equivalent_groups * states_per_group
    states = set(range(total_states))
    input_symbols = set(chr(ord("a") + i) if i < 26 else f"s{i}" for i in range(alphabet_size))
    initial_state = 0

    final_states = set()
    for group_id in range(num_equivalent_groups):
        if group_id % 2 == 0:
            for i in range(states_per_group):
                final_states.add(group_id * states_per_group + i)

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

test_cases = [
    (200, 100, 100, "20K states, 100 symbols", 4.4),   # Reference: ~4.4s old, ~4.0s new
    (500, 200, 150, "100K states, 150 symbols", 30.89), # Reference: ~46s old, ~30.89s new
]

print("=" * 80)
print("Testing Optimized Implementation")
print("=" * 80)

for num_groups, states_per_group, alphabet_size, desc, prev_time in test_cases:
    total_states = num_groups * states_per_group
    print(f"\nTest: {desc} ({total_states:,} states, {alphabet_size} symbols)")
    print("-" * 80)
    
    print("Generating DFA...", end=" ", flush=True)
    start = time.perf_counter()
    dfa = generate_highly_reducible_dfa(num_groups, states_per_group, alphabet_size)
    gen_time = time.perf_counter() - start
    print(f"done in {gen_time:.2f}s")
    
    print("Minimizing...", end=" ", flush=True)
    start = time.perf_counter()
    minimal_dfa = dfa.minify()
    minify_time = time.perf_counter() - start
    print(f"done in {minify_time:.2f}s")
    
    reduction = len(dfa.states) / len(minimal_dfa.states)
    print(f"Result: {len(dfa.states):,} → {len(minimal_dfa.states):,} states ({reduction:.1f}× reduction)")
    
    if minify_time < prev_time:
        improvement = (prev_time - minify_time) / prev_time * 100
        speedup = prev_time / minify_time
        print(f"✅ {improvement:.1f}% faster than previous ({speedup:.2f}x)")
    else:
        slowdown = (minify_time - prev_time) / prev_time * 100
        print(f"⚠️  {slowdown:.1f}% slower than previous")

print("\n" + "=" * 80)
print("Summary: Optimizations focused on:")
print("  1. Block size caching - avoid repeated len() calls")
print("  2. Inverse worklist mapping - O(1) instead of O(α) symbol iteration")
print("  3. Combined size computation - fewer get_set_by_id() calls")
print("=" * 80)
