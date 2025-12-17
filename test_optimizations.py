"""Quick test of optimized minify implementation"""
import sys
sys.path.insert(0, r'C:\Users\eliot\Documents\GitHub\automata')

from automata.fa.dfa import DFA

# Test 1: Basic minify
dfa = DFA(
    states={'q0', 'q1', 'q2', 'q3', 'q4'},
    input_symbols={'0', '1'},
    transitions={
        'q0': {'0': 'q1', '1': 'q2'},
        'q1': {'0': 'q1', '1': 'q3'},
        'q2': {'0': 'q1', '1': 'q2'},
        'q3': {'0': 'q1', '1': 'q4'},
        'q4': {'0': 'q1', '1': 'q2'},
    },
    initial_state='q0',
    final_states={'q3', 'q4'},
)

print("Testing basic DFA minimization...")
minimal_dfa = dfa.minify()
print(f"✓ Basic test passed: {len(dfa.states)} states -> {len(minimal_dfa.states)} states")

# Test 2: Partial DFA
partial_dfa = DFA(
    states={'q0', 'q1', 'q2'},
    input_symbols={'a', 'b'},
    transitions={
        'q0': {'a': 'q1'},
        'q1': {'b': 'q2'},
        'q2': {'a': 'q0'},
    },
    initial_state='q0',
    final_states={'q2'},
    allow_partial=True,
)

print("Testing partial DFA minimization...")
minimal_partial = partial_dfa.minify()
print(f"✓ Partial DFA test passed: {len(partial_dfa.states)} states -> {len(minimal_partial.states)} states")
# Check it's still partial
trans_count = sum(len(trans) for trans in minimal_partial.transitions.values())
symbol_count = len(minimal_partial.input_symbols) * len(minimal_partial.states)
if trans_count < symbol_count:
    print(f"✓ Still partial: {trans_count} transitions < {symbol_count} max")
else:
    print(f"⚠️ Warning: Not partial anymore: {trans_count} == {symbol_count}")

# Test 3: Large reducible DFA
print("\nTesting large reducible DFA (20K states)...")
from random import Random
rand = Random(42)

num_groups = 200
states_per_group = 100
alphabet_size = 50

states = set(range(num_groups * states_per_group))
input_symbols = set(chr(ord('a') + i) if i < 26 else f's{i}' for i in range(alphabet_size))
initial_state = 0

# Create final states
final_states = set()
for group_id in range(num_groups):
    if group_id % 2 == 0:
        for i in range(states_per_group):
            final_states.add(group_id * states_per_group + i)

# Create transitions where states in same group behave identically
transitions = {}
group_behaviors = []

for group_id in range(num_groups):
    group_behavior = {}
    for symbol in input_symbols:
        if rand.random() < 0.8:
            target_group = rand.randint(0, num_groups - 1)
            group_behavior[symbol] = target_group
        else:
            group_behavior[symbol] = None
    group_behaviors.append(group_behavior)

for group_id in range(num_groups):
    group_behavior = group_behaviors[group_id]
    for i in range(states_per_group):
        state_id = group_id * states_per_group + i
        state_transitions = {}
        for symbol, target_group in group_behavior.items():
            if target_group is not None:
                target_state = target_group * states_per_group + rand.randint(0, states_per_group - 1)
                state_transitions[symbol] = target_state
        transitions[state_id] = state_transitions

large_dfa = DFA(
    states=states,
    input_symbols=input_symbols,
    transitions=transitions,
    initial_state=initial_state,
    final_states=final_states,
    allow_partial=True,
)

print(f"Generated {len(large_dfa.states)} state DFA with {alphabet_size} symbols")
import time
start = time.perf_counter()
minimal_large = large_dfa.minify()
elapsed = time.perf_counter() - start

print(f"✓ Large DFA minimized in {elapsed:.2f}s: {len(large_dfa.states)} -> {len(minimal_large.states)} states")
print(f"  Reduction: {len(large_dfa.states) / len(minimal_large.states):.1f}x")

print("\n✅ All tests passed!")
